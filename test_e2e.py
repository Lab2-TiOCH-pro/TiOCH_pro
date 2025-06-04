import os
import sys
import requests
import json
import time
from pathlib import Path
import argparse

def run_test(pdf_path, module3_url, module4_url):
    # Sprawdź, czy plik istnieje
    if not os.path.exists(pdf_path):
        print(f"Błąd: Plik {pdf_path} nie istnieje.")
        return False

    print(f"Plik {pdf_path} znaleziony.")

    # 1. Wgraj plik do modułu 3
    print("Krok 1: Wgrywanie pliku do modułu 3...")

    try:
        with open(pdf_path, 'rb') as pdf_file:
            files = {'files': (os.path.basename(pdf_path), pdf_file)}
            data = {'uploader_email': 'test@example.com'}
            
            response = requests.post(f"{module3_url}/documents", files=files, data=data)
            
            if response.status_code != 207:  # Moduł 3 zwraca 207 Multi-Status
                print(f"Błąd podczas wgrywania pliku: {response.text}")
                return False
            
            upload_result = response.json()
            document_id = upload_result[0].get('documentId')
            
            if not document_id:
                print(f"Błąd: Nie otrzymano document_id. Odpowiedź: {upload_result}")
                return False
                
            print(f"Plik wgrany pomyślnie. Document ID: {document_id}")
    except Exception as e:
        print(f"Błąd podczas wgrywania pliku: {str(e)}")
        return False

    # 2. Poczekaj na konwersję przez moduł 2
    print("Krok 2: Oczekiwanie na konwersję pliku przez moduł 2...")

    max_retries = 10
    retry_interval = 3  # sekundy
    conversion_completed = False

    for i in range(max_retries):
        try:
            response = requests.get(f"{module3_url}/documents/{document_id}")
            
            if response.status_code != 200:
                print(f"Błąd podczas sprawdzania statusu dokumentu: {response.text}")
                time.sleep(retry_interval)
                continue
                
            document = response.json()
            conversion_status = document.get('conversionStatus')
            
            if conversion_status == 'completed':
                conversion_completed = True
                print("Konwersja zakończona pomyślnie.")
                break
            elif conversion_status == 'failed':
                print(f"Konwersja nie powiodła się. Szczegóły: {document.get('conversionError', 'Brak szczegółów')}")
                return False
            else:
                print(f"Status konwersji: {conversion_status}. Oczekiwanie...")
                time.sleep(retry_interval)
        except Exception as e:
            print(f"Błąd podczas sprawdzania statusu konwersji: {str(e)}")
            time.sleep(retry_interval)

    if not conversion_completed:
        print("Przekroczono maksymalną liczbę prób oczekiwania na konwersję.")
        return False

    # 3. Wywołaj endpoint /detect modułu 4 z document_id
    print("Krok 3: Wywołanie endpointu /detect modułu 4...")

    try:
        payload = {"document_id": document_id}
        response = requests.post(f"{module4_url}/detect", json=payload)
        
        if response.status_code != 200:
            print(f"Błąd podczas analizy dokumentu: {response.text}")
            return False
            
        analysis_results = response.json()
        print(f"Analiza zakończona pomyślnie. Wyniki: {json.dumps(analysis_results, indent=2)}")
    except Exception as e:
        print(f"Błąd podczas analizy dokumentu: {str(e)}")
        return False

    # 4. Sprawdź, czy wyniki zostały zapisane w bazie modułu 3
    print("Krok 4: Sprawdzanie, czy wyniki zostały zapisane w bazie modułu 3...")

    try:
        response = requests.get(f"{module3_url}/documents/{document_id}")
        
        if response.status_code != 200:
            print(f"Błąd podczas pobierania dokumentu: {response.text}")
            return False
            
        document = response.json()
        analysis_result = document.get('analysisResult', {})
        
        if not analysis_result:
            print("Błąd: Brak wyników analizy w dokumencie.")
            return False
            
        analysis_status = analysis_result.get('status')
        
        if analysis_status != 'completed':
            print(f"Błąd: Status analizy: {analysis_status}, oczekiwano: completed")
            return False
            
        detected_items = analysis_result.get('detectedItems', [])
        
        if not detected_items:
            print("Uwaga: Lista wykrytych elementów jest pusta.")
        else:
            print(f"Wykryte elementy: {json.dumps(detected_items, indent=2)}")
            
        # Sprawdź format wyników
        for item in detected_items:
            if not all(key in item for key in ['type', 'value', 'label']):
                print(f"Błąd: Nieprawidłowy format elementu: {item}")
                return False
        
        print("Test zakończony pomyślnie! Cały przepływ działa poprawnie.")
        return True
    except Exception as e:
        print(f"Błąd podczas sprawdzania wyników w bazie modułu 3: {str(e)}")
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Test przepływu danych między modułami 3 i 4')
    parser.add_argument('--pdf', type=str, default=r"C:\Users\mateu\Desktop\pliki\plik6.pdf", 
                        help='Ścieżka do pliku PDF do testowania')
    parser.add_argument('--module3', type=str, default="http://localhost:8002", 
                        help='Adres URL API modułu 3')
    parser.add_argument('--module4', type=str, default="http://localhost:8003", 
                        help='Adres URL API modułu 4')
    
    args = parser.parse_args()
    
    success = run_test(args.pdf, args.module3, args.module4)
    sys.exit(0 if success else 1)
