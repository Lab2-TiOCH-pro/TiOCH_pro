import pytest
from unittest.mock import patch, MagicMock

# Add project root to sys.path for imports
import sys
from pathlib import Path
project_root = Path(__file__).resolve().parent.parent.parent # Adjust based on test file location
sys.path.insert(0, str(project_root))

# Mock spacy before importing NERDetector
# This is a common pattern: mock the dependency before the module using it is imported.
mock_spacy = MagicMock()

# Mock spacy.cli.download
mock_spacy_cli_download = MagicMock()

# Mock spacy.load() to return a mock nlp object
mock_nlp_object = MagicMock()
mock_nlp_object.pipe_names = ["ner", "parser"] # Example pipe names
mock_nlp_object.disable_pipes = MagicMock()

# Define a mock Entity class that spaCy uses
class MockSpacyEntity:
    def __init__(self, text, label_):
        self.text = text
        self.label_ = label_

@patch.dict(sys.modules, {
    'spacy': mock_spacy,
    'spacy.cli': MagicMock(download=mock_spacy_cli_download)
})
@patch('app.ner_detector.spacy.load') # Patch spacy.load where it is used in ner_detector
def test_ner_detector_init_and_model_loading_success(mock_spacy_load_func):
    """Test successful initialization and model loading."""
    mock_spacy_load_func.return_value = mock_nlp_object
    
    from app.ner_detector import NERDetector # Import here after mocks are set up
    detector = NERDetector()
    
    mock_spacy_load_func.assert_called_once_with("pl_core_news_sm")
    mock_nlp_object.disable_pipes.assert_called_once_with("parser") # Assuming 'parser' is the other pipe
    assert detector.nlp == mock_nlp_object

@patch.dict(sys.modules, {
    'spacy': mock_spacy,
    'spacy.cli': MagicMock(download=mock_spacy_cli_download)
})
@patch('app.ner_detector.spacy.load')
def test_ner_detector_init_fallback_model(mock_spacy_load_func):
    """Test fallback to secondary model if primary fails."""
    # Reset the disable_pipes mock on the global mock_nlp_object before this test
    # to ensure it's only called once within this test's scope for the fallback model.
    mock_nlp_object.disable_pipes = MagicMock() # Re-assign a fresh mock

    # Simulate OSError for the first model (both attempts), then success for the second
    mock_spacy_load_func.side_effect = [
        OSError("Model pl_core_news_sm not found - first attempt"),
        OSError("Model pl_core_news_sm not found - second attempt after download"),
        mock_nlp_object  # This should be the result of loading "xx_ent_wiki_sm"
    ]
    
    from app.ner_detector import NERDetector
    detector = NERDetector()
    
    assert mock_spacy_load_func.call_count == 3
    mock_spacy_load_func.assert_any_call("pl_core_news_sm")
    mock_spacy_cli_download.assert_called_once_with("pl_core_news_sm") # Attempted download for first model
    mock_spacy_load_func.assert_any_call("xx_ent_wiki_sm")
    mock_nlp_object.disable_pipes.assert_called_once_with("parser")
    assert detector.nlp == mock_nlp_object


@patch.dict(sys.modules, {
    'spacy': mock_spacy,
    'spacy.cli': MagicMock(download=mock_spacy_cli_download)
})
@patch('app.ner_detector.spacy.load')
def test_ner_detect_entities(mock_spacy_load_func):
    """Test entity detection and mapping."""
    mock_doc = MagicMock()
    mock_doc.ents = [
        MockSpacyEntity("Jan Kowalski", "PER"),
        MockSpacyEntity("Warszawa", "LOC"),
        MockSpacyEntity("100 zł", "MONEY"),
        MockSpacyEntity("01-01-2023", "DATE"),
        MockSpacyEntity("Org Inc.", "ORG") # Should be ignored
    ]
    mock_nlp_object.return_value = mock_doc # nlp(text) returns this mock_doc
    mock_spacy_load_func.return_value = mock_nlp_object

    from app.ner_detector import NERDetector
    detector = NERDetector()
    detector.nlp = mock_nlp_object # Ensure the detector uses our fully mocked nlp

    results = detector.detect("Jan Kowalski mieszka w Warszawa i ma 100 zł od 01-01-2023 w Org Inc.")

    expected_results = [
        {"type": "imie i nazwisko", "value": "Jan Kowalski", "label": "PER"},
        {"type": "kontakt", "value": "Warszawa", "label": "LOC"},
        {"type": "finansowe", "value": "100 zł", "label": "MONEY"},
        {"type": "ID", "value": "01-01-2023", "label": "DATE"}
    ]
    assert results == expected_results

@patch.dict(sys.modules, {
    'spacy': mock_spacy,
    'spacy.cli': MagicMock(download=mock_spacy_cli_download)
})
@patch('app.ner_detector.spacy.load')
def test_ner_detect_no_entities(mock_spacy_load_func):
    mock_doc = MagicMock()
    mock_doc.ents = []
    mock_nlp_object.return_value = mock_doc
    mock_spacy_load_func.return_value = mock_nlp_object

    from app.ner_detector import NERDetector
    detector = NERDetector()
    detector.nlp = mock_nlp_object

    results = detector.detect("Zwykłe zdanie.")
    assert results == []

@patch.dict(sys.modules, {
    'spacy': mock_spacy,
    'spacy.cli': MagicMock(download=mock_spacy_cli_download)
})
@patch('app.ner_detector.spacy.load')
def test_ner_detect_spacy_error(mock_spacy_load_func, capsys):
    mock_nlp_object.side_effect = Exception("spaCy boom!") # nlp(text) will raise an error
    mock_spacy_load_func.return_value = mock_nlp_object

    from app.ner_detector import NERDetector
    detector = NERDetector()
    detector.nlp = mock_nlp_object # Ensure it uses the error-raising mock

    results = detector.detect("Test.")
    assert results == []
    captured = capsys.readouterr()
    assert "spaCy NER processing error: spaCy boom!" in captured.out 