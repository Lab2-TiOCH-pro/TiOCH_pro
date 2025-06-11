import pytest

# Add project root to sys.path for imports
import sys
from pathlib import Path
project_root = Path(__file__).resolve().parent.parent.parent # Adjust based on test file location
sys.path.insert(0, str(project_root))

from app.regex_detector import RegexDetector

@pytest.fixture
def detector():
    return RegexDetector()

# Test cases for various regex patterns
@pytest.mark.parametrize("text, expected_type, expected_value, expected_label", [
    ("Mój PESEL to 12345678901", "ID", "12345678901", "PESEL"),
    ("NIP firmy: 123-456-78-90", "ID", "123-456-78-90", "NIP"),
    ("NIP firmy: 1234567890", "ID", "1234567890", "NIP"), # NIP without dashes
    ("REGON: 123456789", "ID", "123456789", "REGON"),
    ("REGON: 12345678901234", "ID", "12345678901234", "REGON"), # 14-digit REGON
    ("Paszport AB1234567", "ID", "AB1234567", "PASSPORT"),
    ("Data: 01/02/2023", "ID", "01/02/2023", "DATE"),
    ("Data: 01.02.2023", "ID", "01.02.2023", "DATE"),
    ("Data: 01-02-2023", "ID", "01-02-2023", "DATE"),
    ("Email: test@example.com", "kontakt", "test@example.com", "EMAIL"),
    ("Telefon: 123-456-789", "kontakt", "123-456-789", "PHONE"),
    ("Telefon: 123 456 789", "kontakt", "123 456 789", "PHONE"),
    ("Tel: +48 123456789", "kontakt", "+48 123456789", "PHONE"),
    ("Konto: PL12345678901234567890123456", "finansowe", "PL12345678901234567890123456", "ACCOUNT"),
    ("Karta: 1234-5678-9012-3456", "finansowe", "1234-5678-9012-3456", "CREDIT_CARD"),
    ("Kwota: 100.50 PLN", "finansowe", "100.50 PLN", "MONEY"),
    ("Kwota: 200 EUR", "finansowe", "200 EUR", "MONEY"),
    ("Ulica Kwiatowa 1A", "kontakt", "Ulica Kwiatowa 1A", "ADDRESS"),
    ("ul. Słoneczna 22/3", "kontakt", "ul. Słoneczna 22/3", "ADDRESS"),
    ("Mieszka na os. Bajkowym 5c", "kontakt", "os. Bajkowym 5c", "ADDRESS"),
    ("Adres to al. Niepodległości 100", "kontakt", "al. Niepodległości 100", "ADDRESS"),
])
def test_regex_patterns(detector, text, expected_type, expected_value, expected_label):
    results = detector.detect(text)
    assert len(results) >= 1, f"Expected at least one result for: {text}"
    # Check if the specific expected result is present
    found = False
    for r in results:
        if r["value"] == expected_value and r["type"] == expected_type and r["label"] == expected_label:
            found = True
            break
    assert found, f"Expected {{'type': '{expected_type}', 'value': '{expected_value}', 'label': '{expected_label}'}} not found in {results} for text: {text}"

# Test cases for keyword patterns
@pytest.mark.parametrize("text, expected_type, expected_value, expected_label", [
    ("Potrzebne zaświadczenie lekarskie.", "medyczne", "zaświadczenie lekarskie", "MEDICAL_CERT"),
    ("Składam wniosek o urlop dziekański.", "inne", "urlop dziekański", "DEAN_LEAVE"),
    ("Dotyczy sprawy dyscyplinarne.", "inne", "dyscyplinarne", "DISCIPLINARY"),
    ("Mój numer paszportu to XYZ.", "ID", "numer paszportu", "PASZPORT_CTX"),
    ("Wymagana jest data urodzenia.", "ID", "data urodzenia", "DATA_URODZENIA"),
    ("Załączam protokół egzaminacyjny.", "edukacyjne", "protokół egzaminacyjny", "EXAM_PROTOCOL"),
    ("Temat: praca dyplomowa", "edukacyjne", "praca dyplomowa", "THESIS"),
    ("Wystawiam faktura VAT.", "finansowe", "faktura", "FATURA"),
    ("Proszę o orzeczenie o niepełnosprawności.", "medyczne", "orzeczenie o niepełnosprawności", "MEDICAL_CERT"),
])
def test_keyword_patterns(detector, text, expected_type, expected_value, expected_label):
    results = detector.detect(text)
    assert len(results) >= 1, f"Expected at least one result for: {text}"
    found = False
    for r in results:
        # Keyword matching is case-insensitive in detection, original case is returned in value
        if r["value"].lower() == expected_value.lower() and r["type"] == expected_type and r["label"] == expected_label:
            found = True
            break
    assert found, f"Expected {{'type': '{expected_type}', 'value': '{expected_value}', 'label': '{expected_label}'}} not found in {results} for text: {text}"

def test_no_sensitive_data(detector):
    text = "This is a normal sentence without any sensitive information."
    results = detector.detect(text)
    assert results == []

def test_multiple_detections(detector):
    text = "PESEL: 12345678901, email: test@example.com. Załączam faktura."
    results = detector.detect(text)
    assert len(results) == 3
    
    expected_finds = [
        {"type": "ID", "value": "12345678901", "label": "PESEL"},
        {"type": "kontakt", "value": "test@example.com", "label": "EMAIL"},
        {"type": "finansowe", "value": "faktura", "label": "FATURA"}
    ]
    
    for expected in expected_finds:
        assert any(r["type"] == expected["type"] and r["value"] == expected["value"] and r["label"] == expected["label"] for r in results)

def test_deduplication_within_regex_detector(detector):
    # This text contains the same NIP twice, should be detected once by RegexDetector's internal deduplication
    text = "NIP: 111-222-33-44 oraz NIP: 111-222-33-44."
    results = detector.detect(text)
    assert len(results) == 1
    assert results[0]["type"] == "ID"
    assert results[0]["value"] == "111-222-33-44"
    assert results[0]["label"] == "NIP"

    # This text contains the same keyword twice
    text_kw = "To jest faktura i jeszcze jedna faktura."
    results_kw = detector.detect(text_kw)
    # Keyword detection loop might find multiple occurrences if not handled properly by deduplication
    # The current deduplication key (type, value, label) should handle this.
    assert len(results_kw) == 1 
    assert results_kw[0]["type"] == "finansowe"
    assert results_kw[0]["value"] == "faktura"
    assert results_kw[0]["label"] == "FATURA" 