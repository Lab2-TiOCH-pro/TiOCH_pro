import re
from typing import List, Dict, Any

class RegexDetector:
    """
    Klasa do wykrywania danych wrażliwych za pomocą wyrażeń regularnych i słów-kluczy.
    """
    def __init__(self):
        # Wzorce regex dla danych wrażliwych
        self.patterns = {
            "PESEL":      {"regex": re.compile(r"\b\d{11}\b"), "type": "ID"},
            "NIP":        {"regex": re.compile(r"\b\d{3}-?\d{3}-?\d{2}-?\d{2}\b"), "type": "ID"},
            "REGON":      {"regex": re.compile(r"\b\d{9}(?:\d{5})?\b"), "type": "ID"},
            "PASSPORT":   {"regex": re.compile(r"\b[A-Z]{2}\d{7}\b"), "type": "ID"},
            "DATE":       {"regex": re.compile(r"\b\d{2}[./-]\d{2}[./-]\d{4}\b"), "type": "ID"},
            "EMAIL":      {"regex": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"), "type": "kontakt"},
            "PHONE":      {"regex": re.compile(r"(\+?48\s?)?(?:\d{3}[-\s]?\d{3}[-\s]?\d{3})"), "type": "kontakt"},
            "ACCOUNT":    {"regex": re.compile(r"\b[A-Z]{2}\d{2}(?:\s?\d{4}){6}\b"), "type": "finansowe"},
            "CREDIT_CARD":{"regex": re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b"), "type": "finansowe"},
            "MONEY":      {"regex": re.compile(r"\b\d+[.,]?\d*\s?(?:PLN|EUR|USD|GBP)\b"), "type": "finansowe"},
            "ADDRESS":    {"regex": re.compile(r"\b(?:ulica|ul\.|al\.|aleja|osiedle|os\.|plac|pl\.)\s+[A-ZĄĆĘŁŃÓŚŹŻ][\wąćęłńóśźż]+\s+\d+[A-Za-z]?(?:/\d+)?", re.IGNORECASE), "type": "kontakt"},
        }
        # Słowa-klucze dla danych kontekstowych
        self.keyword_patterns = {
            "MEDICAL_CERT": {"keywords": ["zaświadczenie lekarskie", "orzeczenie o niepełnosprawności"], "type": "medyczne"},
            "DEAN_LEAVE":   {"keywords": ["urlop dziekański"], "type": "inne"},
            "DISCIPLINARY": {"keywords": ["dyscyplinarne", "przewinień"], "type": "inne"},
            "PASZPORT_CTX":   {"keywords": ["numer paszportu", "nr paszportu"], "type": "ID"},
            "VISA_CTX":       {"keywords": ["numer wizy", "nr wizy"], "type": "ID"},
            "DOC_POBYTU":     {"keywords": ["karta pobytu", "dokument pobytowy"], "type": "ID"},
            "DATA_URODZENIA": {"keywords": ["data urodzenia"], "type": "ID"},
            "EXAM_PROTOCOL":  {"keywords": ["protokoły egzaminacyjne", "protokół egzaminacyjny"], "type": "edukacyjne"},
            "THESIS":         {"keywords": ["praca dyplomowa"], "type": "edukacyjne"},
            "FATURA":         {"keywords": ["faktura"], "type": "finansowe"},
        }

    def detect(self, text: str) -> List[Dict[str, Any]]:
        """
        Wykrywa dane wrażliwe w tekście za pomocą regex i słów-kluczy.
        """
        results: List[Dict[str, Any]] = []
        # Detekcja przez regex
        for name, pat in self.patterns.items():
            for match in pat["regex"].finditer(text):
                results.append({
                    "type": pat["type"],
                    "value": match.group(),
                    "start": match.start(),
                    "end": match.end(),
                    "label": name
                })
        # Detekcja przez słowa-klucze (case-insensitive)
        lower_text = text.lower()
        for name, item in self.keyword_patterns.items():
            for kw in item["keywords"]:
                idx = 0
                while True:
                    idx = lower_text.find(kw, idx)
                    if idx == -1:
                        break
                    results.append({
                        "type": item["type"],
                        "value": text[idx:idx+len(kw)],
                        "start": idx,
                        "end": idx+len(kw),
                        "label": name
                    })
                    idx += len(kw)
        # Sortuj po pozycji i usuń duplikaty
        results = sorted(results, key=lambda x: x["start"])
        unique = []
        seen = set()
        for r in results:
            span = (r["start"], r["end"], r["value"])
            if span not in seen:
                seen.add(span)
                unique.append(r)
        return unique 