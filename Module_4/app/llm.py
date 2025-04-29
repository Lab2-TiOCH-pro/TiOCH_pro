import os
from openai import OpenAI
from typing import List, Dict, Any
from dotenv import load_dotenv, find_dotenv

# Załaduj zmienne środowiskowe z pliku .env (znajdującego się gdziekolwiek w drzewie)
load_dotenv(find_dotenv())

class LLMDetrcor:
    """
    Klasa do wykrywania danych wrażliwych za pomocą modelu GPT-4.1 mini.
    """
    
    def __init__(self):
        # Pobranie klucza API z zmiennych środowiskowych
        self.api_key = os.getenv("OPENAI_API_KEY")
        
        # Sprawdzenie, czy klucz API jest dostępny
        if not self.api_key:
            print("Ostrzeżenie: Brak klucza API OpenAI. Ustaw zmienną OPENAI_API_KEY w pliku .env")
            self.client = None
        else:
            # Inicjalizacja klienta OpenAI
            self.client = OpenAI(api_key=self.api_key)
        
        # Prompt dla modelu
        self.prompt_template = """
        Jesteś modelem językowym GPT‑4.1 mini wyspecjalizowanym w wykrywaniu i klasyfikowaniu danych wrażliwych w dokumentach tekstowych.

        Kategorie danych wrażliwych:
        1. Identyfikatory osobiste:  
            - PESEL (11 cyfr)  
            - NIP (10 cyfr, czasem z myślnikami)  
            - REGON (9 lub 14 cyfr)  
            - Numery paszportów/dowodów  
            - Daty urodzenia  
            - Imiona i nazwiska osób  
        2. Dane kontaktowe:  
            - Adresy zamieszkania  
            - Numery telefonów  
            - Adresy e‑mail  
        3. Dane finansowe:  
            - Numery kont bankowych  
            - Numery kart kredytowych  
            - Wynagrodzenia, stypendia  
            - Kwoty transakcji  
        4. Dane medyczne:  
            - Zaświadczenia lekarskie  
            - Orzeczenia o niepełnosprawności  
            - Inne informacje medyczne  
        5. Dane zawodowe/edukacyjne:  
            - Imiona i nazwiska osób  
            - Oceny i wyniki egzaminacyjne  
            - Recenzje prac, opinie  
            - Umowy o pracę i umowy cywilnoprawne  
            - Decyzje administracyjne (np. skreślenia, urlopy dziekańskie)  
        6. Inne wrażliwe:  
            - Sytuacja materialna/rodzinna  
            - Powody urlopów dziekańskich  
            - Opisy przewinień i dyscyplinarne  
        
        ZADANIE:
        - Przejrzyj tekst linia po linii i dla każdego wystąpienia danych z powyższych kategorii wygeneruj obiekt JSON z polami:
                • "type": jeden z ("ID","kontakt","finansowe","medyczne","edukacyjne","inne")  
                • "value": dokładna wykryta wartość  
                • "label": etykieta opisująca źródło lub kategorię wykrycia  

        – Zwróć wyłącznie jedną tablicę JSON zawierającą wszystkie obiekty, bez dodatkowych komentarzy ani opisu.

        Tekst do analizy:
        {text}
        """
    
    def detect(self, text: str) -> List[Dict[str, Any]]:
        """
        Wykrywa dane wrażliwe w tekście za pomocą modelu GPT-4.1 mini.
        
        Args:
            text: Tekst do analizy
            
        Returns:
            Lista znalezionych danych wrażliwych z informacją o typie, wartości i kontekście
        """
        # Jeśli brak klucza API, zwróć pustą listę
        if not self.api_key:
            print("Brak klucza API OpenAI. Nie można wykonać detekcji za pomocą GPT.")
            return []
        
        try:
            # Przygotowanie promptu
            prompt = self.prompt_template.format(text=text)
            
            # Wywołanie API
            response = self.client.chat.completions.create(
                model="gpt-4.1-mini-2025-04-14",
                messages=[
                    {"role": "user", "content": prompt} 
                ]
            )
        
            # Parsowanie odpowiedzi GPT i zwrócenie wyników
            content = response.choices[0].message.content
            # DEBUG: wypisz surową odpowiedź GPT, żeby zobaczyć, co zwraca
            print("DEBUG GPT raw content:", content)
            # Usuń zbędne białe znaki i markdownowe znaczniki
            raw = content.strip()
            if raw.startswith("```") and raw.endswith("```"):
                raw = raw.strip("`").strip()
            # Wyodrębnij samą tablicę lub obiekt JSON
            import re
            match = re.search(r"(\[.*\]|\{.*\})", raw, re.DOTALL)
            json_text = match.group(1) if match else raw
            try:
                import json
                return json.loads(json_text)
            except Exception as e:
                print(f"Nie można przetworzyć odpowiedzi GPT: {e}")
                return []
        except Exception as e:
            print(f"Wystąpił błąd podczas detekcji danych wrażliwych za pomocą GPT: {str(e)}")
            return []
