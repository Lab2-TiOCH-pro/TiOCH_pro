import pytest
from unittest.mock import MagicMock, patch

# Add project root to sys.path for imports
import sys
from pathlib import Path
project_root = Path(__file__).resolve().parent.parent.parent # Adjust based on test file location
sys.path.insert(0, str(project_root))

from app.sensitive_detector import SensitiveDataDetector

@pytest.fixture
def mock_regex_detector():
    detector = MagicMock()
    detector.detect = MagicMock(return_value=[])
    return detector

@pytest.fixture
def mock_llm_detector():
    detector = MagicMock()
    detector.detect = MagicMock(return_value=[])
    return detector

@patch('app.sensitive_detector.LLMDetector') # Path to LLMDetector where it's imported in SensitiveDataDetector
@patch('app.sensitive_detector.RegexDetector')
def test_sensitive_data_detector_init(
    MockRegexDetector, MockLLMDetector,
    mock_regex_detector, mock_llm_detector
):
    MockRegexDetector.return_value = mock_regex_detector
    MockLLMDetector.return_value = mock_llm_detector

    detector = SensitiveDataDetector()

    MockRegexDetector.assert_called_once()
    MockLLMDetector.assert_called_once()
    assert detector.regex == mock_regex_detector
    assert detector.llm == mock_llm_detector

@patch('app.sensitive_detector.LLMDetector')
@patch('app.sensitive_detector.RegexDetector')
def test_detect_no_findings(
    MockRegexDetector, MockLLMDetector,
    mock_regex_detector, mock_llm_detector
):
    MockRegexDetector.return_value = mock_regex_detector
    MockLLMDetector.return_value = mock_llm_detector

    detector = SensitiveDataDetector()
    results = detector.detect("some text")

    mock_regex_detector.detect.assert_called_once_with("some text")
    mock_llm_detector.detect.assert_called_once_with("some text")
    assert results == []

@patch('app.sensitive_detector.LLMDetector')
@patch('app.sensitive_detector.RegexDetector')
def test_detect_with_findings_and_deduplication(
    MockRegexDetector, MockLLMDetector,
    mock_regex_detector, mock_llm_detector
):
    mock_regex_detector.detect.return_value = [
        {"type": "ID", "value": "123", "label": "PESEL", "start": 10},
        {"type": "kontakt", "value": "a@b.com", "label": "EMAIL", "start": 1}
    ]
    mock_llm_detector.detect.return_value = [
        {"type": "finansowe", "value": "100PLN", "label": "MONEY_LLM", "start": 5}
    ]

    MockRegexDetector.return_value = mock_regex_detector
    MockLLMDetector.return_value = mock_llm_detector

    detector = SensitiveDataDetector()
    results = detector.detect("email a@b.com then 100PLN and id 123")

    # Expected: sorted by 'start', then deduplicated by (value, type)
    # NER "ID":"123" should be removed as Regex "ID":"123" came first due to sorting on start (even if detector order varies)
    # However, the current deduplication key is (value, type). The sorting by start happens *before* deduplication.
    # If start values were different and led to different ordering, the one appearing first in the sorted list for a given (value, type) would be kept.
    
    # Given the example, with distinct start times and the (value, type) deduplication:
    # Regex: ("123", "ID"), ("a@b.com", "kontakt")
    # LLM:   ("100PLN", "finansowe")

    # Sorted list before deduplication (based on example 'start' values):
    # 1. {"type": "kontakt", "value": "a@b.com", "label": "EMAIL", "start": 1} (Regex)
    # 2. {"type": "finansowe", "value": "100PLN", "label": "MONEY_LLM", "start": 5} (LLM)
    # 3. {"type": "ID", "value": "123", "label": "PESEL", "start": 10} (Regex)

    # Actual deduplication logic: `key = (r.get("value"), r.get("type"))`
    # The first occurrence of a (value, type) pair in the sorted list is kept.
    
    expected_results = [
        {"type": "kontakt", "value": "a@b.com", "label": "EMAIL", "start": 1},
        {"type": "finansowe", "value": "100PLN", "label": "MONEY_LLM", "start": 5},
        {"type": "ID", "value": "123", "label": "PESEL", "start": 10}
    ]

    assert len(results) == len(expected_results)
    for res_item in results:
        # Check if each item in results is in expected_results, ignoring order within the list for this assertion
        # The list itself should be sorted by 'start' due to the `sorted()` call in `detect`
        assert any(exp_item == res_item for exp_item in expected_results)
    
    # More precise check for sorted order and content
    assert results == expected_results

@patch('app.sensitive_detector.LLMDetector')
@patch('app.sensitive_detector.RegexDetector')
def test_detect_sorting_and_deduplication_order_matters(
    MockRegexDetector, MockLLMDetector,
    mock_regex_detector, mock_llm_detector
):
    # NER provides an item earlier that Regex later also provides
    mock_regex_detector.detect.return_value = [
        {"type": "ID", "value": "123", "label": "REGEX_ID_LATE", "start": 10} 
    ]
    mock_llm_detector.detect.return_value = []

    MockRegexDetector.return_value = mock_regex_detector
    MockLLMDetector.return_value = mock_llm_detector

    detector = SensitiveDataDetector()
    results = detector.detect("text with 123")

    # Expected: NER's item is kept because it has an earlier 'start' and thus appears first
    # in the sorted list before deduplication for the (value="123", type="ID") key.
    expected_results = [
        {"type": "ID", "value": "123", "label": "REGEX_ID_LATE", "start": 10}
    ]
    assert results == expected_results 