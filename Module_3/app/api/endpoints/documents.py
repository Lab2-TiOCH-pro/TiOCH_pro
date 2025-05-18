from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Path,
    UploadFile,
    File,
    Form,
    status,
)
from typing import Optional, List
from datetime import datetime
import traceback

from fastapi.responses import StreamingResponse
from pydantic import EmailStr

from app.models.documents import (
    DocumentUpdate,
    DocumentList,
    DocumentInDB,
    UploadResultItem
)
from app.services.documents import DocumentService
from app.api.dependencies import get_document_service
from app.core.exceptions import (
    DocumentNotFoundException,
    DatabaseException,
    ValidationException,
    FileNotFoundInGridFSException
)

router = APIRouter()


@router.post(
    "/documents",
    status_code=status.HTTP_207_MULTI_STATUS,
    response_model=List[UploadResultItem],
    summary="Upload One or More Documents",
    description="Uploads one or more document filesw ith uploader email. Stores files in GridFS.",
)
async def upload_documents(
    files: List[UploadFile] = File(
        ..., description="One or more document files to upload."
    ),
    uploader_email: EmailStr = Form(..., description="Uploader's email address."),
    document_service: DocumentService = Depends(get_document_service),
):
    """
    Handles uploading multiple files. Each file is processed individually.
    Returns a list detailing the outcome for each file.
    """
    results: List[UploadResultItem] = []

    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No files were uploaded."
        )

    for file in files:
        filename = file.filename
        if not filename:
            results.append(
                UploadResultItem(
                    filename="N/A", status="failed", error="Missing filename."
                )
            )
            continue

        doc_id = None
        file_content = b""

        try:
            file_format = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
            if not file_format:
                 raise ValidationException(f"Cannot determine file format for '{filename}'. Missing extension.")
            
            file_content = await file.read()
            file_size = len(file_content)

            if file_size == 0:
                raise ValidationException("Uploaded file cannot be empty.")

            doc_id = await document_service.create_document(
                file_name=filename,
                file_format=file_format,
                file_content=file_content,
                uploader_email=uploader_email,
            )

            results.append(
                UploadResultItem(
                    filename=filename, documentId=doc_id, status="uploaded"
                )
            )

        except ValidationException as e:
             print(f"Validation error processing file '{filename}': {e.detail}")
             results.append(
                 UploadResultItem(
                    filename=filename,
                    status="failed",
                    error=str(e.detail),
                 )
             )
        except DatabaseException as e:
            print(f"Database error processing file '{filename}': {e.detail}")
            traceback.print_exc()
            results.append(
                UploadResultItem(
                    filename=filename,
                    status="failed",
                    error="Failed to store document due to a database issue.",
                )
            )
        except Exception as e:
            print(f"Unexpected error processing file '{filename}': {e}")
            traceback.print_exc()
            results.append(
                UploadResultItem(
                    filename=filename,
                    status="failed",
                    error="An unexpected server error occurred during upload.",
                )
            )
        finally:
            try:
                await file.close()
            except Exception as close_err:
                print(f"Error closing file handle for '{filename}': {close_err}")

    return results


@router.get(
    "/documents",
    response_model=DocumentList,
    summary="List Documents Metadata",
    description="Retrieves paginated list of document metadata with filtering capabilities.",
)
async def list_documents(
    page: int = Query(1, ge=1, description="Page number starting from 1."),
    limit: int = Query(20, ge=1, le=100, description="Number of documents per page."),
    conversion_status: Optional[str] = Query(None, description="Filter by conversion status (e.g., 'completed', 'pending')."),
    original_format: Optional[str] = Query(None, description="Filter by original file format (e.g., 'pdf', 'docx')."),
    date_from: Optional[datetime] = Query(None, description="Filter documents uploaded from this date/time (ISO format)."),
    date_to: Optional[datetime] = Query(None, description="Filter documents uploaded up to this date/time (ISO format)."),
    query: Optional[str] = Query(None, description="Search term in original filename."),
    document_service: DocumentService = Depends(get_document_service),
):
    """Fetches list of document metadata, including filters and pagination."""
    try:
        result = await document_service.list_documents(
            page=page,
            limit=limit,
            conversion_status=conversion_status,
            original_format=original_format,
            date_from=date_from,
            date_to=date_to,
            query=query,
        )
        return result
    except DatabaseException as e:
        print(f"DB error listing docs: {e.detail}")
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"DB error: {e.detail}",
        )
    except Exception as e:
        print(f"Unexpected error listing docs: {e}")
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error: {str(e)}",
        )


