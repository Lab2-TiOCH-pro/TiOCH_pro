import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock
from bson import ObjectId
from datetime import datetime, timedelta, timezone
import io
from gridfs.errors import NoFile as GridFSFileNotFound

from app.db.repositories.documents import DocumentRepository
from app.models.documents import DocumentCreate, DocumentInDB
from app.core.exceptions import DatabaseException, FileNotFoundInGridFSException

from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorCollection, AsyncIOMotorGridFSBucket, AsyncIOMotorGridOut, AsyncIOMotorCursor

pytestmark = pytest.mark.asyncio

FAKE_OBJECT_ID = ObjectId()
FAKE_OBJECT_ID_STR = str(FAKE_OBJECT_ID)
FAKE_OBJECT_ID_2 = ObjectId()
FAKE_OBJECT_ID_2_STR = str(FAKE_OBJECT_ID_2)
TEST_EMAIL = "test@example.com"
NOW = datetime.now(timezone.utc)

@pytest.fixture
def mock_db() -> AsyncMock:
    return AsyncMock(spec=AsyncIOMotorDatabase)

@pytest.fixture
def mock_collection() -> AsyncMock:
    mock = AsyncMock(spec=AsyncIOMotorCollection)
    return mock

@pytest.fixture
def mock_fs() -> AsyncMock:
    return AsyncMock(spec=AsyncIOMotorGridFSBucket)

@pytest.fixture
def document_repository(mock_db: AsyncMock, mock_collection: AsyncMock, mock_fs: AsyncMock) -> DocumentRepository:
    mock_db.documents = mock_collection
    mock_db.__getitem__.return_value = mock_collection
    return DocumentRepository(database=mock_db, file_system=mock_fs)

async def mock_upload_from_stream(*args, **kwargs):
    await asyncio.sleep(0)
    return FAKE_OBJECT_ID

async def mock_insert_one(*args, **kwargs):
    await asyncio.sleep(0)
    mock_result = MagicMock()
    mock_result.inserted_id = FAKE_OBJECT_ID
    return mock_result

async def mock_find_one(return_value=None, *args, **kwargs):
    """Zwraca przekazaną wartość (słownik lub None) po await."""
    await asyncio.sleep(0)
    return return_value

async def mock_delete_one(deleted_count=0, *args, **kwargs):
    """Zwraca obiekt wyniku z deleted_count po await."""
    await asyncio.sleep(0)
    mock_result = MagicMock()
    mock_result.deleted_count = deleted_count
    return mock_result

async def mock_fs_delete(*args, **kwargs):
    """Symuluje awaitable fs.delete (nic nie zwraca)."""
    print(f"Mock fs.delete called with args: {args}")
    await asyncio.sleep(0)
    return None 



async def test_create_repo_success(document_repository: DocumentRepository, mock_collection: AsyncMock, mock_fs: AsyncMock):

    doc_create = DocumentCreate(originalFilename="repo_create.txt", originalFormat="txt", uploaderEmail=TEST_EMAIL)
    file_size = 150; file_content = b"repo content" * 10; file_name_for_gridfs = "repo_create.txt"
    mock_fs.upload_from_stream.side_effect = mock_upload_from_stream
    mock_collection.insert_one.side_effect = mock_insert_one
 
    result_id_str = await document_repository.create(doc_create, file_content, file_name_for_gridfs)
 
    assert result_id_str == FAKE_OBJECT_ID_STR
    mock_fs.upload_from_stream.assert_called_once()
    fs_call_kwargs = mock_fs.upload_from_stream.call_args.kwargs
    assert fs_call_kwargs['filename'] == file_name_for_gridfs
    assert isinstance(fs_call_kwargs['source'], io.BytesIO)
    assert fs_call_kwargs['metadata']['originalFilename'] == doc_create.original_filename
    mock_collection.insert_one.assert_called_once()
    inserted_data = mock_collection.insert_one.call_args[0][0]
    assert inserted_data['originalFilename'] == doc_create.original_filename

    assert inserted_data['originalDocumentPath'] == f"gridfs:{FAKE_OBJECT_ID_STR}"
    assert "contentHash" in inserted_data


async def test_create_repo_gridfs_failure(document_repository: DocumentRepository, mock_collection: AsyncMock, mock_fs: AsyncMock):

    doc_create = DocumentCreate(originalFilename="fail.txt", originalFormat="txt", uploaderEmail=TEST_EMAIL)
    # Symuluj błąd w coroutine
    async def gridfs_boom(*args, **kwargs): raise Exception("GridFS Boom!")
    mock_fs.upload_from_stream.side_effect = gridfs_boom

    with pytest.raises(DatabaseException, match="Failed to create document with GridFS: GridFS Boom!"):
        await document_repository.create(doc_create, b"fail", "fail.txt")

    mock_collection.insert_one.assert_not_called()
    mock_fs.delete.assert_not_called()


