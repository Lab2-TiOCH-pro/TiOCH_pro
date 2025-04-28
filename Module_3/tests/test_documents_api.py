import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport 
from fastapi import status
from unittest.mock import AsyncMock
from typing import  AsyncIterator
from datetime import datetime, timezone, timedelta
from bson import ObjectId
import io

from app.main import app
from app.api.dependencies import get_document_service 
from app.services.documents import DocumentService
from app.models.documents import (
    DocumentInDB,
    DocumentList,
    ConversionStatus,
    AnalysisStatus,
    AnalysisResult,
)
from app.core.exceptions import (
    DocumentNotFoundException,
    ConflictException,
    FileNotFoundInGridFSException
)

pytestmark = pytest.mark.asyncio

@pytest.fixture
def mock_document_service() -> AsyncMock:
    mock = AsyncMock(spec=DocumentService)
    return mock

@pytest_asyncio.fixture
async def test_client(mock_document_service: AsyncMock) -> AsyncIterator[AsyncClient]:
    app.dependency_overrides[get_document_service] = lambda: mock_document_service
    
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides = {}

FAKE_OBJECT_ID = str(ObjectId())
FAKE_OBJECT_ID_2 = str(ObjectId())
TEST_EMAIL = "test@example.com"

def create_sample_doc_in_db(doc_id: str = FAKE_OBJECT_ID, **overrides) -> DocumentInDB:
    """Tworzy przykładowy obiekt DocumentInDB na potrzeby testów."""
    defaults = {
        "_id": ObjectId(doc_id),
        "originalFilename": "test.pdf",
        "originalFormat": "pdf",
        "uploaderEmail": TEST_EMAIL,
        "uploadTimestamp": datetime.now(timezone.utc) - timedelta(days=1),
        "sizeBytes": 12345,
        "contentHash": "sha256:abcdef123456",
        "originalDocumentPath": f"gridfs:{ObjectId()}",
        # "conversionStatus": ConversionStatus.STATUS_COMPLETED,
        # "conversionTimestamp": datetime.now(timezone.utc),
        # "normalizedTextRef": f"gridfs:{ObjectId()}",
        # "metadata": DocumentMetadata(pageCount=1),
        # "processingTimeSeconds": 1.5,
        # "analysisStatus": AnalysisStatus.NOT_STARTED,
        # "analysisResult": None,
    }

    data_for_model = {**defaults, **overrides}

    pydantic_data = {}
    for key, value in data_for_model.items():
        field_info = DocumentInDB.model_fields.get(key)
        alias = getattr(field_info, 'alias', key) if field_info else key
        pydantic_data[alias if alias else key] = value

    return DocumentInDB.model_validate(pydantic_data)


async def mock_async_file_generator(content: bytes) -> AsyncIterator[bytes]:
    """Pomocniczy generator asynchroniczny do mockowania streamingu plików."""
    chunk_size = 1024
    for i in range(0, len(content), chunk_size):
        yield content[i:i + chunk_size]


async def test_upload_single_document_success(test_client: AsyncClient, mock_document_service: AsyncMock):
    """Testuje pomyślny upload jednego pliku."""
    mock_document_service.create_document.return_value = FAKE_OBJECT_ID
    file_content = b"This is a test file content."
    files = {'files': ('test_upload.txt', io.BytesIO(file_content), 'text/plain')}
    data = {'uploader_email': TEST_EMAIL}

    response = await test_client.post("/api/documents", files=files, data=data)

    assert response.status_code == status.HTTP_207_MULTI_STATUS
    result = response.json()
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]['filename'] == 'test_upload.txt'
    assert result[0]['status'] == 'uploaded'
    assert result[0]['documentId'] == FAKE_OBJECT_ID
    assert result[0]['error'] is None

    mock_document_service.create_document.assert_awaited_once()

    call_args_info = mock_document_service.create_document.call_args
    positional_args = call_args_info[0]
    keyword_args = call_args_info[1]

    assert not positional_args

    assert keyword_args['file_name'] == 'test_upload.txt'
    assert keyword_args['file_format'] == 'txt'
    assert keyword_args['file_size'] == len(file_content)
    assert keyword_args['file_content'] == file_content
    assert keyword_args['uploader_email'] == TEST_EMAIL     


