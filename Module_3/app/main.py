import asyncio
import datetime
from io import BytesIO
import mimetypes

from bson import ObjectId
from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError, ValidationException
from contextlib import asynccontextmanager
import logging

import httpx
import asyncio

from fastapi.middleware.cors import CORSMiddleware


from app.models.documents import AnalysisResult, AnalysisStatus, ConversionStatus, DocumentMetadata, DocumentUpdate
from app.db.repositories.documents import DocumentRepository
from app.api.endpoints import documents
from app.core.config import settings
from app.db.mongodb import db_context, connect_to_mongo, close_mongo_connection
from app.api.errors import (
    conflict_exception_handler,
    http_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
    database_exception_handler,
    document_not_found_exception_handler,
    generic_exception_handler,
)

from app.core.exceptions import (
    BaseCustomException,
    ConflictException,
    DocumentNotFoundException,
    DatabaseException,
    FileNotFoundInGridFSException,
)

ALLOWED_ORIGINS = [
    "http://localhost",
    "http://localhost:80",
    "http://127.0.0.1",
    "http://localhost:3000",
]


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

change_stream_listener_task: asyncio.Task | None = None

async def process_document_pipeline(change_event: dict, repo: DocumentRepository, conversion_url: str, detection_url: str):
    """Processes a single insert event from the change stream."""
    doc_id_obj = change_event.get('documentKey', {}).get('_id')
    full_document = change_event.get('fullDocument')

    if not doc_id_obj or not isinstance(doc_id_obj, ObjectId):
        logger.warning(f"Skipping change event: missing/invalid documentKey._id: {change_event.get('documentKey')}")
        return

    document_id = str(doc_id_obj)
    logger.info(f"[DocID: {document_id}] Processing started.")

    if not conversion_url:
        logger.error(f"[DocID: {document_id}] Skipping processing: CONVERSION_SERVICE_URL not set.")
        await repo.update(document_id, DocumentUpdate(conversionStatus=ConversionStatus.STATUS_FAILED, conversionError="Missing Conversion Service URL"))
        return
    if not detection_url:
        logger.error(f"[DocID: {document_id}] Skipping detection step: DETECTION_SERVICE_URL not set.")

    original_doc_path = None
    original_filename = f"document_{document_id}"
    gridfs_id = None
    normalized_text_content: str | None = None

    try:
        if not full_document:
            logger.warning(f"[DocID: {document_id}] Full document missing in change event. Fetching.")
            doc_data = await repo.get_by_id(document_id)
            if not doc_data: raise DocumentNotFoundException(f"Document {document_id} disappeared after insert event.")
            full_document = doc_data.model_dump(by_alias=True)

        original_doc_path = full_document.get("originalDocumentPath")
        original_filename = full_document.get("originalFilename", original_filename)

        if not original_doc_path or not original_doc_path.startswith("gridfs:"):
            raise ValueError("Missing or invalid originalDocumentPath.")

        gridfs_id_str = original_doc_path.split(":")[-1]
        if not ObjectId.is_valid(gridfs_id_str): raise ValueError("Invalid GridFS ObjectId format.")
        gridfs_id = ObjectId(gridfs_id_str)

        logger.info(f"[DocID: {document_id}] Downloading original file from GridFS: {gridfs_id}")
        content_stream_gen, file_meta = await repo.download_gridfs_file(gridfs_id)
        content_type = file_meta.get("contentType")
        gridfs_filename = file_meta.get("originalFilename", original_filename)
        
        if not content_type or content_type == gridfs_filename.rsplit('.', 1)[-1].lower():
            guessed_type, _ = mimetypes.guess_type(gridfs_filename)
            content_type = guessed_type if guessed_type else "application/octet-stream"
            logger.warning(f"[DocID: {document_id}] ContentType from GridFS was missing or invalid. Guessed as: {content_type} for filename '{gridfs_filename}'")

        file_content_bytes = b"".join([chunk async for chunk in content_stream_gen])
        if not file_content_bytes: raise ValueError("Original file content is empty.")
        file_like_object = BytesIO(file_content_bytes)
        logger.info(f"[DocID: {document_id}] Original file downloaded ({len(file_content_bytes)} bytes).")

        # Wywołanie Module 2 (Konwersja)
        logger.info(f"[DocID: {document_id}] Calling Conversion Service (Module 2): {conversion_url}")
        logger.info(f"[DocID: {document_id}] Sending to M2 - Filename: {gridfs_filename}, Content-Type: {content_type}")
        files_payload = {'file': (gridfs_filename, file_like_object, content_type)}

        async with httpx.AsyncClient() as client:
            response_m2 = await client.post(conversion_url, files=files_payload) 
            response_m2.raise_for_status()
            conversion_result = response_m2.json() 
            logger.info(f"[DocID: {document_id}] Conversion Service responded OK.")

        # Przetwarzanie odpowiedzi z Module 2 i aktualizacja DB
        normalized_text_content = conversion_result.get("text")
        metadata_dict = conversion_result.get("metadata")

        if metadata_dict is None:
            raise ValueError("Invalid response structure from Conversion Service (missing 'metadata').")

        try:
            parsed_metadata = DocumentMetadata(**metadata_dict)
        except Exception as pydantic_error:
             raise ValueError(f"Invalid metadata structure from Conversion Service: {pydantic_error}")

        conversion_update = DocumentUpdate(
            conversionStatus=ConversionStatus.STATUS_COMPLETED,
            conversionTimestamp=datetime.datetime.now(datetime.timezone.utc),
            normalizedText=normalized_text_content,    
            metadata=parsed_metadata             
        )
        logger.info(f"[DocID: {document_id}] Updating database after successful conversion.")
        await repo.update(document_id, conversion_update)
        logger.info(f"[DocID: {document_id}] Database updated after conversion.")

        # Wywołanie Module 4 (Detekcja)
        if not detection_url:
            logger.warning(f"[DocID: {document_id}] Skipping detection: DETECTION_SERVICE_URL not set.")
            logger.info(f"[DocID: {document_id}] Processing finished (conversion only).")
            return 

        if not normalized_text_content:
            logger.warning(f"[DocID: {document_id}] Skipping detection: No normalized text available after conversion.")
            await repo.update(document_id, DocumentUpdate(analysisResult=AnalysisResult(status=AnalysisStatus.SKIPPED, error="No text from conversion")))
            logger.info(f"[DocID: {document_id}] Processing finished (conversion OK, detection skipped).")
            return

        logger.info(f"[DocID: {document_id}] Calling Detection Service (Module 4): {detection_url}")
        detection_payload = {"text": normalized_text_content}
        async with httpx.AsyncClient(timeout=180.0) as client:
            response_m4 = await client.post(detection_url, json=detection_payload)
            response_m4.raise_for_status()
            detection_results = response_m4.json()
            logger.info(f"[DocID: {document_id}] Detection Service responded OK.")

        # Przetwarzanie odpowiedzi z Module 4 i aktualizacja DB
        if not isinstance(detection_results, list):
            raise ValueError("Invalid response structure from Detection Service (expected a list).")

        analysis_update = DocumentUpdate(
            analysisResult=AnalysisResult(
                status=AnalysisStatus.COMPLETED,
                timestamp=datetime.datetime.now(datetime.timezone.utc),
                detectedItems=detection_results
            )
        )
        logger.info(f"[DocID: {document_id}] Updating database after successful detection.")
        await repo.update(document_id, analysis_update)
        logger.info(f"[DocID: {document_id}] Database updated after detection.")
        logger.info(f"[DocID: {document_id}] Processing finished successfully.")

    except DocumentNotFoundException as e:
        logger.error(f"[DocID: {document_id}] Processing failed: Document not found during pipeline. {e}")
    except FileNotFoundInGridFSException as e:
        logger.error(f"[DocID: {document_id}] Processing failed: GridFS file error. {e}")
        await repo.update(document_id, DocumentUpdate(conversionStatus=ConversionStatus.STATUS_FAILED, conversionError=f"GridFS Error: {e}"))
    except httpx.RequestError as exc:
        target_service = "Conversion(M2)" if detection_url and 'response_m2' not in locals() else "Detection(M4)"
        logger.error(f"[DocID: {document_id}] Processing failed: HTTP request error connecting to {target_service}. {exc}")
        status_update = DocumentUpdate(
            conversionStatus=ConversionStatus.STATUS_FAILED, conversionError=f"Network error calling {target_service}: {exc}"
        ) if target_service == "Conversion(M2)" else DocumentUpdate(
           analysisResult=AnalysisResult(status=AnalysisStatus.FAILED, error=f"Network error calling {target_service}: {exc}")
        )
        await repo.update(document_id, status_update)
    except httpx.HTTPStatusError as exc:
        target_service = "Conversion(M2)" if exc.request.url == conversion_url else "Detection(M4)"
        logger.error(f"[DocID: {document_id}] Processing failed: HTTP status error from {target_service}. Status: {exc.response.status_code}. Response: {exc.response.text[:200]}")
        error_msg = f"Error from {target_service} ({exc.response.status_code}): {exc.response.text[:150]}"
        status_update = DocumentUpdate(
             conversionStatus=ConversionStatus.STATUS_FAILED, conversionError=error_msg
        ) if target_service == "Conversion(M2)" else DocumentUpdate(
            analysisResult=AnalysisResult(status=AnalysisStatus.FAILED, error=error_msg)
        )
        await repo.update(document_id, status_update)
    except (ValueError, ValidationException, TypeError) as e:
        logger.error(f"[DocID: {document_id}] Processing failed: Data error or invalid response. {e}")
        failed_step = "conversion" if 'parsed_metadata' not in locals() else "detection"
        status_update = DocumentUpdate(
            conversionStatus=ConversionStatus.STATUS_FAILED, conversionError=f"Data/Response Error: {e}"
        ) if failed_step == "conversion" else DocumentUpdate(
            analysisResult=AnalysisResult(status=AnalysisStatus.FAILED, error=f"Data/Response Error: {e}")
        )
        await repo.update(document_id, status_update)
    except DatabaseException as e:
         logger.error(f"[DocID: {document_id}] Processing failed: Database update error. {e}")
    except Exception as e:
        logger.exception(f"[DocID: {document_id}] Processing failed: Unexpected error.")
        try:
            failed_step = "conversion" if 'conversion_update' not in locals() else "detection"
            status_update = DocumentUpdate(
                conversionStatus=ConversionStatus.STATUS_FAILED, conversionError=f"Unexpected error: {e}"
            ) if failed_step == "conversion" else DocumentUpdate(
                analysisResult=AnalysisResult(status=AnalysisStatus.FAILED, error=f"Unexpected error: {e}")
            )
            await repo.update(document_id, status_update)
        except Exception as final_error:
             logger.error(f"[DocID: {document_id}] Could not even update status after unexpected error: {final_error}")

