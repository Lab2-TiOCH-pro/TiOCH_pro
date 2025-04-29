import os
from pathlib import Path
from dotenv import load_dotenv, find_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from app.sensitive_detector import SensitiveDataDetector

# Załaduj zmienne środowiskowe z pliku .env (znajdującego się gdziekolwiek w drzewie)
load_dotenv(find_dotenv())

class DetectRequest(BaseModel):
    text: str

class DetectionResult(BaseModel):
    type: str
    value: str
    label: str

app = FastAPI(
    title="Sensitive Data Detection Service",
    version="1.0"
)

# Initialize the detector using existing module
# This detector aggregates regex, NER, and LLM-based detection

detector = SensitiveDataDetector()

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}

@app.post("/detect", response_model=List[DetectionResult])
async def detect(request: DetectRequest):
    """
    Analyze the provided text for sensitive data and return detection results.
    """
    try:
        results = detector.detect(request.text)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 