from app.config import ALLOWED_EXTS, ALLOWED_CONTENT_TYPES, MAX_FILE_SIZE
from fastapi import UploadFile

def validate_file_type(extension: str, content_type: str) -> bool:
    return extension in ALLOWED_EXTS and content_type in ALLOWED_CONTENT_TYPES

def validate_file_size(file: UploadFile):
    return file.size < MAX_FILE_SIZE