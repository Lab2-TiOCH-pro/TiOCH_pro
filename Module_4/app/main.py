import os
from pathlib import Path
from dotenv import load_dotenv, find_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from app.tasks import detect_task, process_document
from app.celery_app import celery
import time
import asyncio

load_dotenv(find_dotenv())

class DetectRequest(BaseModel):
    text: Optional[str] = None
    document_id: Optional[str] = None

class DetectionResult(BaseModel):
    type: str
    value: str
    label: str

app = FastAPI(
    title="Sensitive Data Detection Service",
    version="1.0",
    description="Usługa wykrywania danych wrażliwych zgodna z RODO"
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
    try:
        # Check if document_id is provided for retrieval from database
        if request.document_id:
            # Retrieve document from database, analyze and save results
            return await process_document(request.document_id)
        
        # If document_id is not provided, check if text is provided for analysis
        elif request.text:
            # Check if OpenAI API key is available
            if not os.getenv("OPENAI_API_KEY"):
                use_llm = False
            else:
                use_llm = True
                
            # Enqueue the task
            task = detect_task.delay(request.text, None, use_llm)
            
            # Wait for the task to complete (with timeout)
            timeout = 30  # seconds
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                async_result = celery.AsyncResult(task.id)
                if async_result.ready():
                    if async_result.successful():
                        return async_result.result
                    else:
                        # Task failed
                        raise HTTPException(status_code=500, detail=f"Task failed: {str(async_result.result)}")
                # Wait a bit before checking again
                await asyncio.sleep(0.1)
            
            # If we reach here, the task timed out
            raise HTTPException(status_code=408, detail="Request timeout while processing text")
        else:
            # If neither document_id nor text is provided, return an error
            raise HTTPException(status_code=400, detail="Either document_id or text must be provided")
    except Exception as e:
        # Catch any other exceptions
        raise HTTPException(status_code=500, detail=f"Error processing request: {str(e)}")