async def watch_new_documents(db, fs, conversion_url: str, detection_url: str):
    """Nasłuchuje na kolekcji 'documents' i uruchamia pipeline przetwarzania."""
    repo = DocumentRepository(db, fs)
    collection = db.documents
    pipeline = [{'$match': {'operationType': 'insert'}}]

    logger.info("Starting change stream listener for new documents...")
    while True:
        try:
            async with collection.watch(pipeline, full_document='updateLookup') as stream:
                async for change in stream:
                    # Uruchomiono przetwarzanie jako osobne zadanie asyncio
                    # aby nie blokować odbioru kolejnych zdarzeń
                    asyncio.create_task(process_document_pipeline(
                        change, repo, conversion_url, detection_url
                    ))
        except asyncio.CancelledError:
            logger.info("Change stream listener task cancelled.")
            break 
        except Exception as e:
            logger.exception(f"Change stream listener error: {e}. Restarting listener in 5 seconds...")
            await asyncio.sleep(5)

    logger.info("Change stream listener stopped definitively.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Zarządzanie cyklem życia aplikacji FastAPI."""
    global change_stream_listener_task
    logger.info("Application startup...")
    listener_started = False
    try:
        await connect_to_mongo()
        if db_context.db is not None and db_context.fs is not None:
            logger.info("MongoDB connected.")
            if settings.CONVERSION_SERVICE_URL and settings.DETECTION_SERVICE_URL:
                logger.info("Starting change stream listener...")
                change_stream_listener_task = asyncio.create_task(
                    watch_new_documents(
                        db_context.db,
                        db_context.fs,
                        settings.CONVERSION_SERVICE_URL,
                        settings.DETECTION_SERVICE_URL
                    )
                )
                listener_started = True
                logger.info("Change stream listener task created.")
            else:
                missing_urls = []
                if not settings.CONVERSION_SERVICE_URL: missing_urls.append("CONVERSION_SERVICE_URL")
                if not settings.DETECTION_SERVICE_URL: missing_urls.append("DETECTION_SERVICE_URL")
                logger.warning(f"Change stream listener WILL NOT start: Missing configuration for {', '.join(missing_urls)}.")
        else:
            logger.error("Change stream listener WILL NOT start: DB connection failed.")

        yield

    except Exception as e:
        logger.critical(f"Application startup failed: {e}", exc_info=True)
        raise e
    finally:
        logger.info("Application shutdown sequence initiated...")
        if listener_started and change_stream_listener_task and not change_stream_listener_task.done():
            logger.info("Cancelling change stream listener task...")
            change_stream_listener_task.cancel()
            try:
                await change_stream_listener_task
                logger.info("Change stream listener task successfully cancelled.")
            except asyncio.CancelledError:
                logger.info("Change stream listener task cancellation confirmed.")
            except Exception as e:
                logger.error(f"Error during change stream listener task shutdown: {e}", exc_info=True)

        await close_mongo_connection()
        logger.info("Application shutdown sequence complete.")


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="API for managing documents, conversion, sensitive data identification.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.add_exception_handler(FileNotFoundInGridFSException, document_not_found_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(DocumentNotFoundException, document_not_found_exception_handler)
app.add_exception_handler(DatabaseException, database_exception_handler)
app.add_exception_handler(ConflictException, conflict_exception_handler) 
app.add_exception_handler(BaseCustomException, generic_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)

app.include_router(documents.router, prefix=settings.API_V1_STR, tags=["Documents"])


@app.get(
    "/",
    tags=["Root"],
    summary="Root Endpoint / Health Check",
    description="Returns a welcome message indicating the service is running.",
)
async def read_root():
    """Returns a simple welcome message indicating the service is running."""
    return {"message": f"Welcome to the {settings.PROJECT_NAME} API"}
