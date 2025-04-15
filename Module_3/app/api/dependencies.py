from fastapi import Depends
from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorGridFSBucket

from app.db.mongodb import get_db, get_gridfs_bucket
from app.db.repositories.documents import DocumentRepository
from app.services.documents import DocumentService

# Plik definiuje funkcje "zależności" (dependencies) używane przez FastAPI
# do wstrzykiwania instancji repozytoriów i serwisów do endpointów API.

# Zależność do tworzenia i dostarczania instancji DocumentRepository.
# Automatycznie pobiera połączenie do bazy danych (db) za pomocą zależności get_db.
def get_document_repository(
    db: AsyncIOMotorDatabase = Depends(get_db),
    fs: AsyncIOMotorGridFSBucket = Depends(get_gridfs_bucket)
) -> DocumentRepository:
    return DocumentRepository(db, fs)


# Zależność do tworzenia i dostarczania instancji DocumentService.
# Automatycznie pobiera instancję repozytorium (document_repository) za pomocą zależności get_document_repository.
def get_document_service(
    document_repository: DocumentRepository = Depends(get_document_repository),
) -> DocumentService:
    return DocumentService(document_repository)
