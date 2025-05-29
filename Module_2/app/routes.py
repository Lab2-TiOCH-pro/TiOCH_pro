from typing import Optional

from dns.rcode import NOERROR
from fastapi import UploadFile, HTTPException, APIRouter, Body, File
from fastapi.params import Form

from app.config import MAX_FILE_SIZE_MB
from app.models import ExtractTextResponse
from app.utils import  file_extraction, web_extraction

router = APIRouter()

@router.post(
    "/file",
    response_model=ExtractTextResponse,
    summary="Extract text from an uploaded file",
    description=(
        "Uploads a document or url and extracts plain text content from supported formats. "
        "Supports PDF, DOCX, XLSX, CSV, HTML, TXT, JSON, and XML. "
        f"Max file size: {MAX_FILE_SIZE_MB}MB."
    ),
    responses={
        200: {"description": "Text successfully extracted."},
        400: {"description": "Invalid file or website."},
        413: {"description": "File too large."},
        422: {"description": "Malformed request."},
    }
)
async def extract_text_from_file(
    file: Optional[UploadFile] = File(default=None),
    website_url: Optional[str] = Form(default=None),
):
    response: ExtractTextResponse

    if file is not None:
        response = await file_extraction(file)
    elif website_url is not None:
        response = await web_extraction(website_url)
    else:
        raise HTTPException(status_code=422, detail="Malformed request.")

    return response
