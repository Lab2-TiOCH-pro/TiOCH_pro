# Moduł 3: Zarządzanie Danymi

## Technologie

*   **Język:** Python 3.13.2
*   **Framework API:** FastAPI
*   **Baza Danych:** MongoDB (z wykorzystaniem Motor - asynchronicznego sterownika)
*   **Przechowywanie Plików:** MongoDB GridFS
*   **Walidacja Danych:** Pydantic
*   **Konteneryzacja:** Docker

## API Endpoints

Wszystkie endpointy są dostępne pod prefiksem `/api`.

# Instrukcja Uruchomienia Projektu w Dokerze

### Instrukcje
1. Przejdź do folderu projektu:
   ```bash
   cd ścieżka/do/projektu
   ```

2. Uruchom projekt:
   ```bash
   docker-compose up --build    # lub "docker-compose up --build -d" dla działania w tle
   # Jeśli poniższa komenda nie działa (błąd zasad wykonywania), wykonaj:
   # Set-ExecutionPolicy Unrestricted -Scope Process
   ```

3. Sprawdź API:
   - http://127.0.0.1:8000/docs
   - http://127.0.0.1:8000/redoc

4. Zatrzymaj:
   ```bash
   docker-compose down          # lub "docker-compose down -v" aby usunąć dane MongoDB

   # Jeśli użyto Set-ExecutionPolicy wcześniej, przywróć domyślne ustawienia:
   # Set-ExecutionPolicy Restricted -Scope Process
   ```