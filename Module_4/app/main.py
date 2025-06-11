import os
import logging
from pathlib import Path
from dotenv import load_dotenv, find_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from app.tasks import detect_task, process_document
from app.celery_app import celery
import time
import asyncio
import traceback

# Konfiguracja loggera
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv(find_dotenv())

class DetectRequest(BaseModel):
    text: Optional[str] = None
    document_id: Optional[str] = None

class DetectionResult(BaseModel):
    type: str
    value: str
    label: str

class APIException(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(self.detail)

app = FastAPI(
    title="Sensitive Data Detection Service",
    version="1.0",
    description="Usługa wykrywania danych wrażliwych zgodna z RODO"
)

# Dodanie middleware do obsługi wyjątków
@app.middleware("http")
async def exception_handling_middleware(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception as e:
        logger.error(f"Nieobsłużony wyjątek: {str(e)}")
        logger.error(traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={"detail": f"Wystąpił błąd wewnętrzny serwera: {str(e)}"}
        )

# Dodanie obsługi wyjątków
@app.exception_handler(APIException)
async def api_exception_handler(request: Request, exc: APIException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )

@app.get("/health")
async def health_check():
    """
    Endpoint checking service status.
    """
    return {"status": "ok"}

@app.post("/detect", response_model=List[DetectionResult])
async def detect(request: DetectRequest):
    """
    Main endpoint for detecting sensitive data.
    
    Handles two modes:
    1. Analysis of text provided directly in the request
    2. Analysis of document from module 3 database based on document_id
    
    Returns a list of detected sensitive data in the format:
    [
      { "type": "ID", "value": "12345678901", "label": "PESEL" },
      { "type": "kontakt", "value": "email@example.com", "label": "EMAIL" }
    ]
    """
    request_id = id(request)  # Unikalny identyfikator żądania dla logowania
    logger.info(f"[{request_id}] Otrzymano żądanie /detect: document_id={request.document_id is not None}, text_length={len(request.text) if request.text else 0}")
    
    try:
        # Check if document_id is provided for retrieval from database
        if request.document_id:
            logger.info(f"[{request_id}] Przetwarzanie dokumentu o ID: {request.document_id}")
            try:
                result = await process_document(request.document_id)
                logger.info(f"[{request_id}] Dokument przetworzony pomyślnie, znaleziono {len(result)} elementów")
                return result
            except Exception as e:
                logger.error(f"[{request_id}] Błąd podczas przetwarzania dokumentu: {str(e)}")
                logger.error(traceback.format_exc())
                raise APIException(status_code=500, detail=f"Błąd podczas przetwarzania dokumentu: {str(e)}")
        
        # If document_id is not provided, check if text is provided for analysis
        elif request.text:
            logger.info(f"[{request_id}] Przetwarzanie tekstu o długości {len(request.text)}")
            
            # Check if OpenAI API key is available
            if not os.getenv("OPENAI_API_KEY"):
                logger.warning(f"[{request_id}] Brak klucza API OpenAI, używanie tylko detektora regex")
                use_llm = False
            else:
                logger.info(f"[{request_id}] Klucz API OpenAI dostępny, używanie detektora LLM")
                use_llm = True
                
            # Enqueue the task
            try:
                task = detect_task.delay(request.text, None, use_llm)
                logger.info(f"[{request_id}] Zadanie Celery utworzone: {task.id}")
            except Exception as e:
                logger.error(f"[{request_id}] Błąd podczas tworzenia zadania Celery: {str(e)}")
                logger.error(traceback.format_exc())
                raise APIException(status_code=500, detail=f"Błąd podczas tworzenia zadania Celery: {str(e)}")
            
            # Wait for the task to complete (with timeout)
            timeout = 120  # seconds - zwiększony timeout
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                try:
                    async_result = celery.AsyncResult(task.id)
                    if async_result.ready():
                        if async_result.successful():
                            result = async_result.result
                            if not isinstance(result, list):
                                logger.error(f"[{request_id}] Nieprawidłowy format wyniku: {type(result)}")
                                raise APIException(status_code=500, detail=f"Nieprawidłowy format wyniku: {type(result)}")
                            
                            logger.info(f"[{request_id}] Zadanie zakończone pomyślnie, znaleziono {len(result)} elementów")
                            return result
                        else:
                            # Task failed
                            error_msg = str(async_result.result)
                            logger.error(f"[{request_id}] Zadanie zakończone niepowodzeniem: {error_msg}")
                            raise APIException(status_code=500, detail=f"Zadanie zakończone niepowodzeniem: {error_msg}")
                    
                    # Zadanie nadal w trakcie wykonywania
                    await asyncio.sleep(0.5)  # Dłuższy czas oczekiwania między sprawdzeniami
                except Exception as e:
                    logger.error(f"[{request_id}] Błąd podczas sprawdzania statusu zadania: {str(e)}")
                    logger.error(traceback.format_exc())
                    raise APIException(status_code=500, detail=f"Błąd podczas sprawdzania statusu zadania: {str(e)}")
            
            # If we reach here, the task timed out
            logger.error(f"[{request_id}] Przekroczono limit czasu ({timeout}s) podczas przetwarzania tekstu")
            raise APIException(status_code=408, detail=f"Przekroczono limit czasu ({timeout}s) podczas przetwarzania tekstu")
        else:
            # If neither document_id nor text is provided, return an error
            logger.error(f"[{request_id}] Brak wymaganego parametru: document_id lub text")
            raise APIException(status_code=400, detail="Wymagany jest parametr document_id lub text")
    except APIException:
        # Przekazujemy wyjątek APIException dalej, zostanie obsłużony przez exception_handler
        raise
    except Exception as e:
        # Catch any other exceptions
        logger.error(f"[{request_id}] Nieoczekiwany błąd: {str(e)}")
        logger.error(traceback.format_exc())
        raise APIException(status_code=500, detail=f"Nieoczekiwany błąd: {str(e)}")

