import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import asyncio

# Adjust the import path according to your project structure
# This assumes your tests are in a 'tests' directory sibling to an 'app' directory
import sys
from pathlib import Path
# Add the project root to sys.path to allow importing 'app'
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from app.main import app, DetectionResult, TaskResponse
from app.celery_app import celery as celery_app_instance # Use the actual celery instance

client = TestClient(app)

@pytest.fixture
def mock_celery_task():
    mock_task = MagicMock()
    mock_task.id = "test_task_id"
    return mock_task

@pytest.fixture
def mock_async_result():
    mock_res = MagicMock()
    return mock_res

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

@patch("app.main.detect_task.delay")
def test_detect_endpoint(mock_delay, mock_celery_task):
    mock_delay.return_value = mock_celery_task
    test_text = "This is a test text with some data."
    response = client.post("/detect", json={"text": test_text})
    
    assert response.status_code == 200
    assert response.json() == {"task_id": "test_task_id"}
    mock_delay.assert_called_once_with(test_text)

@pytest.mark.asyncio
@patch("app.main.celery.AsyncResult")
async def test_get_task_result_pending(mock_async_result_constructor, mock_async_result):
    mock_async_result.state = "PENDING"
    mock_async_result_constructor.return_value = mock_async_result
    
    response = client.get("/tasks/some_task_id")
    
    assert response.status_code == 202
    assert response.json() == {"detail": {"status": "PENDING"}}
    mock_async_result_constructor.assert_called_once_with("some_task_id")

@pytest.mark.asyncio
@patch("app.main.celery.AsyncResult")
async def test_get_task_result_started(mock_async_result_constructor, mock_async_result):
    mock_async_result.state = "STARTED"
    mock_async_result_constructor.return_value = mock_async_result
    
    response = client.get("/tasks/some_task_id")
    
    assert response.status_code == 202
    assert response.json() == {"detail": {"status": "STARTED"}}

@pytest.mark.asyncio
@patch("app.main.celery.AsyncResult")
async def test_get_task_result_failure(mock_async_result_constructor, mock_async_result):
    mock_async_result.state = "FAILURE"
    mock_async_result.result = "Task failed due to an error"
    mock_async_result_constructor.return_value = mock_async_result
    
    response = client.get("/tasks/some_task_id")
    
    assert response.status_code == 500
    assert response.json() == {"detail": "Task failed due to an error"}

@pytest.mark.asyncio
@patch("app.main.celery.AsyncResult")
async def test_get_task_result_success(mock_async_result_constructor, mock_async_result):
    mock_async_result.state = "SUCCESS"
    mock_data = [{"type": "ID", "value": "12345", "label": "PESEL"}]
    mock_async_result.result = mock_data # Directly assign the list of dicts
    mock_async_result_constructor.return_value = mock_async_result
    
    response = client.get("/tasks/some_task_id")
    
    assert response.status_code == 200
    # FastAPI will automatically serialize Pydantic models or lists of them
    assert response.json() == mock_data

@pytest.mark.asyncio
@patch("app.main.detect_task.delay")
async def test_full_flow_successful_detection(mock_delay, mock_celery_task):
    # 1. Mock the detect_task.delay call
    mock_delay.return_value = mock_celery_task
    test_text = "My PESEL is 12345678901."
    
    # 2. Call /detect endpoint
    response_detect = client.post("/detect", json={"text": test_text})
    assert response_detect.status_code == 200
    task_id_response = TaskResponse(**response_detect.json())
    assert task_id_response.task_id == "test_task_id"
    
    # 3. Mock Celery's AsyncResult for the task status/result
    with patch("app.main.celery.AsyncResult") as mock_async_result_constructor:
        # First call: PENDING
        mock_pending_result = MagicMock()
        mock_pending_result.state = "PENDING"
        mock_pending_result.id = task_id_response.task_id
        
        # Second call: SUCCESS
        mock_success_result = MagicMock()
        mock_success_result.state = "SUCCESS"
        mock_success_result.id = task_id_response.task_id
        # This is what detect_task would return, which is a list of dicts
        mock_success_result.result = [{"type": "ID", "value": "12345678901", "label": "PESEL_DETECTED"}]

        # Configure the mock to return different results on subsequent calls
        mock_async_result_constructor.side_effect = [mock_pending_result, mock_success_result]

        # 4. Poll /tasks/{task_id} - expecting PENDING initially
        response_task_pending = client.get(f"/tasks/{task_id_response.task_id}")
        assert response_task_pending.status_code == 202
        assert response_task_pending.json()["detail"]["status"] == "PENDING"
        
        # 5. Poll /tasks/{task_id} again - expecting SUCCESS
        # Ensure enough time for a hypothetical task completion (not strictly needed with mocks)
        await asyncio.sleep(0.01) 
        response_task_success = client.get(f"/tasks/{task_id_response.task_id}")
        
        assert response_task_success.status_code == 200
        expected_results = [{"type": "ID", "value": "12345678901", "label": "PESEL_DETECTED"}]
        assert response_task_success.json() == expected_results

        # Verify AsyncResult was called correctly
        assert mock_async_result_constructor.call_count == 2
        mock_async_result_constructor.assert_any_call(task_id_response.task_id) 