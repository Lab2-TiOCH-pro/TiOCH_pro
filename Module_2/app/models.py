from datetime import datetime
from pydantic import BaseModel

class FileMetadata(BaseModel):
    filename: str
    size: int
    date: datetime = datetime.now()

class ExtractTextResponse(BaseModel):
    text: str
    metadata: FileMetadata