import spacy
from typing import List, Dict, Any

class NERDetector:
    """
    Klasa do wykrywania danych wrażliwych za pomocą spaCy NER.
    """
    def __init__(self):
        # Attempt to load Polish model, download if missing, fallback to multilingual
        from spacy.cli import download
        models = ["pl_core_news_sm", "xx_ent_wiki_sm"]
        for model in models:
            try:
                self.nlp = spacy.load(model)
                break
            except OSError:
                download(model)
                self.nlp = spacy.load(model)
                break

    def detect(self, text: str) -> List[Dict[str, Any]]:
        """
        Wykrywa dane wrażliwe w tekście za pomocą NER spaCy.
        """
        results: List[Dict[str, Any]] = []
        doc = self.nlp(text)
        for ent in doc.ents:
            lab = ent.label_
            if lab in ("PER", "PERSON"):
                cat = "imie i nazwisko"
            elif lab in ("LOC", "GPE", "ADDRESS"):
                cat = "kontakt"
            elif lab in ("MONEY", "PERCENT", "QUANTITY"):
                cat = "finansowe"
            elif lab in ("DATE", "TIME"):
                cat = "ID"
            else:
                continue
            results.append({
                "type": cat,
                "value": ent.text,
                "start": ent.start_char,
                "end": ent.end_char,
                "label": lab
            })
        return results 