import pytest
from unittest.mock import AsyncMock
from bson import ObjectId

from test_documents_api import create_sample_doc_in_db, mock_async_file_generator
from app.services.documents import DocumentService
from app.db.repositories.documents import DocumentRepository
from app.models.documents import (
    DocumentList,
    DocumentCreate,
    DocumentUpdate,
    ConversionStatus,
)
from app.core.exceptions import (
    DocumentNotFoundException,
    ValidationException,
    FileNotFoundInGridFSException
)

pytestmark = pytest.mark.asyncio

FAKE_OBJECT_ID = str(ObjectId())
FAKE_OBJECT_ID_2 = str(ObjectId())
TEST_EMAIL = "test@example.com"

@pytest.fixture
def mock_document_repository() -> AsyncMock:
    """Tworzy mock dla DocumentRepository."""
    return AsyncMock(spec=DocumentRepository)

@pytest.fixture
def document_service(mock_document_repository: AsyncMock) -> DocumentService:
    """Tworzy instancję DocumentService z zamockowanym repozytorium."""
    return DocumentService(document_repository=mock_document_repository)

async def test_create_document_service_success(document_service: DocumentService, mock_document_repository: AsyncMock):
    """Testuje pomyślne tworzenie dokumentu w serwisie."""
    mock_document_repository.create.return_value = FAKE_OBJECT_ID
    file_name = "service_test.txt"
    file_format = "txt"
    file_content = b"Service test"

    result_id = await document_service.create_document(
        file_name=file_name,
        file_format=file_format,
        file_content=file_content,
        uploader_email=TEST_EMAIL,
    )

    assert result_id == FAKE_OBJECT_ID

    mock_document_repository.create.assert_awaited_once()
    call_args = mock_document_repository.create.call_args[0]
    create_arg: DocumentCreate = call_args[0]

    assert isinstance(create_arg, DocumentCreate)
    assert create_arg.original_filename == file_name
    assert create_arg.original_format == file_format
    assert create_arg.uploader_email == TEST_EMAIL
    assert call_args[1] == file_content
    assert call_args[2] == file_name


@pytest.mark.parametrize("file_name, file_size, expected_error", [
    ("", 100, "File name is required."),
    ("test.txt", 0, "File content cannot be empty."),
    ("test.txt", -10, "File content cannot be empty."),
])

async def test_create_document_service_validation_error(document_service: DocumentService, mock_document_repository: AsyncMock, file_name, file_size, expected_error):
    """Testuje błędy walidacji przy tworzeniu dokumentu w serwisie."""

    file_format = "txt"
    file_content = b"abc" if file_size > 0 else b""

    with pytest.raises(ValidationException, match=expected_error):
        await document_service.create_document(
            file_name=file_name,
            file_format=file_format,
            file_content=file_content,
            uploader_email=TEST_EMAIL,
        )
    # Upewnienie się, że repozytorium NIE zostało wywołane
    mock_document_repository.create.assert_not_awaited()


async def test_get_document_service_success(document_service: DocumentService, mock_document_repository: AsyncMock):
    """Testuje pomyślne pobranie dokumentu przez serwis."""

    expected_doc = create_sample_doc_in_db(FAKE_OBJECT_ID)
    mock_document_repository.get_by_id.return_value = expected_doc

    result_doc = await document_service.get_document(FAKE_OBJECT_ID)

    assert result_doc == expected_doc
    mock_document_repository.get_by_id.assert_awaited_once_with(FAKE_OBJECT_ID)


async def test_get_document_service_not_found(document_service: DocumentService, mock_document_repository: AsyncMock):
    """Testuje pobranie nieistniejącego dokumentu przez serwis."""

    mock_document_repository.get_by_id.return_value = None

    with pytest.raises(DocumentNotFoundException, match=f"Document with ID {FAKE_OBJECT_ID} not found"):
        await document_service.get_document(FAKE_OBJECT_ID)
    mock_document_repository.get_by_id.assert_awaited_once_with(FAKE_OBJECT_ID)


async def test_list_documents_service(document_service: DocumentService, mock_document_repository: AsyncMock):
    """Testuje listowanie dokumentów przez serwis."""

    expected_list_dict = {"total": 0, "page": 1, "limit": 20, "documents": []}
    mock_document_repository.get_list.return_value = expected_list_dict


    result_list = await document_service.list_documents(page=1, limit=20, original_format="pdf")

    assert isinstance(result_list, DocumentList)
    assert result_list.total == 0
    assert result_list.page == 1
    assert result_list.limit == 20
    assert result_list.documents == []

    mock_document_repository.get_list.assert_awaited_once_with(
        page=1, limit=20, conversion_status=None, original_format="pdf",
        date_from=None, date_to=None, query=None
    )


