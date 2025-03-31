from fastapi import UploadFile, HTTPException, APIRouter
from FileConversion.converter import FileConversion
from app.config import MAX_FILE_SIZE_MB
from app.models import ExtractTextResponse, FileMetadata
from app.utils import validate_file_size, validate_file_type

router = APIRouter()

@router.post("/file")
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

@router.post("/website")
async def extract_text_from_website(website_url: str):
    return {"message": "still empty :'("}