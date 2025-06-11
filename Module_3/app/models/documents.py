import datetime
from enum import Enum
from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, ConfigDict, Field, validator, GetCoreSchemaHandler, EmailStr
from pydantic_core import core_schema
from bson import ObjectId


class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate_object_id_compat

    @classmethod
    def validate_object_id(cls, v):
        """Validate that the input is a valid ObjectId"""
        if isinstance(v, ObjectId):
            return v
        try:
            if ObjectId.is_valid(str(v)):
                return ObjectId(v)
        except Exception:
            pass
        raise ValueError(f"'{v}' is not a valid ObjectId")

    @classmethod
    def validate_object_id_compat(cls, v, _: core_schema.ValidationInfo):
        """Validation method for compatibility with __get_validators__ if needed."""
        return cls.validate_object_id(v)

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        """
        Return a Pydantic CoreSchema using the single-argument validator.
        """
        return core_schema.no_info_plain_validator_function(
            cls.validate_object_id,
            serialization=core_schema.to_string_ser_schema(),
        )

    @classmethod
    def __get_pydantic_json_schema__(
        cls, core_schema: core_schema.CoreSchema, handler: GetCoreSchemaHandler
    ) -> Dict[str, Any]:
        """
        Defines the JSON schema for OpenAPI (Swagger).
        Specifies that the ObjectId field will be represented as a string.
        """
        json_schema = handler(core_schema)
        json_schema.update(type="string", example="605fe1a6e3b4f8a3c1e6a7b8")
        return json_schema

# Enum definiujący możliwe statusy konwersji dokumentu (przez Moduł 2).
class ConversionStatus(str, Enum):
    STATUS_PENDING = "pending"
    STATUS_COMPLETED = "completed"
    STATUS_FAILED = "failed"

# Enum definiujący możliwe statusy analizy danych wrażliwych (przez Moduł 4).
class AnalysisStatus(str, Enum):
    PENDING = "pending"         
    COMPLETED = "completed"  
    FAILED = "failed" 
    NOT_STARTED = "not_started" # do testów
    SKIPPED = "skipped"

class AnalysisResult(BaseModel):
    """Result of the analysis of sensitive data."""
    status: AnalysisStatus = Field(default=AnalysisStatus.PENDING)
    timestamp: Optional[datetime.datetime] = None
    error: Optional[str] = None
    detected_items: List[Dict[str, Any]] = Field(
        default_factory=list,
        alias="detectedItems",
        description="List of detected sensitive data items."
    )
    analysis_time: Optional[float] = Field(
        None,
        alias="analysisTime",
        description="Analysis duration in seconds."
    )

    model_config = ConfigDict(
        populate_by_name=True, 
        use_enum_values=True,
        extra='ignore'    
    )

class DocumentMetadata(BaseModel):
    """Metadata extracted by Module (Conversion)."""

    filename: str = Field(..., description="Filename reported by the conversion module.")
    size: int = Field(..., description="Size in bytes reported by the conversion module.")

    date: Optional[datetime.datetime] = Field(None, description="Date reported by the conversion module.")

    model_config = ConfigDict(
        populate_by_name=True,
        extra='ignore'      
    )


class DocumentBase(BaseModel):
    """Base fields for a document."""

    original_filename: str = Field(..., alias="originalFilename", description="Original name of the uploaded file.")
    original_format: str = Field(..., alias="originalFormat", description="Original file format extension (e.g., 'pdf', 'docx').")
    uploader_email: EmailStr = Field(..., alias="uploaderEmail", description="Email of the uploader (required).")
    
    model_config = ConfigDict(
        populate_by_name=True
    )

class DocumentCreate(DocumentBase):
    """Model used when creating a new document entry."""
    pass


