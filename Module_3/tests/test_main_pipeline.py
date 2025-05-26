import pytest
from unittest.mock import AsyncMock, MagicMock, patch, ANY
from bson import ObjectId
import datetime
import httpx
from copy import deepcopy

from app.main import process_document_pipeline
from app.db.repositories.documents import DocumentRepository
from app.models.documents import (
    DocumentUpdate,
    ConversionStatus,
    AnalysisStatus
)
from app.core.exceptions import FileNotFoundInGridFSException


pytestmark = pytest.mark.asyncio

DOC_ID_OBJ = ObjectId()
DOC_ID_STR = str(DOC_ID_OBJ)
GRIDFS_ORIG_ID_OBJ = ObjectId()
GRIDFS_ORIG_ID_STR = str(GRIDFS_ORIG_ID_OBJ)
GRIDFS_TEXT_ID_OBJ = ObjectId()
GRIDFS_TEXT_ID_STR = str(GRIDFS_TEXT_ID_OBJ)

TEST_CONVERSION_URL = "http://fake-conversion.com/file"
TEST_DETECTION_URL = "http://fake-detection.com/detect"

BASE_CHANGE_EVENT = {
    "documentKey": {"_id": DOC_ID_OBJ},
    "fullDocument": {
        "_id": DOC_ID_OBJ,
        "originalFilename": "test_pipeline.pdf",
        "originalDocumentPath": f"gridfs:{GRIDFS_ORIG_ID_STR}",
        "conversionStatus": ConversionStatus.STATUS_PENDING.value,
        "analysisStatus": AnalysisStatus.NOT_STARTED.value,
    }
}

ORIGINAL_FILE_CONTENT = b"Original PDF content simulation"
NORMALIZED_TEXT_CONTENT = "This is the normalized text from Module 2."
MOCK_METADATA_DICT = {"filename": "test_pipeline.pdf", "size": 12345, "date": datetime.datetime.now(datetime.timezone.utc).isoformat()}
MOCK_DETECTION_RESULTS = [{"type": "EMAIL", "value": "test@example.com", "label": "EMAIL"}]

@pytest.fixture
def mock_repo() -> AsyncMock:
    repo = AsyncMock(spec=DocumentRepository)
    repo.update = AsyncMock(return_value=None)
    async def default_download(*args, **kwargs):
        metadata = {"contentType": "application/pdf", "originalFilename": "test_pipeline.pdf"}
        async def generator(): yield ORIGINAL_FILE_CONTENT
        return generator(), metadata
    repo.download_gridfs_file = AsyncMock(side_effect=default_download)
    return repo

@pytest.fixture
def mock_http_response() -> MagicMock:
    def _create_mock_response(status_code=200, json_data=None, text_data=None, error=None, request_url=None):
        resp = AsyncMock(spec=httpx.Response)
        resp.status_code = status_code
        resp.json = MagicMock(return_value=json_data)
        resp.text = text_data if text_data is not None else str(json_data or "")
        mock_request = AsyncMock(spec=httpx.Request)
        mock_request.url = httpx.URL(request_url or "http://mockurl.com")
        resp.request = mock_request
        if status_code >= 400:
            http_error = httpx.HTTPStatusError(f"{status_code} Error", request=mock_request, response=resp)
            resp.raise_for_status = MagicMock(side_effect=http_error)
        else:
            resp.raise_for_status = MagicMock()
        return resp
    return _create_mock_response