async def test_upload_multiple_documents(test_client: AsyncClient, mock_document_service: AsyncMock):
    """Testuje upload wielu plików, w tym jednego z błędem."""
    # Mockujemy, że pierwszy plik się uda, a drugi rzuci błąd
    mock_document_service.create_document.side_effect = [
        FAKE_OBJECT_ID,
    ]

    file_content1 = b"Content for file 1."
    file_content2 = b"" # Pusty plik powodujący błąd

    files_data = [
        ('files', ('file1.pdf', io.BytesIO(file_content1), 'application/pdf')),
        ('files', ('file2.txt', io.BytesIO(file_content2), 'text/plain'))
    ]
    data = {'uploader_email': TEST_EMAIL}

    response = await test_client.post("/api/documents", files=files_data, data=data)

    assert response.status_code == status.HTTP_207_MULTI_STATUS
    results = response.json()
    assert len(results) == 2

    assert results[0]['filename'] == 'file1.pdf'
    assert results[0]['status'] == 'uploaded'
    assert results[0]['documentId'] == FAKE_OBJECT_ID
    assert results[0]['error'] is None

    assert results[1]['filename'] == 'file2.txt'
    assert results[1]['status'] == 'failed'
    assert results[1]['documentId'] is None
    assert "Uploaded file cannot be empty." in results[1]['error']

    assert mock_document_service.create_document.await_count == 1


async def test_upload_document_missing_email(test_client: AsyncClient):
    """Testuje upload bez podania adresu email (powinien być błąd walidacji 422)."""
    file_content = b"Test content."
    files = {'files': ('test.txt', io.BytesIO(file_content), 'text/plain')}
  
    data = {}

    response = await test_client.post("/api/documents", files=files, data=data)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert "uploader_email" in response.text

async def test_upload_no_files(test_client: AsyncClient):
    """Testuje próbę uploadu bez załączenia plików."""
    data = {'uploader_email': TEST_EMAIL}
 
    response = await test_client.post("/api/documents", data=data)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


async def test_list_documents_success(test_client: AsyncClient, mock_document_service: AsyncMock):
    """Testuje pomyślne listowanie dokumentów."""
    doc1 = create_sample_doc_in_db(FAKE_OBJECT_ID)
    doc2 = create_sample_doc_in_db(FAKE_OBJECT_ID_2, originalFilename="report.docx", originalFormat="docx")
    expected_result = DocumentList(total=2, page=1, limit=20, documents=[doc1, doc2])

    mock_document_service.list_documents.return_value = expected_result.model_dump()

    response = await test_client.get("/api/documents", params={"page": 1, "limit": 20})

    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert result["total"] == 2
    assert result["page"] == 1
    assert result["limit"] == 20
    assert len(result["documents"]) == 2

    assert result["documents"][0]["_id"] == FAKE_OBJECT_ID
    assert result["documents"][1]["_id"] == FAKE_OBJECT_ID_2

    mock_document_service.list_documents.assert_awaited_once_with(
        page=1, limit=20, conversion_status=None, original_format=None, date_from=None, date_to=None, query=None
    )


async def test_list_documents_with_filter(test_client: AsyncClient, mock_document_service: AsyncMock):
    """Testuje listowanie z użyciem filtrów."""
    mock_document_service.list_documents.return_value = DocumentList(total=0, page=1, limit=10, documents=[]).model_dump()

    await test_client.get("/api/documents", params={
        "page": 2,
        "limit": 10,
        "conversion_status": "pending",
        "original_format": "xlsx",
        "query": "raport"
    })

    mock_document_service.list_documents.assert_awaited_once_with(
        page=2, limit=10, conversion_status="pending", original_format="xlsx", date_from=None, date_to=None, query="raport"
    )


async def test_get_document_success(test_client: AsyncClient, mock_document_service: AsyncMock):
    """Testuje pomyślne pobranie jednego dokumentu."""
    expected_doc = create_sample_doc_in_db(FAKE_OBJECT_ID)
    mock_document_service.get_document.return_value = expected_doc

    response = await test_client.get(f"/api/documents/{FAKE_OBJECT_ID}")

    assert response.status_code == status.HTTP_200_OK

    expected_json_compatible_dict = expected_doc.model_dump(mode='json', by_alias=True)
    assert response.json() == expected_json_compatible_dict

    mock_document_service.get_document.assert_awaited_once_with(FAKE_OBJECT_ID)