async def test_update_document_service_success(document_service: DocumentService, mock_document_repository: AsyncMock):
    """Testuje pomyślną aktualizację dokumentu przez serwis."""

    update_data = DocumentUpdate(conversionStatus=ConversionStatus.STATUS_FAILED)
    updated_doc = create_sample_doc_in_db(FAKE_OBJECT_ID, conversionStatus=ConversionStatus.STATUS_FAILED)
    mock_document_repository.update.return_value = updated_doc


    result_doc = await document_service.update_document(FAKE_OBJECT_ID, update_data)

 
    assert result_doc == updated_doc
    mock_document_repository.update.assert_awaited_once_with(FAKE_OBJECT_ID, update_data)
    # Upewnienie się, że get_by_id nie było wołane w tym scenariuszu
    mock_document_repository.get_by_id.assert_not_awaited()


async def test_update_document_service_not_found(document_service: DocumentService, mock_document_repository: AsyncMock):
    """Testuje aktualizację nieistniejącego dokumentu przez serwis."""

    update_data = DocumentUpdate(conversionStatus=ConversionStatus.STATUS_FAILED)

    mock_document_repository.update.return_value = None
    # Repo.get_by_id  zwraca None, symulując brak dokumentu
    mock_document_repository.get_by_id.return_value = None


    with pytest.raises(DocumentNotFoundException, match=f"Document with ID '{FAKE_OBJECT_ID}' not found for update."):
        await document_service.update_document(FAKE_OBJECT_ID, update_data)


    mock_document_repository.update.assert_awaited_once_with(FAKE_OBJECT_ID, update_data)
    mock_document_repository.get_by_id.assert_awaited_once_with(FAKE_OBJECT_ID)


async def test_delete_document_service_success(document_service: DocumentService, mock_document_repository: AsyncMock):
    """Testuje pomyślne usunięcie dokumentu przez serwis."""

    mock_document_repository.delete.return_value = True

    result = await document_service.delete_document(FAKE_OBJECT_ID)

    assert result is True
    mock_document_repository.delete.assert_awaited_once_with(FAKE_OBJECT_ID)


async def test_delete_document_service_not_found(document_service: DocumentService, mock_document_repository: AsyncMock):
    """Testuje usunięcie nieistniejącego dokumentu przez serwis."""

    mock_document_repository.delete.return_value = False

    with pytest.raises(DocumentNotFoundException, match=f"Document with ID {FAKE_OBJECT_ID} not found for deletion"):
        await document_service.delete_document(FAKE_OBJECT_ID)
    mock_document_repository.delete.assert_awaited_once_with(FAKE_OBJECT_ID)

async def test_get_original_document_content_service_success(document_service: DocumentService, mock_document_repository: AsyncMock):
    """Testuje pomyślne pobranie oryginalnej zawartości przez serwis."""

    doc_id = FAKE_OBJECT_ID
    gridfs_id = ObjectId()

    existing_doc = create_sample_doc_in_db(doc_id, originalDocumentPath=f"gridfs:{gridfs_id}")
    file_content = b"original content"
    metadata = {"contentType": "text/plain"}

    mock_document_repository.get_by_id.return_value = existing_doc
    mock_document_repository.download_gridfs_file.return_value = (mock_async_file_generator(file_content), metadata)


    stream_gen, result_metadata = await document_service.get_original_document_content(doc_id)


    assert result_metadata == metadata

    retrieved_content = b"".join([chunk async for chunk in stream_gen])
    assert retrieved_content == file_content
    mock_document_repository.get_by_id.assert_awaited_once_with(doc_id)
    mock_document_repository.download_gridfs_file.assert_awaited_once_with(gridfs_id)


async def test_get_original_document_content_service_no_ref(document_service: DocumentService, mock_document_repository: AsyncMock):
    """Testuje pobranie oryginalnej zawartości, gdy brakuje referencji GridFS."""

    doc_id = FAKE_OBJECT_ID

    existing_doc = create_sample_doc_in_db(doc_id, originalDocumentPath=None)
    mock_document_repository.get_by_id.return_value = existing_doc


    with pytest.raises(FileNotFoundInGridFSException, match="No valid GridFS reference found"):
        await document_service.get_original_document_content(doc_id)
    mock_document_repository.get_by_id.assert_awaited_once_with(doc_id)
    mock_document_repository.download_gridfs_file.assert_not_awaited()