async def test_pipeline_happy_path(mock_repo: AsyncMock, mock_http_response: MagicMock):
    """Testuje pomyślny przebieg całego pipeline."""
    change_event = deepcopy(BASE_CHANGE_EVENT)
    m2_response = mock_http_response(200, {"text": NORMALIZED_TEXT_CONTENT, "metadata": MOCK_METADATA_DICT}, request_url=TEST_CONVERSION_URL)
    m4_response = mock_http_response(200, MOCK_DETECTION_RESULTS, request_url=TEST_DETECTION_URL)

    with patch('app.main.httpx.AsyncClient') as MockClient:
        mock_client_instance = AsyncMock()
        mock_client_instance.post = AsyncMock(side_effect=[m2_response, m4_response])
        MockClient.return_value.__aenter__.return_value = mock_client_instance
        await process_document_pipeline(change_event, mock_repo, TEST_CONVERSION_URL, TEST_DETECTION_URL)

    mock_repo.download_gridfs_file.assert_awaited_once_with(GRIDFS_ORIG_ID_OBJ)
    assert mock_client_instance.post.await_count == 2
    m2_call = mock_client_instance.post.await_args_list[0]
    assert m2_call.args[0] == TEST_CONVERSION_URL; assert 'files' in m2_call.kwargs
    m4_call = mock_client_instance.post.await_args_list[1]
    assert m4_call.args[0] == TEST_DETECTION_URL; assert m4_call.kwargs.get('json') == {"text": NORMALIZED_TEXT_CONTENT}

    assert mock_repo.update.await_count == 2
    update1_call_args = mock_repo.update.await_args_list[0].args
    update1_payload: DocumentUpdate = update1_call_args[1]
    assert update1_payload.conversion_status == ConversionStatus.STATUS_COMPLETED
    assert update1_payload.normalized_text == NORMALIZED_TEXT_CONTENT
    assert update1_payload.metadata.filename == MOCK_METADATA_DICT["filename"]
    assert update1_payload.conversion_timestamp is not None

    update2_call_args = mock_repo.update.await_args_list[1].args
    update2_payload: DocumentUpdate = update2_call_args[1]
    assert update2_payload.analysis_result.status == AnalysisStatus.COMPLETED
    assert update2_payload.analysis_result.detected_items == MOCK_DETECTION_RESULTS
    assert update2_payload.analysis_result.timestamp is not None
    assert update2_payload.analysis_result.error is None

async def test_pipeline_m2_http_error(mock_repo: AsyncMock, mock_http_response: MagicMock):
    change_event = deepcopy(BASE_CHANGE_EVENT)
    m2_response = mock_http_response(status_code=500, text_data="Internal Server Error", request_url=TEST_CONVERSION_URL)
    with patch('app.main.httpx.AsyncClient') as MockClient:
        mock_client_instance = AsyncMock(); mock_client_instance.post = AsyncMock(return_value=m2_response)
        MockClient.return_value.__aenter__.return_value = mock_client_instance
        await process_document_pipeline(change_event, mock_repo, TEST_CONVERSION_URL, TEST_DETECTION_URL)

    mock_repo.download_gridfs_file.assert_awaited_once()
    mock_client_instance.post.assert_awaited_once_with(TEST_CONVERSION_URL, files=ANY)
    m2_response.raise_for_status.assert_called_once()
    mock_repo.update.assert_awaited_once()
    update_payload: DocumentUpdate = mock_repo.update.await_args_list[0].args[1]
    assert update_payload.conversion_status == ConversionStatus.STATUS_FAILED
    assert "Error from Conversion(M2) (500)" in update_payload.conversion_error
    assert "Internal Server Error" in update_payload.conversion_error

async def test_pipeline_m2_network_error(mock_repo: AsyncMock, mock_http_response: MagicMock):
    change_event = deepcopy(BASE_CHANGE_EVENT)
    with patch('app.main.httpx.AsyncClient') as MockClient:
        mock_client_instance = AsyncMock(); mock_client_instance.post = AsyncMock(side_effect=httpx.RequestError("Connection refused"))
        MockClient.return_value.__aenter__.return_value = mock_client_instance
        await process_document_pipeline(change_event, mock_repo, TEST_CONVERSION_URL, TEST_DETECTION_URL)

    mock_repo.download_gridfs_file.assert_awaited_once()
    mock_client_instance.post.assert_awaited_once_with(TEST_CONVERSION_URL, files=ANY)
    mock_repo.update.assert_awaited_once()
    update_payload: DocumentUpdate = mock_repo.update.await_args_list[0].args[1]
    assert update_payload.conversion_status == ConversionStatus.STATUS_FAILED
    assert "Network error calling Conversion(M2)" in update_payload.conversion_error
    assert "Connection refused" in update_payload.conversion_error

