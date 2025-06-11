import requests
from bs4 import BeautifulSoup

from FileConversion.converter import FileConversion
from app.config import ALLOWED_EXTS, ALLOWED_CONTENT_TYPES, MAX_FILE_SIZE, MAX_FILE_SIZE_MB
from fastapi import UploadFile, HTTPException

from app.models import FileMetadata, ExtractTextResponse


async def file_extraction(file: UploadFile) -> ExtractTextResponse:
    extension = file.filename.split(".")[-1].lower()
    content_type = file.headers.get('Content-Type')

    # extension check
    if not validate_file_type(extension, content_type):
        raise HTTPException(status_code=400, detail="File type not allowed")

    # file size check
    if not validate_file_size(file):
        raise HTTPException(status_code=413, detail=f"File too large. Max size is {MAX_FILE_SIZE_MB} MB")

    await file.seek(0)

    extraction = FileConversion(file, extension, content_type)
    extracted_text = extraction.get_text()
    return ExtractTextResponse(
        text=extracted_text,
        metadata=FileMetadata(filename=file.filename, size=file.size)
    )

async def web_extraction(website_url: str) -> ExtractTextResponse:
    try:
        response = requests.get(website_url)
        response.raise_for_status()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch URL: {e}")

    soup = BeautifulSoup(response.text, "html.parser")
    text = soup.get_text()
    clean_text = " ".join(text.split())
    return ExtractTextResponse(
        text=clean_text,
        metadata=FileMetadata(
            filename=website_url,
            size=len(response.content)
        )
    )

def validate_file_type(extension: str, content_type: str) -> bool:
    return extension in ALLOWED_EXTS and content_type in ALLOWED_CONTENT_TYPES

def validate_file_size(file: UploadFile):
    return file.size < MAX_FILE_SIZE