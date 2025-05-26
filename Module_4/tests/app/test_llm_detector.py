import pytest
from unittest.mock import patch, MagicMock
import os
import json

# Add project root to sys.path for imports
import sys
from pathlib import Path
project_root = Path(__file__).resolve().parent.parent.parent # Adjust based on test file location
sys.path.insert(0, str(project_root))

from app.llm import LLMDetector

@pytest.fixture
def mock_openai_client():
    client = MagicMock()
    client.chat.completions.create = MagicMock()
    return client

# Test initialization with API key
@patch.dict(os.environ, {"OPENAI_API_KEY": "test_key"})
@patch("app.llm.OpenAI") # Patch where OpenAI is imported/used in llm.py
def test_llm_detector_init_with_api_key(MockOpenAI, mock_openai_client):
    MockOpenAI.return_value = mock_openai_client
    detector = LLMDetector()
    MockOpenAI.assert_called_once_with(api_key="test_key")
    assert detector.client == mock_openai_client
    assert detector.api_key == "test_key"

# Test initialization without API key
@patch.dict(os.environ, {}, clear=True) # Ensure OPENAI_API_KEY is not set
@patch("app.llm.OpenAI")
def test_llm_detector_init_without_api_key(MockOpenAI, capsys):
    # We don't expect OpenAI to be called if key is missing
    detector = LLMDetector()
    MockOpenAI.assert_not_called()
    assert detector.client is None
    assert detector.api_key is None
    captured = capsys.readouterr()
    assert "Ostrzeżenie: Brak klucza API OpenAI" in captured.out

# Test detect method when API key is missing
@patch.dict(os.environ, {}, clear=True)
def test_detect_no_api_key(capsys):
    detector = LLMDetector() # Will init with no API key
    results = detector.detect("some text")
    assert results == []
    captured = capsys.readouterr() # Capturing init warning and detect print
    assert "Brak klucza API OpenAI. Nie można wykonać detekcji za pomocą GPT." in captured.out

# Test successful detection and parsing
@patch.dict(os.environ, {"OPENAI_API_KEY": "test_key"})
@patch("app.llm.OpenAI")
def test_detect_success(MockOpenAI, mock_openai_client):
    MockOpenAI.return_value = mock_openai_client
    
    mock_response = MagicMock()
    mock_message = MagicMock()
    # Simulate the expected JSON string output from LLM
    expected_data = [{"type": "ID", "value": "123", "label": "Test Data"}]
    mock_message.content = json.dumps(expected_data) # LLM returns a JSON string
    mock_response.choices = [MagicMock(message=mock_message)]
    mock_openai_client.chat.completions.create.return_value = mock_response
    
    detector = LLMDetector()
    results = detector.detect("analyze this text")
    
    assert results == expected_data
    mock_openai_client.chat.completions.create.assert_called_once()
    args, kwargs = mock_openai_client.chat.completions.create.call_args
    assert kwargs["model"] == "gpt-4.1-mini-2025-04-14"
    assert "analyze this text" in kwargs["messages"][0]["content"]

# Test successful detection with markdown in response
@patch.dict(os.environ, {"OPENAI_API_KEY": "test_key"})
@patch("app.llm.OpenAI")
def test_detect_success_with_markdown(MockOpenAI, mock_openai_client):
    MockOpenAI.return_value = mock_openai_client
    mock_response = MagicMock()
    mock_message = MagicMock()
    expected_data = [{"type": "ID", "value": "456", "label": "Markdown Data"}]
    # Simulate LLM response wrapped in markdown code block
    mock_message.content = f"```json\n{json.dumps(expected_data)}\n```"
    mock_response.choices = [MagicMock(message=mock_message)]
    mock_openai_client.chat.completions.create.return_value = mock_response

    detector = LLMDetector()
    results = detector.detect("text for markdown response")
    assert results == expected_data

# Test detection with malformed JSON response from LLM
@patch.dict(os.environ, {"OPENAI_API_KEY": "test_key"})
@patch("app.llm.OpenAI")
def test_detect_malformed_json(MockOpenAI, mock_openai_client, capsys):
    MockOpenAI.return_value = mock_openai_client
    mock_response = MagicMock()
    mock_message = MagicMock()
    mock_message.content = 'This is not JSON, it is [{"type": ID, value: "789"}] an error.'
    mock_response.choices = [MagicMock(message=mock_message)]
    mock_openai_client.chat.completions.create.return_value = mock_response
    
    detector = LLMDetector()
    results = detector.detect("text for malformed json")
    
    assert results == []
    captured = capsys.readouterr()
    assert "Nie można przetworzyć odpowiedzi GPT:" in captured.out 

# Test detection when OpenAI API call fails
@patch.dict(os.environ, {"OPENAI_API_KEY": "test_key"})
@patch("app.llm.OpenAI")
def test_detect_api_call_failure(MockOpenAI, mock_openai_client, capsys):
    MockOpenAI.return_value = mock_openai_client
    mock_openai_client.chat.completions.create.side_effect = Exception("API Error")
    
    detector = LLMDetector()
    results = detector.detect("text for api failure")
    
    assert results == []
    captured = capsys.readouterr()
    assert "Wystąpił błąd podczas detekcji danych wrażliwych za pomocą GPT: API Error" in captured.out 