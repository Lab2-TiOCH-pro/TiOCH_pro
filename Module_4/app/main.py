import os
from pathlib import Path
from dotenv import load_dotenv, find_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
from app.tasks import detect_task
from app.celery_app import celery

# Załaduj zmienne środowiskowe z pliku .env (znajdującego się gdziekolwiek w drzewie)
load_dotenv(find_dotenv())

class DetectRequest(BaseModel):
    text: str

class DetectionResult(BaseModel):
    type: str
    value: str
    label: str

class TaskResponse(BaseModel):
    task_id: str

app = FastAPI(
    title="Sensitive Data Detection Service",
    version="1.0"
)

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}

@app.post("/detect", response_model=TaskResponse)
async def detect(request: DetectRequest):
    """
    Enqueue a sensitive data detection task and return its identifier.
    """
    task = detect_task.delay(request.text)
    return TaskResponse(task_id=task.id)

@app.get("/tasks/{task_id}", response_model=List[DetectionResult])
async def get_task_result(task_id: str):
    """
    Retrieve the result or status of a detection task by ID.
    """
    async_result = celery.AsyncResult(task_id)
    if async_result.state in ("PENDING", "STARTED"):
        raise HTTPException(status_code=202, detail={"status": async_result.state})
    if async_result.state == "FAILURE":
        raise HTTPException(status_code=500, detail=str(async_result.result))
    return async_result.result 