async def test_create_repo_insert_failure(document_repository: DocumentRepository, mock_collection: AsyncMock, mock_fs: AsyncMock):

    doc_create = DocumentCreate(originalFilename="insert_fail.txt", originalFormat="txt", uploaderEmail=TEST_EMAIL)

    mock_fs.upload_from_stream.side_effect = mock_upload_from_stream
    # Symuluj błąd w coroutine insert_one
    async def insert_boom(*args, **kwargs): raise Exception("Mongo Insert Boom!")
    mock_collection.insert_one.side_effect = insert_boom

    mock_fs.delete.side_effect = mock_fs_delete

    with pytest.raises(DatabaseException, match="Failed to create document with GridFS: Mongo Insert Boom!"):
        await document_repository.create(doc_create, b"insert fail", "insert_fail.txt")

    mock_fs.upload_from_stream.assert_called_once()
    mock_fs.delete.assert_called_once_with(FAKE_OBJECT_ID)


async def test_get_by_id_repo_success(document_repository: DocumentRepository, mock_collection: AsyncMock):

    db_data = {
        "_id": FAKE_OBJECT_ID, "originalFilename": "found.txt", "originalFormat": "txt",
        "uploaderEmail": TEST_EMAIL, "uploadTimestamp": NOW, "sizeBytes": 10,
        "originalDocumentPath": f"gridfs:{ObjectId()}"
    }

    async def find_one_returns_data(*args, **kwargs): return db_data
    mock_collection.find_one.side_effect = find_one_returns_data

    result_doc = await document_repository.get_by_id(FAKE_OBJECT_ID_STR)

    assert isinstance(result_doc, DocumentInDB)
    assert result_doc.id == FAKE_OBJECT_ID
    assert result_doc.original_filename == "found.txt"
    mock_collection.find_one.assert_called_once_with({"_id": FAKE_OBJECT_ID})


async def test_get_by_id_repo_invalid_id(document_repository: DocumentRepository, mock_collection: AsyncMock):
    result_doc = await document_repository.get_by_id("invalid-id-string")

    assert result_doc is None
    mock_collection.find_one.assert_not_called()


async def test_get_by_id_repo_not_found(document_repository: DocumentRepository, mock_collection: AsyncMock):
    async def find_one_returns_none(*args, **kwargs): return None
    mock_collection.find_one.side_effect = find_one_returns_none

    result_doc = await document_repository.get_by_id(FAKE_OBJECT_ID_STR)

    assert result_doc is None
    mock_collection.find_one.assert_called_once_with({"_id": FAKE_OBJECT_ID})


async def test_delete_repo_success(document_repository: DocumentRepository, mock_collection: AsyncMock, mock_fs: AsyncMock):

    original_gridfs_id = ObjectId()
    db_data = {
        "_id": FAKE_OBJECT_ID,
        "originalDocumentPath": f"gridfs:{original_gridfs_id}",
    }

    async def find_one_returns_delete_data(*args, **kwargs): return db_data
    mock_collection.find_one.side_effect = find_one_returns_delete_data

    async def delete_one_returns_success(*args, **kwargs): return await mock_delete_one(deleted_count=1)
    mock_collection.delete_one.side_effect = delete_one_returns_success

    mock_fs.delete.side_effect = mock_fs_delete

    result = await document_repository.delete(FAKE_OBJECT_ID_STR)
    assert result is True

    mock_collection.find_one.assert_called_once_with(
        {"_id": FAKE_OBJECT_ID},
        {"originalDocumentPath": 1}
    )
    mock_collection.delete_one.assert_called_once_with({"_id": FAKE_OBJECT_ID})
    
    assert mock_fs.delete.call_count == 1

    mock_fs.delete.assert_called_once_with(original_gridfs_id)

async def test_get_list_repo_success(document_repository: DocumentRepository, mock_collection: AsyncMock):
    """Testuje pomyślne listowanie dokumentów z repo."""
    page = 2
    limit = 5
    doc_data_1 = { "_id": FAKE_OBJECT_ID, "originalFilename": "doc1.pdf", "originalFormat": "pdf", "uploaderEmail": TEST_EMAIL, "uploadTimestamp": NOW, "sizeBytes": 100}
    doc_data_2 = { "_id": FAKE_OBJECT_ID_2, "originalFilename": "doc2.txt", "originalFormat": "txt", "uploaderEmail": TEST_EMAIL, "uploadTimestamp": NOW - timedelta(days=1), "sizeBytes": 50}
    documents_from_db = [doc_data_1, doc_data_2]

    async def mock_count_documents(*args, **kwargs): return 12
    mock_collection.count_documents.side_effect = mock_count_documents

    mock_cursor = AsyncMock(spec=AsyncIOMotorCursor)

    mock_cursor.__aiter__.return_value = documents_from_db

    mock_collection.find.return_value = mock_cursor

    mock_cursor.sort.return_value = mock_cursor
    mock_cursor.skip.return_value = mock_cursor
    mock_cursor.limit.return_value = mock_cursor

    result_dict = await document_repository.get_list(page=page, limit=limit, original_format="pdf")

    expected_filter = {"originalFormat": "pdf"}
    expected_skip = (page - 1) * limit

    mock_collection.count_documents.assert_called_once_with(expected_filter)
    mock_collection.find.assert_called_once_with(expected_filter)
    mock_cursor.sort.assert_called_once_with("uploadTimestamp", -1)
    mock_cursor.skip.assert_called_once_with(expected_skip)
    mock_cursor.limit.assert_called_once_with(limit)

    assert result_dict["total"] == 12
    assert result_dict["page"] == page
    assert result_dict["limit"] == limit
    assert len(result_dict["documents"]) == 2

    assert isinstance(result_dict["documents"][0], DocumentInDB)
    assert isinstance(result_dict["documents"][1], DocumentInDB)
    assert result_dict["documents"][0].id == FAKE_OBJECT_ID
    assert result_dict["documents"][1].id == FAKE_OBJECT_ID_2
    assert result_dict["documents"][0].original_format == "pdf"


