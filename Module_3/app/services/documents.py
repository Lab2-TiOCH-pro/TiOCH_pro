from typing import Optional, Tuple, AsyncIterator, Dict, Any
from datetime import datetime, timezone
from pydantic import EmailStr
from bson import ObjectId

from app.db.repositories.documents import DocumentRepository

from app.models.documents import (
    AnalysisResult,
    AnalysisStatus,
    ConversionStatus,
    DocumentCreate,
    DocumentUpdate,
    DocumentInDB,
    DocumentList,
)
from app.core.exceptions import ConflictException, DatabaseException, DocumentNotFoundException, ValidationException, FileNotFoundInGridFSException

# Warstwa serwisowa - zawiera logikę biznesową operacji na dokumentach. Oddzielamy logikę API (endpointy) od logiki dostępu do danych (repozytoria).

class DocumentService:
    def __init__(self, document_repository: DocumentRepository):
        """Initializes the service from the document repository."""
        self.document_repository: DocumentRepository = document_repository

    async def create_document(
        self,
        file_name: str,
        file_format: str,
        file_size: int,
        file_content: bytes,
        uploader_email: EmailStr,
    ) -> str:
        """Creates a new document. Performs basic validation and uploads data to the repository."""
        if not file_name:
            raise ValidationException("File name is required.")
        if file_size <= 0:
            raise ValidationException("File content cannot be empty.")

        doc_create = DocumentCreate(
            originalFilename=file_name,
            originalFormat=file_format.lower() if file_format else "",
            uploaderEmail=uploader_email,
        )

        document_id = await self.document_repository.create(
            doc_create, file_size, file_content, file_name
        )

        return document_id

    async def get_document(self, document_id: str) -> DocumentInDB:
        """Get a single document based on its ID."""
        document = await self.document_repository.get_by_id(document_id)

        if document is None:
            raise DocumentNotFoundException(f"Document with ID {document_id} not found")
        return document

    async def list_documents(
        self,
        page: int = 1,
        limit: int = 20,
        conversion_status: Optional[str] = None,
        original_format: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        query: Optional[str] = None,
    ) -> DocumentList:
        """Gets a list of document metadata, including filters and pagination."""
        if page < 1:
            page = 1
        if limit < 1:
            limit = 1
        if limit > 100:
            limit = 100
        
        normalized_format = original_format.lower() if original_format else None

        result_dict = await self.document_repository.get_list(
            page=page,
            limit=limit,
            conversion_status=conversion_status,
            original_format=normalized_format,
            date_from=date_from,
            date_to=date_to,
            query=query,
        )
        
        return DocumentList(**result_dict)

    async def update_document(
        self, document_id: str, document_update: DocumentUpdate
    ) -> DocumentInDB:
        """Updates the metadata of an existing document."""
        updated_document = await self.document_repository.update(
            document_id, document_update
        )
        if updated_document is None:
            existing_doc = await self.document_repository.get_by_id(document_id)
            if existing_doc is None:
                raise DocumentNotFoundException(
                    f"Document with ID '{document_id}' not found for update."
                )
            else:
                return existing_doc

        return updated_document

    async def delete_document(self, document_id: str) -> bool:
        """Updates the metadata of an existing document."""
        deleted = await self.document_repository.delete(document_id)
        if not deleted:
            raise DocumentNotFoundException(
                f"Document with ID {document_id} not found for deletion"
            )
        return True

    async def initiate_document_analysis(self, document_id: str) -> DocumentInDB:
        """
        Marks a document to be picked up for sensitive data analysis.
        Sets the analysis status to PENDING.
        """
        document = await self.get_document(document_id)
       
        allowed_conversion_statuses = [
            ConversionStatus.STATUS_COMPLETED,
            ConversionStatus.STATUS_NOT_REQUIRED
        ]

        if document.conversion_status not in allowed_conversion_statuses:
             raise ConflictException(
                 f"Cannot initiate analysis for document '{document_id}'. "
                 f"Conversion status is '{document.conversion_status.value}'. "
                 f"Requires status to be one of: {[s.value for s in allowed_conversion_statuses]}."
            )
        
        disallowed_analysis_statuses = [
            AnalysisStatus.IN_PROGRESS,
            AnalysisStatus.COMPLETED
        ]

        if document.analysis_status in disallowed_analysis_statuses:
            raise ConflictException(
                f"Analysis for document '{document_id}' cannot be initiated. "
                f"Current analysis status is '{document.analysis_status.value}'."
            )
 
        analysis_update_payload = DocumentUpdate(
            analysis_status=AnalysisStatus.PENDING,

            analysis_result=AnalysisResult(
                status=AnalysisStatus.PENDING,
                timestamp=datetime.now(timezone.utc)
            )
        )

        try:
            updated_document = await self.document_repository.update(
                document_id, analysis_update_payload
            )
            if updated_document is None:
                raise DocumentNotFoundException(
                    f"Document '{document_id}' was not found during the analysis initiation update process."
                 )
            return updated_document
        except DatabaseException as e:
            raise e
        except Exception as e:
            print(f"Unexpected error initiating analysis for {document_id}: {e}")
            raise DatabaseException(f"Failed to update document status to initiate analysis: {str(e)}")
        
    async def _get_gridfs_content(
        self, document_id: str, attribute_name: str
    ) -> Tuple[AsyncIterator[bytes], Dict[str, Any]]:
        """Gets file content from GridFS based on references in the document. Helper method for get_original_document_content and get_normalized_document_text."""
        document = await self.get_document(document_id)

        gridfs_ref = getattr(document, attribute_name, None)

        if not gridfs_ref or not gridfs_ref.startswith("gridfs:"):
            raise FileNotFoundInGridFSException(
                f"No valid GridFS reference found in attribute '{attribute_name}' for document '{document_id}'."
            )

        try:
            gridfs_file_id_str = gridfs_ref.split(":")[-1]
            if not ObjectId.is_valid(gridfs_file_id_str):
                 raise ValueError("Invalid ObjectId format in reference.")
            gridfs_file_id = ObjectId(gridfs_file_id_str)
        except ValueError as e:
            raise FileNotFoundInGridFSException(
                f"Invalid GridFS reference format in attribute '{attribute_name}' for document '{document_id}': {gridfs_ref}. Error: {e}"
            )

        try:
            stream_gen, file_meta = await self.document_repository.download_gridfs_file(gridfs_file_id)
            return stream_gen, file_meta
        except FileNotFoundInGridFSException as e:
             raise FileNotFoundInGridFSException(f"{e.detail} referenced in field '{attribute_name}' for document '{document_id}'.")
        except DatabaseException as e:
             raise e


    async def get_original_document_content(
        self, document_id: str
    ) -> Tuple[AsyncIterator[bytes], Dict[str, Any]]:
        """Gets the data stream of the original document file and its metadata."""
        return await self._get_gridfs_content(document_id, "original_document_path")

    async def get_normalized_document_text(
        self, document_id: str
    ) -> Tuple[AsyncIterator[bytes], Dict[str, Any]]:
        """Takes a data stream of the normalized text of a document and its metadata. Assumes that the text is UTF-8."""
        return await self._get_gridfs_content(document_id, "normalized_text_ref")