class DocumentUpdate(BaseModel):
    """Model used for updating a document (typically status and conversion/analysis results)."""

    # --- Pola aktualizowane przez Moduł 2 (Konwersja) ---
    conversion_status: Optional[ConversionStatus] = Field(None, alias="conversionStatus", description="Status of the document conversion.")
    conversion_timestamp: Optional[datetime.datetime] = Field(None, alias="conversionTimestamp", description="Timestamp when conversion finished.")
    conversion_error: Optional[str] = Field(None, alias="conversionError", description="Error message if conversion failed.")

    # To pole jest specjalne: jeśli zostanie przekazane, jego zawartość (tekst)
    # zostanie zapisana w GridFS, a w metadanych dokumentu zapisana zostanie tylko referencja ('normalizedTextRef').
    normalized_text: Optional[str] = Field(
        None,
        description="The normalized text content to be saved to GridFS. If provided, 'normalizedTextRef' will be updated.",
        alias="normalizedText"
    )
    metadata: Optional[DocumentMetadata] = Field(None, description="Metadata object reported by the conversion module (Module 2).")
    processing_time_seconds: Optional[float] = Field(None, alias="processingTimeSeconds", description="Processing time for conversion in seconds.")

    # --- Pola aktualizowane przez Moduł 4 (AI - Analiza) ---
    analysis_result: Optional[AnalysisResult] = Field(None, alias="analysisResult", description="Detailed results of the sensitive data analysis.")

    model_config = ConfigDict(
        populate_by_name=True,
        extra='ignore'
    )


class DocumentInDB(DocumentBase):
    """Full document model as stored in the database."""

    id: PyObjectId = Field(..., alias="_id", description="Unique identifier for the document (MongoDB ObjectId).")
    upload_timestamp: datetime.datetime = Field(..., alias="uploadTimestamp", description="Timestamp when the document entry was created.")
    content_hash: Optional[str] = Field(None, alias="contentHash", description="SHA-256 hash of the original file content.")

     # --- Pola związane z konwersją (aktualizowane przez Moduł 2) ---
    conversion_timestamp: Optional[datetime.datetime] = Field(None, alias="conversionTimestamp", description="Timestamp when conversion finished.")
    conversion_status: ConversionStatus = Field(
        default=ConversionStatus.STATUS_PENDING, alias="conversionStatus", description="Status of the document conversion."
    )
    conversion_error: Optional[str] = Field(None, alias="conversionError", description="Error message if conversion failed.")

    normalized_text: Optional[str] = Field(None, alias="normalizedText", description="Normalized text content stored directly in the document.")
    
    metadata: Optional[DocumentMetadata] = Field(None, description="Metadata extracted during conversion.")

    # Referencja do oryginalnego pliku zapisanego w GridFS.
    original_document_path: Optional[str] = Field(
        None,
        description="Reference to the original file in GridFS (e.g., 'gridfs:ObjectId').",
        alias="originalDocumentPath",
    )
    processing_time_seconds: Optional[float] = Field(
        None, alias="processingTimeSeconds", description="Processing time for conversion in seconds."
    )

    # --- Pola związane z analizą (aktualizowane przez Moduł 4) ---
    analysis_result: Optional[AnalysisResult] = Field(
        None,
        alias="analysisResult",
        description="Detailed results of the sensitive data analysis."
    )

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={
            ObjectId: str,
            datetime.datetime: lambda dt: dt.isoformat() if dt else None
        },
        use_enum_values=True
    )


class DocumentList(BaseModel):
    """Model for the list documents endpoint response, including pagination info."""

    total: int = Field(..., description="Total number of documents matching the query.")
    page: int = Field(..., description="Current page number.")
    limit: int = Field(..., description="Number of documents per page.")
    documents: List[DocumentInDB] = Field(..., description="List of document metadata on the current page.")


class UploadResultItem(BaseModel):
    """Represents the outcome for a single file in a multi-file upload request."""
    filename: str = Field(..., description="Name of the uploaded file.")
    documentId: Optional[str] = Field(None, description="The ID assigned to the document if upload was successful.")
    status: Literal["uploaded", "failed"] = Field(..., description="Status of the upload operation for this file.")
    error: Optional[str] = Field(None, description="Error message if the upload failed.")