async def test_get_document_not_found(test_client: AsyncClient, mock_document_service: AsyncMock):
    """Testuje pobranie dokumentu, który nie istnieje (404)."""
    mock_document_service.get_document.side_effect = DocumentNotFoundException(f"Document {FAKE_OBJECT_ID} not found")

    response = await test_client.get(f"/api/documents/{FAKE_OBJECT_ID}")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "not found" in response.json()["detail"]
    mock_document_service.get_document.assert_awaited_once_with(FAKE_OBJECT_ID)


async def test_update_document_success(test_client: AsyncClient, mock_document_service: AsyncMock):
    """Testuje pomyślną aktualizację dokumentu."""
    update_payload = {"conversionStatus": "completed", "processingTimeSeconds": 5.0}

    updated_doc = create_sample_doc_in_db(FAKE_OBJECT_ID, conversionStatus=ConversionStatus.STATUS_COMPLETED, processingTimeSeconds=5.0)
    mock_document_service.update_document.return_value = updated_doc

    response = await test_client.patch(f"/api/documents/{FAKE_OBJECT_ID}", json=update_payload)

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["conversionStatus"] == "completed"
    assert response.json()["_id"] == FAKE_OBJECT_ID

    mock_document_service.update_document.assert_awaited_once()
    call_args = mock_document_service.update_document.call_args[0]
    assert call_args[0] == FAKE_OBJECT_ID
    update_arg = call_args[1]
    assert update_arg.conversion_status == ConversionStatus.STATUS_COMPLETED
    assert update_arg.processing_time_seconds == 5.0
    assert update_arg.normalized_text is None


# async def test_update_document_with_normalized_text(test_client: AsyncClient, mock_document_service: AsyncMock):
#     """Testuje aktualizację z polem normalizedText."""
#     update_payload = {"normalizedText": "To jest znormalizowany tekst."}

#     updated_doc = create_sample_doc_in_db(FAKE_OBJECT_ID, normalizedTextRef=f"gridfs:{ObjectId()}")
#     mock_document_service.update_document.return_value = updated_doc

#     response = await test_client.patch(f"/api/documents/{FAKE_OBJECT_ID}", json=update_payload)

#     assert response.status_code == status.HTTP_200_OK
#     assert response.json()["normalizedTextRef"] is not None

#     mock_document_service.update_document.assert_awaited_once()
#     call_args = mock_document_service.update_document.call_args[0]
#     update_arg = call_args[1]
#     assert update_arg.normalized_text == "To jest znormalizowany tekst."


async def test_update_document_not_found(test_client: AsyncClient, mock_document_service: AsyncMock):
    """Testuje aktualizację nieistniejącego dokumentu."""
    mock_document_service.update_document.side_effect = DocumentNotFoundException(f"Document {FAKE_OBJECT_ID} not found")
    update_payload = {"conversionStatus": "failed"}

    response = await test_client.patch(f"/api/documents/{FAKE_OBJECT_ID}", json=update_payload)

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "not found" in response.json()["detail"]

async def test_delete_document_success(test_client: AsyncClient, mock_document_service: AsyncMock):
    """Testuje pomyślne usunięcie dokumentu."""
    mock_document_service.delete_document.return_value = True # Symuluje pomyślne usunięcie

    response = await test_client.delete(f"/api/documents/{FAKE_OBJECT_ID}")

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["success"] is True
    assert response.json()["documentId"] == FAKE_OBJECT_ID
    mock_document_service.delete_document.assert_awaited_once_with(FAKE_OBJECT_ID)


async def test_delete_document_not_found(test_client: AsyncClient, mock_document_service: AsyncMock):
    """Testuje usuwanie nieistniejącego dokumentu."""
    mock_document_service.delete_document.side_effect = DocumentNotFoundException(f"Document {FAKE_OBJECT_ID} not found")

    response = await test_client.delete(f"/api/documents/{FAKE_OBJECT_ID}")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "not found" in response.json()["detail"]
    mock_document_service.delete_document.assert_awaited_once_with(FAKE_OBJECT_ID)

# async def test_initiate_analysis_success(test_client: AsyncClient, mock_document_service: AsyncMock):
#     """Testuje pomyślne zainicjowanie analizy."""

#     updated_doc = create_sample_doc_in_db(
#         FAKE_OBJECT_ID,
#         analysisStatus=AnalysisStatus.PENDING,
#         analysisResult=AnalysisResult(status=AnalysisStatus.PENDING, timestamp=datetime.now(timezone.utc))
#     )
#     mock_document_service.initiate_document_analysis.return_value = updated_doc

#     response = await test_client.post(f"/api/documents/{FAKE_OBJECT_ID}/analysis")