@router.get(
    "/documents/{document_id}",
    response_model=DocumentInDB,
    summary="Get Single Document",
    description="Retrieves a specific document identified by its ID.",
)
async def get_document(
    document_id: str = Path(..., description="The unique identifier of the document."),
    document_service: DocumentService = Depends(get_document_service),
):
    """Get a single document."""
    try:
        document = await document_service.get_document(document_id)
        return document
    except DocumentNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.detail)
    except DatabaseException as e:
        print(f"DB error getting doc {document_id}: {e.detail}")
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"DB error: {e.detail}",
        )
    except Exception as e:
        print(f"Unexpected error getting doc {document_id}: {e}")
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error: {str(e)}",
        )


# Dla Modułu 2 (Konwersja) do zapisania wyników konwersji lub Modułu 4 (AI) do zapisania wyników analizy.
@router.patch(
    "/documents/{document_id}",
    response_model=DocumentInDB,
    summary="Update document after conversion",
    description="Updates document metadata, typically after conversion or analysis. Can store normalized text in GridFS via 'normalizedText' field in the request body.",
)
async def update_document(
    document_update: DocumentUpdate,
    document_id: str = Path(..., description="Document ID to update."),
    document_service: DocumentService = Depends(get_document_service),
):
    """Updates document metadata, e.g. conversion status, reference to normalized text, analysis results."""
    try:
        updated_document = await document_service.update_document(
            document_id, document_update
        )
        return updated_document
    except DocumentNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.detail)
    except DatabaseException as e:
        print(f"DB error updating doc {document_id}: {e.detail}")
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"DB error: {e.detail}",
        )
    except ValidationException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.detail)
    except Exception as e:
        print(f"Unexpected error updating doc {document_id}: {e}")
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error: {str(e)}",
        )


@router.delete(
    "/documents/{document_id}",
    status_code=status.HTTP_200_OK,
    response_model=dict,
    summary="Delete Document",
    description="Deletes document metadata and associated GridFS file.",
)
async def delete_document(
    document_id: str = Path(..., description="Document ID to delete."),
    document_service: DocumentService = Depends(get_document_service),
):
    """Removes a document (metadata and associated file from GridFS)."""
    try:
        await document_service.delete_document(document_id)
        return {
            "message": "Document deleted.",
            "documentId": document_id,
            "success": True,
        }
    except DocumentNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.detail)
    except DatabaseException as e:
        print(f"DB error deleting doc {document_id}: {e.detail}")
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"DB error: {e.detail}",
        )
    except Exception as e:
        print(f"Unexpected error deleting doc {document_id}: {e}")
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error: {str(e)}",
        )

    
@router.get(
    "/documents/{document_id}/content/original",
    summary="Download Original Document Content",
    description="Downloads the original content of the specified document.",
    responses={
        status.HTTP_200_OK: {
            "description": "Document content streamed successfully.",
            "content": {"application/octet-stream": {}}
        },
        status.HTTP_404_NOT_FOUND: {"description": "Document or original file content not found."},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"description": "Internal server error."},
    }
)
async def download_original_document(
    document_id: str = Path(..., description="The ID of the document whose content is to be downloaded."),
    document_service: DocumentService = Depends(get_document_service),
):
    """Gets the original contents of the document file."""
    try:
        stream_generator, file_metadata = await document_service.get_original_document_content(document_id)

        media_type = file_metadata.get("contentType", "application/octet-stream")

        original_filename = file_metadata.get("originalFilename", f"document_{document_id}_original")

        headers = {
            "Content-Disposition": f'attachment; filename="{original_filename}"'
        }

        return StreamingResponse(
            content=stream_generator,
            media_type=media_type,
            headers=headers
        )
    except (DocumentNotFoundException, FileNotFoundInGridFSException) as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.detail)
    except DatabaseException as e:
         print(f"DB error downloading original content for {document_id}: {e.detail}")
         traceback.print_exc()
         raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"DB error: {e.detail}")
    except Exception as e:
        print(f"Unexpected error downloading original content for {document_id}: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Unexpected error: {str(e)}")

