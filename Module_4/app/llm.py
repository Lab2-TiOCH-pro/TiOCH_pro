import os
import logging
import time
from openai import OpenAI
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv, find_dotenv
import json
import re
import backoff  # Dodajemy bibliotekę backoff do obsługi retry

# Konfiguracja loggera
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables from .env file (located anywhere in the directory tree)
load_dotenv(find_dotenv())

class LLMDetector:
    """
    Class for detecting sensitive data using the o4-mini-2025-04-16 model.
    """
    
    def __init__(self):
        # Get API key from environment variables
        self.api_key = os.getenv("OPENAI_API_KEY")
        
        # Check if API key is available
        if not self.api_key:
            logger.warning("Ostrzeżenie: Brak klucza API OpenAI. Ustaw zmienną OPENAI_API_KEY w pliku .env")
            self.client = None
        else:
            # Initialize OpenAI client with increased timeout
            self.client = OpenAI(api_key=self.api_key, timeout=60.0)  # Zwiększony timeout do 60 sekund
        
        # Enhanced prompt template with emphasis on output format
        self.prompt_template = """
        Your task is to analyze the document content and identify all sensitive data according to GDPR guidelines. You must identify **each individual occurrence** of the following data categories. Don't skip any, even if they seem related or are close to each other. This list is exhaustive for this task:

        - PESEL number (11 digits). String of digits according to Polish format (e.g. „85010212345").
        - Email addresses. Pattern `local@domain` with allowed characters (`a-z`, `A-Z`, digits, dots, underscores, hyphens) in the local part and domain (e.g. `jan.kowalski@example.com`).
        - First and last names of individuals. Two-word strings (e.g. „Jan Kowalski").
        - Phone numbers (domestic and international). Can have the format `+48 123 456 789`, with a prefix `0` (e.g. `0123 456 789`) or a string of 9 digits (e.g. `123456789`). Keep all spaces, hyphens, or parentheses as they appear in the text.
        - Residential or correspondence addresses (street, building number, postal code, city). If you find e.g. „ul. Długa 12/3, 00-123 Warszawa" – keep the whole string as `"value"`, set `"type"` to `"location"`, and `"label"` to `"ADRES"`.
        - Credit or debit card numbers (16 digits, with or without hyphens). Often grouped in groups of four („1234-5678-9012-3456") or without spaces („1234567890123456").
        - Passport numbers (2 letters and 7 digits). String of letters and digits according to Polish format (e.g. „AB1234567").
        - ID card numbers (3 letters and 6 digits). String of letters and digits according to Polish format (e.g. „ABC123456").
        - Driver's license numbers (9 digits). String of letters and digits according to Polish format (e.g. „ABC123456").
        - NIP number (10 digits). String of digits according to Polish format (e.g. „1234563218").
        - REGON number (9 or 14 digits). String of digits according to Polish format (e.g. „1234563218").
        - Other personal data subject to protection 

        Return the result in JSON format as an array of objects, where each object contains:
        - `"type"` – general data category (use only: "ID", "contact", "location", "payment", "other").
        - `"value"` – exact value found in the text, **without any modifications or interpretations**.
        - `"label"` – name of the detected data type (use only: "PESEL", "EMAIL", "IMIE I NAZWISKO", "TELEFON", "ADRES", "KARTA", "PASZPORT", "NIP", "DOWOD_OSOBISTY", "DATA", "DATA URODZENIA", "REGON" or "INNE_DANE" for others).

        Analyze the text thoroughly andcarefully. If there is no sensitive data – return an empty array `[]`.

        IMPORTANT: Your response must be a valid JSON object with a key named "result" containing the array of detected items.

        Examples of correct output:
        {
          "result": [
            {
                "type": "ID",
                "value": "85010212345",
                "label": "PESEL"
            },
            {
                "type": "kontakt",
                "value": "jan.kowalski@example.com",
                "label": "EMAIL"
            },
            {
                "type": "lokalizacja",
                "value": "ul. Długa 12 m. 3, 01-234 Warszawa",
                "label": "ADRES"
            },
            {
                "type": "ID",
                "value": "Jan Kowalski",
                "label": "IMIE I NAZWISKO"
            },
            {
                "type": "ID",
                "value": "123 456 789",
                "label": "NIP"
            }
          ]
        }

        Now analyze the following text and generate the result:


        DOCUMENT TO ANALYZE:
        
        {text}
        """
        # Escape all braces to prevent misinterpretation by .format()
        escaped_template = self.prompt_template.replace("{", "{{").replace("}", "}}")
        # Unescape the actual {text} placeholder
        self.prompt_template = escaped_template.replace("{{text}}", "{text}")
    
    # Funkcja do obsługi retry z wykładniczym backoff
    @backoff.on_exception(
        backoff.expo,
        (Exception),
        max_tries=5,  # Maksymalna liczba prób
        max_time=120,  # Maksymalny czas w sekundach
        on_backoff=lambda details: logger.warning(
            f"Ponowna próba wywołania API OpenAI ({details['tries']}). Opóźnienie: {details['wait']:.1f}s"
        )
    )
    def _call_openai_api(self, prompt: str) -> Dict[str, Any]:
        """
        Wywołuje API OpenAI z mechanizmem retry.
        """
        if not self.client:
            raise ValueError("Brak klienta OpenAI")
        
        start_time = time.time()
        logger.info("Wywołanie API OpenAI...")
        
        response = self.client.chat.completions.create(
            model="o4-mini-2025-04-16",
            messages=[
                {"role": "system", "content": "Jesteś ekspertem ds. bezpieczeństwa danych i Twoim zadaniem jest wykrywanie danych wrażliwych w dokumentach tekstowych w języku polskim. Bądź dokładny i kompletny w swojej analizie. Zidentyfikuj wszystkie wystąpienia danych wrażliwych w formacie JSON, używając tylko predefiniowanych typów i etykiet."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"} 
        )
        
        duration = time.time() - start_time
        logger.info(f"Odpowiedź z API OpenAI otrzymana po {duration:.2f}s")
        
        return response
    
    def _parse_llm_response(self, raw_content: str) -> List[Dict[str, Any]]:
        """
        Parsuje odpowiedź z LLM i obsługuje różne formaty.
        """
        if not raw_content:
            logger.error("LLMDetector: Otrzymano pustą odpowiedź z modelu")
            return []
        
        try:
            # Próba parsowania jako JSON
            parsed_json = json.loads(raw_content)
            detected_items = []
            
            # Przypadek 1: Odpowiedź jest listą obiektów detekcji
            if isinstance(parsed_json, list):
                logger.info("LLMDetector: Odpowiedź jest listą obiektów detekcji")
                detected_items = parsed_json
            
            # Przypadek 2: Odpowiedź jest pojedynczym obiektem detekcji
            elif isinstance(parsed_json, dict) and all(key in parsed_json for key in ["type", "value", "label"]):
                logger.info("LLMDetector: Odpowiedź jest pojedynczym obiektem detekcji")
                detected_items = [parsed_json]
            
            # Przypadek 3: Odpowiedź jest obiektem zawierającym listę detekcji pod kluczem
            elif isinstance(parsed_json, dict):
                # Sprawdź znane klucze
                for key in ["result", "results", "detections", "items", "data"]:
                    if key in parsed_json and isinstance(parsed_json[key], list):
                        logger.info(f"LLMDetector: Znaleziono listę detekcji pod kluczem '{key}'")
                        detected_items = parsed_json[key]
                        break
                
                # Jeśli nie znaleziono pod znanymi kluczami, szukaj pierwszej listy
                if not detected_items:
                    for key, value in parsed_json.items():
                        if isinstance(value, list) and value and isinstance(value[0], dict):
                            logger.info(f"LLMDetector: Znaleziono listę detekcji pod kluczem '{key}'")
                            detected_items = value
                            break
            
            # Walidacja i filtrowanie wyników
            valid_items = []
            for item in detected_items:
                if isinstance(item, dict) and "value" in item and "type" in item and "label" in item:
                    valid_items.append({
                        "value": item["value"],
                        "type": item["type"],
                        "label": item["label"],
                        "source": "llm"
                    })
                else:
                    logger.warning(f"LLMDetector: Pominięto niekompletny element: {item}")
            
            if not valid_items and detected_items:
                logger.warning(f"LLMDetector: Znaleziono {len(detected_items)} elementów, ale żaden nie jest prawidłowy")
            
            return valid_items
            
        except json.JSONDecodeError as e:
            logger.error(f"LLMDetector: Błąd parsowania JSON: {e}")
            
            # Próba wydobycia JSON z tekstu za pomocą regex
            for pattern in [
                r'```json\s*(.*?)\s*```',  # JSON w bloku kodu markdown
                r'```\s*(.*?)\s*```',       # Dowolny blok kodu markdown
                r'\{.*"result"\s*:\s*\[.*\].*\}',  # Obiekt JSON z kluczem result
                r'\[\s*\{.*\}\s*\]'         # Lista obiektów JSON
            ]:
                match = re.search(pattern, raw_content, re.DOTALL)
                if match:
                    try:
                        json_text = match.group(1)
                        extracted_json = json.loads(json_text)
                        logger.info(f"LLMDetector: Udało się wydobyć JSON za pomocą regex")
                        
                        # Rekurencyjne wywołanie parsowania dla wydobytego JSON
                        return self._parse_llm_response(json_text)
                    except json.JSONDecodeError:
                        logger.warning(f"LLMDetector: Nie udało się sparsować wydobytego tekstu jako JSON")
            
            # Jeśli wszystkie próby zawiodły, zwróć pustą listę
            logger.error(f"LLMDetector: Nie udało się wydobyć prawidłowego JSON z odpowiedzi")
            return []
    
    def detect(self, text: str) -> List[Dict[str, Any]]:
        """
        Detects sensitive data in text using the language model.
        """
        if not self.client:
            logger.warning("LLMDetector: Brak klienta OpenAI. Detekcja LLM pominięta.")
            return []
        
        results: List[Dict[str, Any]] = []
        try:
            # Przygotowanie promptu
            prompt = self.prompt_template.format(text=text)
            
            # Wywołanie API z mechanizmem retry
            try:
                response = self._call_openai_api(prompt)
                raw_content = response.choices[0].message.content
            except Exception as e:
                logger.error(f"LLMDetector: Błąd podczas wywoływania API OpenAI: {str(e)}")
                return []
            
            # Parsowanie odpowiedzi
            results = self._parse_llm_response(raw_content)
            logger.info(f"LLMDetector: Znaleziono {len(results)} elementów danych wrażliwych")
            
        except Exception as e:
            logger.error(f"LLMDetector: KRYTYCZNY - Nieoczekiwany błąd podczas detekcji LLM: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            
        return results

