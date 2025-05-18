from typing import List, Dict, Any
from app.regex_detector import RegexDetector
from app.ner_detector import NERDetector
from app.llm import LLMDetector

class SensitiveDataDetector:
    """
    Wrapper scalający wyniki detekcji z RegexDetector, NERDetector i LLMDetector.
    """
    def __init__(self):
        self.regex = RegexDetector()
        self.ner   = NERDetector()
        self.llm   = LLMDetector()

    def detect(self, text: str) -> List[Dict[str, Any]]:
        # Zbierz wszystkie wyniki
        results: List[Dict[str, Any]] = []
        results.extend(self.regex.detect(text))
        results.extend(self.ner.detect(text))
        results.extend(self.llm.detect(text))
        # Sortuj według pozycji w tekście
        results = sorted(results, key=lambda x: x.get("start", 0))
        # Usuń duplikaty (span i value)
        unique: List[Dict[str, Any]] = []
        seen = set()
        for r in results:
            # Deduplicate across detectors based on value and type
            key = (r.get("value"), r.get("type"))
            if key not in seen:
                seen.add(key)
                unique.append(r)
        return unique 