async def test_pipeline_m2_response_missing_text(mock_repo: AsyncMock, mock_http_response: MagicMock):
    """Testuje odpowiedź z M2 bez pola 'text', ale z poprawnym 'metadata'."""
    change_event = deepcopy(BASE_CHANGE_EVENT)
    m2_response = mock_http_response(200, {"metadata": MOCK_METADATA_DICT})
    with patch('app.main.httpx.AsyncClient') as MockClient:
        mock_client_instance = AsyncMock(); mock_client_instance.post = AsyncMock(return_value=m2_response)
        MockClient.return_value.__aenter__.return_value = mock_client_instance
        await process_document_pipeline(change_event, mock_repo, TEST_CONVERSION_URL, TEST_DETECTION_URL)

    mock_repo.download_gridfs_file.assert_awaited_once()
    mock_client_instance.post.assert_awaited_once()

    assert mock_repo.update.await_count == 2

    update1_payload: DocumentUpdate = mock_repo.update.await_args_list[0].args[1]
    assert update1_payload.conversion_status == ConversionStatus.STATUS_COMPLETED
    assert getattr(update1_payload, 'normalized_text', '__SENTINEL__') is None
    assert update1_payload.metadata.filename == MOCK_METADATA_DICT["filename"]
    assert update1_payload.metadata.size == MOCK_METADATA_DICT["size"]
    assert update1_payload.conversion_timestamp is not None
    assert update1_payload.conversion_error is None

    update2_payload: DocumentUpdate = mock_repo.update.await_args_list[1].args[1]
    assert update2_payload.analysis_result is not None
    assert update2_payload.analysis_result.status == AnalysisStatus.SKIPPED
    assert "No text from conversion" in update2_payload.analysis_result.error


async def test_pipeline_conversion_ok_and_text_none_skip_detection(mock_repo: AsyncMock, mock_http_response: MagicMock):
    """Testuje przypadek: konwersja OK, text jest None -> detekcja pominięta."""
    change_event = deepcopy(BASE_CHANGE_EVENT)
    m2_response = mock_http_response(200, {"text": None, "metadata": MOCK_METADATA_DICT})
    with patch('app.main.httpx.AsyncClient') as MockClient:
        mock_client_instance = AsyncMock(); mock_client_instance.post = AsyncMock(return_value=m2_response)
        MockClient.return_value.__aenter__.return_value = mock_client_instance
        await process_document_pipeline(change_event, mock_repo, TEST_CONVERSION_URL, TEST_DETECTION_URL)

    mock_repo.download_gridfs_file.assert_awaited_once()
    mock_client_instance.post.assert_awaited_once()
    assert mock_repo.update.await_count == 2
    update1_payload: DocumentUpdate = mock_repo.update.await_args_list[0].args[1]
    assert update1_payload.conversion_status == ConversionStatus.STATUS_COMPLETED
    assert getattr(update1_payload, 'normalized_text', '__SENTINEL__') is None
    assert update1_payload.metadata is not None
    update2_payload: DocumentUpdate = mock_repo.update.await_args_list[1].args[1]
    assert update2_payload.analysis_result.status == AnalysisStatus.SKIPPED
    assert "No text from conversion" in update2_payload.analysis_result.error

