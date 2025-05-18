from enum import Enum
from typing import Optional, Dict, Any, Tuple, AsyncIterator
from motor.motor_asyncio import (
    AsyncIOMotorDatabase,
    AsyncIOMotorCollection,
    AsyncIOMotorGridFSBucket,
    AsyncIOMotorGridOut,
)
from bson import ObjectId
from datetime import datetime, timezone
import hashlib
import io
from gridfs.errors import NoFile as GridFSFileNotFound

from pydantic import BaseModel

from app.core.exceptions import DatabaseException, ValidationException, FileNotFoundInGridFSException
from app.models.documents import (
    DocumentCreate,
    DocumentUpdate,
    DocumentInDB,
    ConversionStatus
)

# Klasa repozytorium implementuje wzorzec Repository,
# hermetyzując logikę dostępu do danych dla kolekcji 'documents' i GridFS.

CHUNK_SIZE = 1024 * 1024

class DocumentRepository:
    def __init__(self, database: AsyncIOMotorDatabase, file_system: AsyncIOMotorGridFSBucket):
        """Initializes the repository with a database instance."""
        self.db: AsyncIOMotorDatabase = database
        self.collection: AsyncIOMotorCollection = database.documents
        self.fs: AsyncIOMotorGridFSBucket = file_system

    async def _calculate_hash(self, content: bytes) -> str:
        """Computes a SHA-256 hash of the file contents."""
        sha256_hash = hashlib.sha256()
        sha256_hash.update(content)
        return f"sha256:{sha256_hash.hexdigest()}"

    async def create(
        self,
        document_data: DocumentCreate,
        file_content: bytes,
        file_name_for_gridfs: str,
    ) -> str:
        """
        Creates a new document: saves the file to GridFS and the metadata to the 'documents' collection.
        Returns the ID of the created document (as a string).
        """
        gridfs_file_id = None
        try:
            file_stream = io.BytesIO(file_content)
            gridfs_file_id = await self.fs.upload_from_stream(
                filename=file_name_for_gridfs,
                source=file_stream,
                metadata={
                    "contentType": document_data.original_format,
                    "originalFilename": document_data.original_filename,
                    "uploadTimestamp": datetime.now(timezone.utc),
                },
            )
            content_hash = await self._calculate_hash(file_content)

            doc_dict = document_data.model_dump(by_alias=True)
            doc_dict.update(
                {
                    "uploadTimestamp": datetime.now(timezone.utc),
                    "contentHash": content_hash,
                    "originalDocumentPath": f"gridfs:{str(gridfs_file_id)}",
                    "conversionStatus": ConversionStatus.STATUS_PENDING.value,
                    "analysisResult": None,
                    "normalizedText": None,
                }
            )

            result = await self.collection.insert_one(doc_dict)

            if not result.inserted_id:
                await self.fs.delete(gridfs_file_id)
                raise DatabaseException("Failed to insert document metadata.")
            
            return str(result.inserted_id)
        except Exception as e:
            print(f"Error in create document: {e}")
            if gridfs_file_id:
                try:
                    await self.fs.delete(gridfs_file_id)
                    print(f"Cleaned up GridFS file {gridfs_file_id} after error.")
                except Exception as cleanup_error:
                    print(
                        f"Error cleaning up GridFS file {gridfs_file_id}: {cleanup_error}"
                    )
            raise DatabaseException(f"Failed to create document with GridFS: {str(e)}")

    async def get_by_id(self, document_id: str) -> Optional[DocumentInDB]:
        """Retrieves a document from the database based on its ID."""
        if not ObjectId.is_valid(document_id):
            return None
        try:
            document_data = await self.collection.find_one({"_id": ObjectId(document_id)})
            
            if not document_data:
                return None
            
            return DocumentInDB.model_validate(document_data)
        except Exception as e:
            print(f"Error getting document {document_id}: {e}")
            raise DatabaseException(f"Failed to get document {document_id}: {str(e)}")

    async def get_list(
        self,
        page: int = 1,
        limit: int = 20,
        conversion_status: Optional[str] = None,
        original_format: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        query: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Gets a list of documents, with filtering and pagination taken into account."""
        try:
            filter_dict = {}

            if conversion_status:
                try:
                    filter_dict["conversionStatus"] = ConversionStatus(conversion_status).value
                except ValueError:
                    raise ValidationException(f"Invalid conversion status value: {conversion_status}")
                
            if original_format:
                filter_dict["originalFormat"] = original_format

            date_filter = {}

            if date_from:
                date_filter["$gte"] = date_from

            if date_to:
                date_filter["$lte"] = date_to

            if date_filter:
                filter_dict["uploadTimestamp"] = date_filter

            if query:
                filter_dict["$or"] = [
                    {"originalFilename": {"$regex": query, "$options": "i"}},
                ]

            total = await self.collection.count_documents(filter_dict)

            skip = (page - 1) * limit
            cursor = (
                self.collection.find(filter_dict)
                .sort("uploadTimestamp", -1)
                .skip(skip)
                .limit(limit)
            )

            documents_list = [DocumentInDB.model_validate(doc) async for doc in cursor]

            return {
                "total": total,
                "page": page,
                "limit": limit,
                "documents": documents_list,
            }
        except ValidationException as ve:
            raise ve
        except Exception as e:
            print(f"Error listing documents: {e}")
            raise DatabaseException(f"Failed to list documents: {str(e)}")

    async def update(
        self, document_id: str, document_update: DocumentUpdate
    ) -> Optional[DocumentInDB]:
        """Updates an existing document in the database."""
        if not ObjectId.is_valid(document_id):
            return None
        
        update_data = document_update.model_dump(exclude_unset=True, by_alias=True)

        mongo_update_set = {}

        try:
            normalized_text = update_data.pop("normalizedText", None)

            if normalized_text is not None:
                mongo_update_set["normalizedText"] = str(normalized_text) 

                if "conversionStatus" not in update_data:
                     update_data["conversionStatus"] = ConversionStatus.STATUS_COMPLETED.value
                if "conversionTimestamp" not in update_data:
                    update_data["conversionTimestamp"] = datetime.now(timezone.utc)
            else:
                 if document_update.normalized_text is None and 'normalizedText' in document_update.model_fields_set:
                    mongo_update_set["normalizedText"] = None

            for key, value in update_data.items():
                db_key = key

                if value is None and key not in ["conversionError", "analysisResult.error"]:
                    continue

                if isinstance(value, Enum):
                    mongo_update_set[db_key] = value.value
                elif isinstance(value, BaseModel):
                    nested_update = value.model_dump(by_alias=True, exclude_unset=True)
                    if nested_update:
                         for sub_key, sub_value in nested_update.items():
                              if sub_value is not None or (db_key == "analysisResult" and sub_key == "error"):
                                  mongo_update_set[f"{db_key}.{sub_key}"] = sub_value
                              elif db_key == "analysisResult" and sub_key == "detectedItems" and sub_value == []:
                                  mongo_update_set[f"{db_key}.{sub_key}"] = []
                else:
                    mongo_update_set[db_key] = value

            if not mongo_update_set:
                return await self.get_by_id(document_id)

            result = await self.collection.update_one(
                {"_id": ObjectId(document_id)},
                {"$set": mongo_update_set}
            )

            if result.matched_count == 0:
                return None

            return await self.get_by_id(document_id)

        except Exception as e:
            print(f"Error updating document {document_id}: {e}")
            raise DatabaseException(f"Failed to update document {document_id}: {str(e)}")

    async def delete(self, document_id: str) -> bool:
        """Removes a document (metadata) and associated file from GridFS."""
        if not ObjectId.is_valid(document_id):
            return False

        original_gridfs_file_id = None

        try:
            doc_meta = await self.collection.find_one(
                {"_id": ObjectId(document_id)},
                {"originalDocumentPath": 1}
            )
            if not doc_meta: return False

            orig_ref = doc_meta.get("originalDocumentPath")
            if orig_ref and orig_ref.startswith("gridfs:") and ObjectId.is_valid(orig_ref.split(":")[-1]):
                original_gridfs_file_id = ObjectId(orig_ref.split(":")[-1])

            delete_result = await self.collection.delete_one({"_id": ObjectId(document_id)})
            deleted_meta = delete_result.deleted_count > 0

            if original_gridfs_file_id:
                try:
                    await self.fs.delete(original_gridfs_file_id)
                    print(f"Successfully deleted original GridFS file {original_gridfs_file_id} for doc {document_id}")
                except Exception as gridfs_error:
                    print(f"Failed to delete original GridFS file {original_gridfs_file_id} for deleted doc {document_id}: {gridfs_error}")
            return deleted_meta

        except Exception as e:
            print(f"Error deleting document {document_id}: {e}")
            raise DatabaseException(f"Failed to delete document {document_id}: {str(e)}")

    async def download_gridfs_file(
        self, gridfs_file_id: ObjectId
    ) -> Tuple[AsyncIterator[bytes], Dict[str, Any]]:
        """Gets a file data stream and its metadata from GridFS."""
        gridfs_out_stream: Optional[AsyncIOMotorGridOut] = None
        try:
            gridfs_out_stream = await self.fs.open_download_stream(gridfs_file_id)

            metadata = gridfs_out_stream.metadata or {}
            if not isinstance(metadata, dict):
                print(f"Warning: GridFS metadata for {gridfs_file_id} is not a dict: {metadata}")
                metadata = {}

            async def file_chunk_generator(stream_to_yield_from: AsyncIOMotorGridOut) -> AsyncIterator[bytes]:
                try:
                    while True:
                        chunk = await stream_to_yield_from.readchunk()
                        if not chunk:
                            break
                        yield chunk
                finally:
                    if stream_to_yield_from:
                        try:
                            await stream_to_yield_from.close()
                            print(f"GridFS stream {gridfs_file_id} closed successfully by generator.")
                        except Exception as close_err:
                            print(f"Error closing GridFS stream {gridfs_file_id} inside generator: {close_err}")
                    else:
                        print(f"stream_to_yield_from was None in generator finally block for {gridfs_file_id}.")

            return file_chunk_generator(gridfs_out_stream), metadata

        except GridFSFileNotFound:
            raise FileNotFoundInGridFSException(f"File with GridFS ID '{gridfs_file_id}' not found.")
        except Exception as e:
            print(f"Error downloading GridFS file {gridfs_file_id}: {e}")
            if gridfs_out_stream:
                try:
                    await gridfs_out_stream.close()
                except Exception as cleanup_err:
                    print(f"Error closing GridFS stream during exception handling: {cleanup_err}")
            raise DatabaseException(f"Failed to download GridFS file {gridfs_file_id}: {str(e)}")