#     assert response.status_code == status.HTTP_200_OK
#     result = response.json()
#     assert result["analysisStatus"] == "pending"
#     assert result["analysisResult"]["status"] == "pending"
#     assert result["_id"] == FAKE_OBJECT_ID
#     mock_document_service.initiate_document_analysis.assert_awaited_once_with(FAKE_OBJECT_ID)


# async def test_initiate_analysis_not_found(test_client: AsyncClient, mock_document_service: AsyncMock):
#     """Testuje inicjację analizy dla nieistniejącego dokumentu."""
#     mock_document_service.initiate_document_analysis.side_effect = DocumentNotFoundException("Doc not found")

#     response = await test_client.post(f"/api/documents/{FAKE_OBJECT_ID}/analysis")

#     assert response.status_code == status.HTTP_404_NOT_FOUND
#     assert "not found" in response.json()["detail"]


# async def test_initiate_analysis_conflict(test_client: AsyncClient, mock_document_service: AsyncMock):
#     """Testuje inicjację analizy, gdy jest to niemożliwe (np. zły status konwersji)."""
#     mock_document_service.initiate_document_analysis.side_effect = ConflictException("Cannot initiate analysis, conversion not completed.")

#     response = await test_client.post(f"/api/documents/{FAKE_OBJECT_ID}/analysis")

#     assert response.status_code == status.HTTP_409_CONFLICT
#     assert "Cannot initiate analysis" in response.json()["detail"]

async def test_download_original_content_success(test_client: AsyncClient, mock_document_service: AsyncMock):
    """Testuje pomyślne pobranie oryginalnej zawartości."""
    file_content = b"Original file binary content \x00\x01\x02"
    metadata = {"contentType": "application/pdf", "originalFilename": "original.pdf"}

    mock_document_service.get_original_document_content.return_value = (
        mock_async_file_generator(file_content),
        metadata
    )

    response = await test_client.get(f"/api/documents/{FAKE_OBJECT_ID}/content/original")

    assert response.status_code == status.HTTP_200_OK
    assert response.content == file_content
    assert response.headers["content-type"] == "application/pdf"
    assert "attachment; filename=\"original.pdf\"" in response.headers["content-disposition"]
    mock_document_service.get_original_document_content.assert_awaited_once_with(FAKE_OBJECT_ID)


async def test_download_original_content_not_found(test_client: AsyncClient, mock_document_service: AsyncMock):
    """Testuje pobieranie oryginalnej zawartości, gdy plik nie istnieje."""
    mock_document_service.get_original_document_content.side_effect = FileNotFoundInGridFSException("Original file not found in GridFS")

    response = await test_client.get(f"/api/documents/{FAKE_OBJECT_ID}/content/original")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "not found" in response.json()["detail"]

# async def test_download_normalized_text_success(test_client: AsyncClient, mock_document_service: AsyncMock):
#     """Testuje pomyślne pobranie znormalizowanego tekstu."""
#     text_content = "Zażółć gęślą jaźń.\nNormalized text."
#     byte_content = text_content.encode('utf-8')
#     metadata = {"contentType": "text/plain; charset=utf-8", "filename": f"normalized_{FAKE_OBJECT_ID}.txt"}
#     mock_document_service.get_normalized_document_text.return_value = (
#         mock_async_file_generator(byte_content),
#         metadata
#     )

#     response = await test_client.get(f"/api/documents/{FAKE_OBJECT_ID}/content/normalized")

#     assert response.status_code == status.HTTP_200_OK
#     # Odpowiedź jest w bajtach, dekodujemy do porównania
#     assert response.content.decode('utf-8') == text_content
#     assert response.headers["content-type"] == "text/plain; charset=utf-8"
#     assert f"attachment; filename=\"normalized_{FAKE_OBJECT_ID}.txt\"" in response.headers["content-disposition"]
#     mock_document_service.get_normalized_document_text.assert_awaited_once_with(FAKE_OBJECT_ID)


# async def test_download_normalized_text_not_found(test_client: AsyncClient, mock_document_service: AsyncMock):
#     """Testuje pobieranie znormalizowanego tekstu, gdy go nie ma."""
#     mock_document_service.get_normalized_document_text.side_effect = FileNotFoundInGridFSException("Normalized text not found")

#     response = await test_client.get(f"/api/documents/{FAKE_OBJECT_ID}/content/normalized")

#     assert response.status_code == status.HTTP_404_NOT_FOUND
#     assert "not found" in response.json()["detail"]