async def test_pipeline_m4_http_error(mock_repo: AsyncMock, mock_http_response: MagicMock):
    change_event = deepcopy(BASE_CHANGE_EVENT)
    m2_response = mock_http_response(200, {"text": NORMALIZED_TEXT_CONTENT, "metadata": MOCK_METADATA_DICT}, request_url=TEST_CONVERSION_URL)
    m4_response = mock_http_response(status_code=400, text_data="Bad Request", request_url=TEST_DETECTION_URL)
    with patch('app.main.httpx.AsyncClient') as MockClient:
        mock_client_instance = AsyncMock(); mock_client_instance.post = AsyncMock(side_effect=[m2_response, m4_response])
        MockClient.return_value.__aenter__.return_value = mock_client_instance
        await process_document_pipeline(change_event, mock_repo, TEST_CONVERSION_URL, TEST_DETECTION_URL)

    mock_repo.download_gridfs_file.assert_awaited_once()
    assert mock_client_instance.post.await_count == 2
    m4_response.raise_for_status.assert_called_once()
    assert mock_repo.update.await_count == 2
    update1_payload: DocumentUpdate = mock_repo.update.await_args_list[0].args[1]
    assert update1_payload.conversion_status == ConversionStatus.STATUS_COMPLETED
    update2_payload: DocumentUpdate = mock_repo.update.await_args_list[1].args[1]
    assert update2_payload.analysis_result.status == AnalysisStatus.FAILED
    assert "Error from Detection(M4) (400)" in update2_payload.analysis_result.error
    assert "Bad Request" in update2_payload.analysis_result.error

async def test_pipeline_m4_bad_json_response(mock_repo: AsyncMock, mock_http_response: MagicMock):
    change_event = deepcopy(BASE_CHANGE_EVENT)
    m2_response = mock_http_response(200, {"text": NORMALIZED_TEXT_CONTENT, "metadata": MOCK_METADATA_DICT})
    m4_response = mock_http_response(200, {"results": "not a list"}) # Zły format
    with patch('app.main.httpx.AsyncClient') as MockClient:
        mock_client_instance = AsyncMock(); mock_client_instance.post = AsyncMock(side_effect=[m2_response, m4_response])
        MockClient.return_value.__aenter__.return_value = mock_client_instance
        await process_document_pipeline(change_event, mock_repo, TEST_CONVERSION_URL, TEST_DETECTION_URL)

    assert mock_repo.update.await_count == 2
    update2_payload: DocumentUpdate = mock_repo.update.await_args_list[1].args[1]
    assert "Invalid response structure" in update2_payload.analysis_result.error
    assert "expected a list" in update2_payload.analysis_result.error


async def test_pipeline_gridfs_download_fails(mock_repo: AsyncMock, mock_http_response: MagicMock):
    change_event = deepcopy(BASE_CHANGE_EVENT)
    mock_repo.download_gridfs_file.side_effect = FileNotFoundInGridFSException("Test GridFS error")
    with patch('app.main.httpx.AsyncClient') as MockClient:
        mock_client_instance = AsyncMock(); MockClient.return_value.__aenter__.return_value = mock_client_instance
        await process_document_pipeline(change_event, mock_repo, TEST_CONVERSION_URL, TEST_DETECTION_URL)

    mock_repo.download_gridfs_file.assert_awaited_once()
    mock_client_instance.post.assert_not_awaited()
    mock_repo.update.assert_awaited_once()
    update_payload: DocumentUpdate = mock_repo.update.await_args_list[0].args[1]
    assert update_payload.conversion_status == ConversionStatus.STATUS_FAILED
    assert "GridFS Error: Test GridFS error" in update_payload.conversion_error

async def test_pipeline_missing_detection_url(mock_repo: AsyncMock, mock_http_response: MagicMock):
    change_event = deepcopy(BASE_CHANGE_EVENT)
    m2_response = mock_http_response(200, {"text": NORMALIZED_TEXT_CONTENT, "metadata": MOCK_METADATA_DICT})
    with patch('app.main.httpx.AsyncClient') as MockClient:
        mock_client_instance = AsyncMock(); mock_client_instance.post = AsyncMock(return_value=m2_response)
        MockClient.return_value.__aenter__.return_value = mock_client_instance
        await process_document_pipeline(change_event, mock_repo, TEST_CONVERSION_URL, None)

    mock_repo.download_gridfs_file.assert_awaited_once()
    mock_client_instance.post.assert_awaited_once_with(TEST_CONVERSION_URL, files=ANY)
    mock_repo.update.assert_awaited_once()
    update1_payload: DocumentUpdate = mock_repo.update.await_args_list[0].args[1]
    assert update1_payload.conversion_status == ConversionStatus.STATUS_COMPLETED
    assert update1_payload.analysis_result is None