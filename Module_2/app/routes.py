from bs4 import BeautifulSoup
from fastapi import UploadFile, HTTPException, APIRouter, requests, Body
from FileConversion.converter import FileConversion
from app.config import MAX_FILE_SIZE_MB
from app.models import ExtractTextResponse, FileMetadata
from app.utils import validate_file_size, validate_file_type
import requests

router = APIRouter()

@router.post(
    "/file",
    response_model=ExtractTextResponse,
    summary="Extract text from an uploaded file",
    description=(
            "Uploads a document and extracts plain text content from supported formats. "
            "Supports PDF, DOCX, XLSX, CSV, HTML, TXT, JSON, and XML. "
            f"Max file size: {MAX_FILE_SIZE_MB}MB."
    ),
    responses={
        200: {"description": "Text successfully extracted."},
        400: {"description": "Invalid file type or extension."},
        413: {"description": "File too large."},
        422: {"description": "Malformed upload request."}
    }
)
async def extract_text_from_file(file: UploadFile):
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

@router.post(
    "/website",
    response_model=ExtractTextResponse,
    summary="Extract text from a website",
    description="Fetches the contents of a public webpage and extracts clean text from its HTML using BeautifulSoup.",
    responses={
        200: {"description": "Text successfully extracted from the website."},
        400: {"description": "Invalid or unreachable URL."},
        422: {"description": "Validation error due to malformed request body."}
    }
)
async def extract_text_from_website(website_url: str = Body(..., embed=True)):
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