async def test_get_list_repo_no_results(document_repository: DocumentRepository, mock_collection: AsyncMock):
    """Testuje listowanie, gdy nie ma pasujących dokumentów."""
    page = 1
    limit = 10

    async def mock_count_documents(*args, **kwargs): return 0
    mock_collection.count_documents.side_effect = mock_count_documents

    mock_cursor = AsyncMock(spec=AsyncIOMotorCursor)

    mock_cursor.__aiter__.return_value = [] 
    mock_collection.find.return_value = mock_cursor
    mock_cursor.sort.return_value = mock_cursor
    mock_cursor.skip.return_value = mock_cursor
    mock_cursor.limit.return_value = mock_cursor

    result_dict = await document_repository.get_list(page=page, limit=limit)

    mock_collection.count_documents.assert_called_once_with({})
    mock_collection.find.assert_called_once_with({})
    mock_cursor.skip.assert_called_once_with(0)
    mock_cursor.limit.assert_called_once_with(limit)

    assert result_dict["total"] == 0
    assert result_dict["documents"] == []


async def test_download_gridfs_file_repo_success(document_repository: DocumentRepository, mock_fs: AsyncMock):
    """Testuje pomyślne pobranie pliku z GridFS."""

    gridfs_file_id = ObjectId()
    file_content = b"gridfs file content chunk1" + b"gridfs file content chunk2"
    metadata = {"filename": "gridfs_test.bin", "contentType": "application/octet-stream"}


    mock_stream = AsyncMock(spec=AsyncIOMotorGridOut)
    mock_stream.metadata = metadata
    chunks = [b"gridfs file content chunk1", b"gridfs file content chunk2", b'']
    chunk_iter = iter(chunks)

    async def mock_readchunk():
        await asyncio.sleep(0)
        return next(chunk_iter)
    mock_stream.readchunk = mock_readchunk
    mock_stream.close = AsyncMock()

    async def mock_open_stream_async(*args, **kwargs):
        await asyncio.sleep(0)
        return mock_stream
    mock_fs.open_download_stream.side_effect = mock_open_stream_async

    stream_generator, result_metadata = await document_repository.download_gridfs_file(gridfs_file_id)

    mock_fs.open_download_stream.assert_called_once_with(gridfs_file_id)
    assert result_metadata == metadata
    assert hasattr(stream_generator, '__aiter__') and hasattr(stream_generator, '__anext__')

    retrieved_content = b""
    async for chunk in stream_generator:
        retrieved_content += chunk

    assert retrieved_content == file_content

    await asyncio.sleep(0.01)
    mock_stream.close.assert_awaited_once()


async def test_download_gridfs_file_repo_not_found(document_repository: DocumentRepository, mock_fs: AsyncMock):
    """Testuje pobieranie, gdy plik nie istnieje w GridFS."""

    gridfs_file_id = ObjectId()

    async def raise_not_found(*args, **kwargs): raise GridFSFileNotFound("File not found")
    mock_fs.open_download_stream.side_effect = raise_not_found


    with pytest.raises(FileNotFoundInGridFSException, match=f"File with GridFS ID '{gridfs_file_id}' not found."):
        await document_repository.download_gridfs_file(gridfs_file_id)

    mock_fs.open_download_stream.assert_called_once_with(gridfs_file_id)


async def test_download_gridfs_file_repo_other_error(document_repository: DocumentRepository, mock_fs: AsyncMock):
    """Testuje inny błąd podczas pobierania z GridFS."""

    gridfs_file_id = ObjectId()

    async def raise_other_error(*args, **kwargs): raise Exception("Some download error")
    mock_fs.open_download_stream.side_effect = raise_other_error

    with pytest.raises(DatabaseException, match=f"Failed to download GridFS file {gridfs_file_id}: Some download error"):
        await document_repository.download_gridfs_file(gridfs_file_id)

    mock_fs.open_download_stream.assert_called_once_with(gridfs_file_id)