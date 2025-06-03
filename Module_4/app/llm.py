import os
from openai import OpenAI
from typing import List, Dict, Any
from dotenv import load_dotenv, find_dotenv
import json
import re

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
            print("Ostrzeżenie: Brak klucza API OpenAI. Ustaw zmienną OPENAI_API_KEY w pliku .env")
            self.client = None
        else:
            # Initialize OpenAI client
            self.client = OpenAI(api_key=self.api_key)
        
        # Enhanced prompt template with emphasis on output format
        self.prompt_template = """
        Your task is to analyze the document content and identify all sensitive data according to GDPR guidelines. You must identify **each individual occurrence** of the following data categories. Don't skip any, even if they seem related or are close to each other. This list is exhaustive for this task:

        - PESEL number
        - Email addresses
        - First and last names of individuals
        - Phone numbers
        - Residential or correspondence addresses
        - Credit or debit card numbers
        - Passport numbers
        - NIP number
        - REGON number
        - Other personal data subject to protection (e.g. ID card number)

        Return the result in JSON format as an array of objects, where each object contains:
        - `"type"` – general data category (use only: "ID", "contact", "location", "payment", "other").
        - `"value"` – exact value found in the text, **without any modifications or interpretations**.
        - `"label"` – name of the detected data type (use only: "PESEL", "EMAIL", "IMIE I NAZWISKO", "TELEFON", "ADRES", "KARTA", "PASZPORT", "NIP", "DOWOD_OSOBISTY", "DATA", "DATA URODZENIA", "REGON" or "INNE_DANE" for others).

        Analyze the text carefully. If there is no sensitive data – return an empty array `[]`.

        Examples of correct output:
        [
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

        Now analyze the following text and generate the result:


        DOCUMENT TO ANALYZE:
        ---
        {text}
        """
        # Escape all braces to prevent misinterpretation by .format()
        escaped_template = self.prompt_template.replace("{", "{{").replace("}", "}}")
        # Unescape the actual {text} placeholder
        self.prompt_template = escaped_template.replace("{{text}}", "{text}")
    
    def detect(self, text: str) -> List[Dict[str, Any]]:
        """
        Detects sensitive data in text using the language model.
        """
        if not self.client:
            print("LLMDetector: No OpenAI client. LLM detection skipped.")
            return []
        
        results: List[Dict[str, Any]] = []
        try:
            prompt = self.prompt_template.format(text=text)
            
            # Wywołanie API
            response = self.client.chat.completions.create(
                model="o4-mini-2025-04-16",
                messages=[
                    {"role": "system", "content": "Jesteś ekspertem ds. bezpieczeństwa danych i Twoim zadaniem jest wykrywanie danych wrażliwych w dokumentach tekstowych w języku polskim. Bądź dokładny i kompletny w swojej analizie. Zidentyfikuj wszystkie wystąpienia danych wrażliwych w formacie JSON, używając tylko predefiniowanych typów i etykiet."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"} 
            )
        
            raw_content = response.choices[0].message.content
            
            if not raw_content:
                print("LLMDetector: Empty response received from model.")
                return []

            try:
                parsed_json = json.loads(raw_content)
                
                detected_items = [] 

                if isinstance(parsed_json, list):
                    detected_items = parsed_json
                elif isinstance(parsed_json, dict):
                    if all(key in parsed_json for key in ["type", "value", "label"]):
                        print("LLMDetector: JSON response is a single detection object. Wrapping in list.")
                        detected_items = [parsed_json]
                    else:
                        found_list = False
                        for key, value in parsed_json.items():
                            if isinstance(value, list):
                                detected_items = value
                                found_list = True
                                print(f"LLMDetector: Found detection list under key '{key}' in JSON response.")
                                break
                        if not found_list:
                            print(f"LLMDetector: JSON response  (dict) is not a single detection and does not contain a list under any key. Content: {raw_content[:500]}")
                else:
                    print(f"LLMDetector: JSON response is neither a list nor a dictionary. Content: {raw_content[:500]}")

                if not detected_items:
                    print("LLMDetector: No detection elements found after parsing JSON.")

                for item in detected_items:
                    if isinstance(item, dict) and "value" in item and "type" in item and "label" in item:
                        start_idx = item.get("start_index", -1)
                        end_idx = item.get("end_index", -1)
                        val = item["value"]

                        if not (isinstance(start_idx, int) and isinstance(end_idx, int) and 0 <= start_idx < end_idx <= len(text) and text[start_idx:end_idx] == val):
                            try:
                                found_pos = text.find(val)
                                if found_pos != -1:
                                    start_idx = found_pos
                                    end_idx = found_pos + len(val)
                                else: 
                                    start_idx = -1
                                    end_idx = -1
                            except: 
                                start_idx = -1
                                end_idx = -1
                        
                        results.append({
                            "value": val,
                            "type": item["type"],
                            "label": item["label"],
                            "start_index": start_idx,
                            "end_index": end_idx,
                            "source": "llm",
                            "description": item.get("description", f"Wykryte przez LLM ({item['label']})") 
                        })
                    else:
                        print(f"LLMDetector: Skipped incomplete element from LLM response: {item}")
            
            except json.JSONDecodeError as e:
                print(f"LLMDetector: JSON parsing error from LLM response: {e}. Raw response (fragment): {raw_content[:500]}")
                match = re.search(r"```json\s*(\[.*\])\s*```", raw_content, re.DOTALL)
                if not match:
                    match = re.search(r"(\[.*\])", raw_content, re.DOTALL) 

                if match:
                    json_text = match.group(1)
                    try:
                        detected_items_fallback = json.loads(json_text)
                        for item_fb in detected_items_fallback:
                            if isinstance(item_fb, dict) and "value" in item_fb and "type" in item_fb and "label" in item_fb:
                                start_idx_fb = item_fb.get("start_index", -1)
                                end_idx_fb = item_fb.get("end_index", -1)
                                val_fb = item_fb["value"]
                                if not (isinstance(start_idx_fb, int) and isinstance(end_idx_fb, int) and 0 <= start_idx_fb < end_idx_fb <= len(text) and text[start_idx_fb:end_idx_fb] == val_fb):
                                    try:
                                        found_pos_fb = text.find(val_fb)
                                        if found_pos_fb != -1:
                                            start_idx_fb = found_pos_fb
                                            end_idx_fb = found_pos_fb + len(val_fb)
                                        else:
                                            start_idx_fb = -1
                                            end_idx_fb = -1
                                    except:
                                        start_idx_fb = -1
                                        end_idx_fb = -1

                                results.append({
                                    "value": val_fb,
                                    "type": item_fb["type"],
                                    "label": item_fb["label"],
                                    "start_index": start_idx_fb,
                                    "end_index": end_idx_fb,
                                    "source": "llm",
                                    "description": item_fb.get("description", f"Wykryte przez LLM ({item_fb['label']})")
                                })
                            else:
                                print(f"LLMDetector: Skipped incomplete element (fallback) from LLM response: {item_fb}")
                        if results:
                             print("LLMDetector: Successfully parsed JSON from LLM response (fallback).")

                    except json.JSONDecodeError:
                        print(f"LLMDetector: Failed to parse extracted JSON array (fallback). Fragment: {json_text[:500]}")
                
        except Exception as e:
            print(f"LLMDetector: An error occurred during LLM detection: {str(e)}")
            import traceback
            traceback.print_exc()
            
        return results

