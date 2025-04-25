# Moduł 3: Zarządzanie Danymi

## Technologie

*   **Język:** Python 3.13.2
*   **Framework API:** FastAPI
*   **Baza Danych:** MongoDB (z wykorzystaniem Motor - asynchronicznego sterownika)
*   **Przechowywanie Plików:** MongoDB GridFS
*   **Walidacja Danych:** Pydantic
*   **Konteneryzacja:** Docker

## Podstawowy Adres URL API

Wszystkie endpointy są dostępne pod prefiksem `/api`.

## Autentykacja

Obecna wersja API **nie wymaga** autentykacji.

## Główne Koncepcje

*   **`document_id`**: Unikalny identyfikator dokumentu w systemie, będący MongoDB ObjectId reprezentowanym jako string (np. `"605fe1a6e3b4f8a3c1e6a7b8"`).
*   **GridFS**: System plików MongoDB używany do przechowywania dużych danych binarnych (oryginalne pliki). W metadanych dokumentu przechowywane są referencje do plików w GridFS (np. `originalDocumentPath: "gridfs:605fe1a6e3b4f8a3c1e6a7c0"`).
<!-- *   **`conversionStatus`**: Status procesu konwersji dokumentu (zarządzany przez Moduł 2). Możliwe wartości: `"pending"`, `"in_progress"`, `"completed"`, `"failed"`, `"not_required"`.
*   **`analysisStatus`**: Status procesu analizy danych wrażliwych (zarządzany przez Moduł 4). Możliwe wartości: `"pending"`, `"in_progress"`, `"completed"`, `"failed"`, `"not_started"`, `"skipped"`. -->

## Modele Danych (Pydantic)

Główne modele używane w API:

*   **`DocumentInDB`**: Pełna reprezentacja dokumentu w bazie danych (używana w odpowiedziach GET).
*   **`DocumentList`**: Model odpowiedzi dla listowania dokumentów, zawiera paginację.
*   **`UploadResultItem`**: Reprezentuje wynik uploadu pojedynczego pliku w odpowiedzi `POST /documents`.
<!-- *   **`DocumentUpdate`**: Model używany w ciele żądania PATCH do aktualizacji dokumentu (np. przez Moduł 2 lub 4). -->
<!-- *   **`DocumentMetadata`**: Metadane ekstrahowane podczas konwersji. -->
<!-- *   **`AnalysisResult`**: Zawiera szczegóły wyniku analizy danych wrażliwych. -->

## Endpointy API

### 1. Upload Dokumentów

*   **`POST /api/documents`**
    *   **Opis:** Uploaduje jeden lub więcej plików dokumentów. Zapisuje pliki w GridFS i tworzy wpisy metadanych w MongoDB. [Modułu 1 (UI)]
    *   **Typ Zawartości Żądania:** `multipart/form-data`
    *   **Parametry (Form Data):**
        *   `files`: (wymagane) Lista jednego lub więcej plików (`List[UploadFile]`).
        *   `uploader_email`: (wymagane) Adres email osoby uploadującej (`string`, format `email`).
    *   **Odpowiedź Sukces (207 Multi-Status):** Zwraca listę statusów dla każdego z uploadowanych plików. Nawet jeśli niektóre pliki się nie powiodły, status odpowiedzi to 207.
        ```json
        [
          {
            "filename": "raport.docx",
            "documentId": "605fe1a6e3b4f8a3c1e6a7b8",
            "status": "uploaded",
            "error": null
          },
          {
            "filename": "pusty.txt",
            "documentId": null,
            "status": "failed",
            "error": "Uploaded file cannot be empty."
          },
          {
            "filename": "bez_nazwy",
            "documentId": null,
            "status": "failed",
            "error": "Missing filename."
          }
        ]
        ```
    *   **Odpowiedzi Błąd:**
        *   `400 Bad Request`: Jeśli nie przesłano żadnych plików.
        *   `422 Unprocessable Entity`: Jeśli email jest niepoprawny lub brakuje wymaganych pól formularza.
        *   `500 Internal Server Error`: Błąd bazy danych lub nieoczekiwany błąd serwera podczas przetwarzania pliku. Szczegóły błędu dla danego pliku znajdą się w polu `error` w odpowiedzi 207.

### 2. Listowanie Dokumentów

*   **`GET /api/documents`**
    *   **Opis:** Pobiera listę dokumentów z możliwością filtrowania i paginacji. [Moduł 1 (UI)]
    *   **Parametry (Query):**
        *   `page` (opcjonalne, domyślnie 1): Numer strony (`integer`, >= 1).
        *   `limit` (opcjonalne, domyślnie 20): Liczba dokumentów na stronie (`integer`, >= 1, <= 100).
        <!-- *   `conversion_status` (opcjonalne): Filtruj wg statusu konwersji (`string`, np. `"completed"`, `"pending"`). -->
        *   `original_format` (opcjonalne): Filtruj wg oryginalnego formatu pliku (`string`, np. `"pdf"`, `"docx"`).
        *   `date_from` (opcjonalne): Filtruj dokumenty od tej daty/czasu uploadu (ISO 8601 `string`, np. `"2023-10-27T10:00:00Z"`).
        *   `date_to` (opcjonalne): Filtruj dokumenty do tej daty/czasu uploadu (ISO 8601 `string`).
        *   `query` (opcjonalne): Tekst do wyszukania w oryginalnej nazwie pliku (`string`).
    *   **Odpowiedź Sukces (200 OK):** Obiekt `DocumentList`.
        ```json
        {
          "total": 150,
          "page": 1,
          "limit": 20,
          "documents": [
            {
              "_id": "605fe1a6e3b4f8a3c1e6a7b8",
              "originalFilename": "raport_roczny.pdf",
              "originalFormat": "pdf",
              "uploaderEmail": "user@example.com",
              "uploadTimestamp": "2023-10-27T12:34:56.789Z",
              "sizeBytes": 102456,
              "contentHash": "sha256:...",
              "originalDocumentPath": "gridfs:...",
            },
          ]
        }
        ```
        <!-- ```json
         {
          "total": 150,
          "page": 1,
          "limit": 20,
          "documents": [
            {
              "_id": "605fe1a6e3b4f8a3c1e6a7b8",
              "originalFilename": "raport_roczny.pdf",
              "originalFormat": "pdf",
              "uploaderEmail": "user@example.com",
              "uploadTimestamp": "2023-10-27T12:34:56.789Z",
              "sizeBytes": 102456,
              "contentHash": "sha256:...",
              "originalDocumentPath": "gridfs:...",
              "conversionStatus": "completed",
              "conversionTimestamp": "2023-10-27T12:35:10.123Z",
              "normalizedTextRef": "gridfs:...",
              "metadata": { "pageCount": 10, "author": "Jan Kowalski" },
              "analysisStatus": "completed",
              "analysisResult": {
                "status": "completed",
                 "timestamp": "2023-10-27T12:36:00.456Z",
                 "detectedItems": [{"type": "PESEL", "value": "..."}],
                 "analysisTime": 5.67
               }
            },
          ]
        }
        ``` -->
    *   **Odpowiedzi Błąd:**
        *   `422 Unprocessable Entity`: Niepoprawny typ parametru query (np. `page` jako tekst).
        *   `500 Internal Server Error`: Błąd bazy danych.

### 3. Pobieranie Pojedynczego Dokumentu

*   **`GET /api/documents/{document_id}`**
    *   **Opis:** Pobiera szczegóły dla jednego dokumentu o podanym ID.
    *   **Parametry (Path):**
        *   `document_id`: (wymagane) ID dokumentu (`string`, format ObjectId).
    *   **Odpowiedź Sukces (200 OK):** Obiekt `DocumentInDB`.
        ```json
        {
          "_id": "605fe1a6e3b4f8a3c1e6a7b8",
          "originalFilename": "raport_roczny.pdf",
          // ... reszta pól jak w przykładzie DocumentList
        }
        ```
    *   **Odpowiedzi Błąd:**
        *   `404 Not Found`: Dokument o podanym ID nie istnieje.
        *   `422 Unprocessable Entity`: Niepoprawny format `document_id`.
        *   `500 Internal Server Error`: Błąd bazy danych.

<!-- 
### 4. Aktualizacja Metadanych Dokumentu

*   **`PATCH /api/documents/{document_id}`**
    *   **Opis:** Aktualizuje metadane dokumentu. Dla Modułu 2 (Konwersja) do zapisania statusu konwersji, referencji do znormalizowanego tekstu i metadanych, oraz dla Modułu 4 (AI) do zapisania statusu i wyników analizy.
    *   **Uwaga:** Pole `normalizedText` w ciele żądania jest specjalne. Jeśli zostanie podane, jego zawartość (tekst) zostanie zapisana w GridFS, a w metadanych dokumentu (`normalizedTextRef`) zapisana zostanie tylko referencja do tego pliku.
    *   **Parametry (Path):**
        *   `document_id`: (wymagane) ID dokumentu do aktualizacji (`string`, format ObjectId).
    *   **Ciało Żądania (Request Body):** Obiekt `DocumentUpdate` (`application/json`). Należy podać tylko te pola, które mają zostać zaktualizowane.
        ```json
        // Przykład: Aktualizacja po udanej konwersji (przez Moduł 2)
        {
          "conversionStatus": "completed",
          "conversionTimestamp": "2023-10-27T13:00:00Z",
          "normalizedText": "To jest znormalizowany tekst dokumentu...", // Zapisze w GridFS
          "metadata": {
            "pageCount": 5,
            "author": "System Konwersji"
          },
          "processingTimeSeconds": 10.5
        }

        // Przykład: Aktualizacja po nieudanej konwersji (przez Moduł 2)
        {
          "conversionStatus": "failed",
          "conversionTimestamp": "2023-10-27T13:01:00Z",
          "conversionError": "Nie można otworzyć pliku: uszkodzony format."
        }

        // Przykład: Aktualizacja po udanej analizie (przez Moduł 4)
        {
          "analysisStatus": "completed",
          "analysisResult": {
            "status": "completed",
            "timestamp": "2023-10-27T13:05:00Z",
            "detectedItems": [
              {"type": "email", "location_start": 15, "location_end": 30, "value_snippet": "...@example.com"}
            ],
            "analysisTime": 8.2
          }
        }
        ```
    *   **Odpowiedź Sukces (200 OK):** Zaktualizowany obiekt `DocumentInDB`.
        ```json
        // Zaktualizowany obiekt DocumentInDB
        {
           "_id": "605fe1a6e3b4f8a3c1e6a7b8",
           // ... reszta pól, w tym zaktualizowane
           "conversionStatus": "completed",
           "normalizedTextRef": "gridfs:nowy_id_tekstu",
           // ...
        }
        ```
    *   **Odpowiedzi Błąd:**
        *   `404 Not Found`: Dokument o podanym ID nie istnieje.
        *   `400 Bad Request`: Niepoprawna wartość w ciele żądania (np. nieznany status).
        *   `422 Unprocessable Entity`: Niepoprawny format `document_id` lub błąd walidacji ciała żądania.
        *   `500 Internal Server Error`: Błąd bazy danych podczas zapisu do GridFS lub aktualizacji metadanych.
         -->

### 4. Usuwanie Dokumentu

*   **`DELETE /api/documents/{document_id}`**
    *   **Opis:** Usuwa dane dokumentu oraz powiązane pliki z GridFS.
    *   **Parametry (Path):**
        *   `document_id`: (wymagane) ID dokumentu do usunięcia (`string`, format ObjectId).
    *   **Odpowiedź Sukces (200 OK):**
        ```json
        {
          "message": "Document deleted.",
          "documentId": "605fe1a6e3b4f8a3c1e6a7b8",
          "success": true
        }
        ```
    *   **Odpowiedzi Błąd:**
        *   `404 Not Found`: Dokument o podanym ID nie istnieje.
        *   `422 Unprocessable Entity`: Niepoprawny format `document_id`.
        *   `500 Internal Server Error`: Błąd bazy danych podczas usuwania metadanych lub plików z GridFS.

<!--
 ### 5. Inicjacja Analizy Danych Wrażliwych

*   **`POST /api/documents/{document_id}/analysis`**
    *   **Opis:** Oznacza dokument jako gotowy do analizy przez Moduł 4 (AI). Zmienia `analysisStatus` na `"pending"`. **Nie wykonuje analizy!** Analiza jest zadaniem Modułu 4, który po jej wykonaniu powinien użyć endpointu `PATCH /api/documents/{document_id}` do zapisania wyników.
    *   **Warunki:** Dokument musi mieć status konwersji `"completed"` lub `"not_required"`. Analiza nie może być już w statusie `"in_progress"` lub `"completed"`.
    *   **Parametry (Path):**
        *   `document_id`: (wymagane) ID dokumentu do analizy (`string`, format ObjectId).
    *   **Ciało Żądania:** Brak.
    *   **Odpowiedź Sukces (200 OK):** Zaktualizowany obiekt `DocumentInDB` z `analysisStatus: "pending"`.
        ```json
        {
          "_id": "605fe1a6e3b4f8a3c1e6a7b8",
          // ... inne pola ...
          "analysisStatus": "pending",
          "analysisResult": {
             "status": "pending",
             "timestamp": "2023-10-27T14:00:00Z", // Czas inicjacji
             "detectedItems": [],
             "error": null,
             "analysisTime": null
           }
          // ...
        }
        ```
    *   **Odpowiedzi Błąd:**
        *   `404 Not Found`: Dokument o podanym ID nie istnieje.
        *   `409 Conflict`: Nie można zainicjować analizy (np. zły status konwersji, analiza już trwa lub zakończona).
        *   `422 Unprocessable Entity`: Niepoprawny format `document_id`.
        *   `500 Internal Server Error`: Błąd bazy danych.
         -->

### 5. Pobieranie Oryginalnej Treści Dokumentu

*   **`GET /api/documents/{document_id}/content/original`**
    *   **Opis:** Pobiera oryginalną zawartość pliku dokumentu z GridFS. Dla Modułu 2 (Konwersja).
    *   **Parametry (Path):**
        *   `document_id`: (wymagane) ID dokumentu (`string`, format ObjectId).
    *   **Odpowiedź Sukces (200 OK):** Strumień binarny z zawartością pliku.
        *   **Nagłówki:**
            *   `Content-Type`: Typ MIME oryginalnego pliku (np. `application/pdf` lub `application/octet-stream`).
            *   `Content-Disposition`: `attachment; filename="oryginalna_nazwa_pliku.xxx"`
    *   **Odpowiedzi Błąd:**
        *   `404 Not Found`: Dokument lub odpowiadający mu plik w GridFS nie istnieje.
        *   `422 Unprocessable Entity`: Niepoprawny format `document_id`.
        *   `500 Internal Server Error`: Błąd podczas odczytu z GridFS.

<!-- ### 6. Pobieranie Znormalizowanego Tekstu Dokumentu

*   **`GET /api/documents/{document_id}/content/normalized`**
    *   **Opis:** Pobiera znormalizowaną treść tekstową dokumentu z GridFS (zapisaną tam przez Moduł 2 poprzez `PATCH /documents/{document_id}` z polem `normalizedText`). Przeznaczone dla Modułu 4 (AI).
    *   **Parametry (Path):**
        *   `document_id`: (wymagane) ID dokumentu (`string`, format ObjectId).
    *   **Odpowiedź Sukces (200 OK):** Strumień tekstowy (UTF-8).
        *   **Nagłówki:**
            *   `Content-Type`: `text/plain; charset=utf-8`
            *   `Content-Disposition`: `attachment; filename="normalized_{document_id}.txt"` (lub inna nazwa zapisana w metadanych GridFS)
    *   **Odpowiedzi Błąd:**
        *   `404 Not Found`: Dokument lub odpowiadający mu plik znormalizowanego tekstu w GridFS nie istnieje (np. konwersja się nie powiodła lub nie zakończyła).
        *   `422 Unprocessable Entity`: Niepoprawny format `document_id`.
        *   `500 Internal Server Error`: Błąd podczas odczytu z GridFS. -->

# Instrukcja Uruchomienia Projektu

### Instrukcje
1. Przejdź do folderu projektu:
   ```bash
   cd ścieżka/do/Module_3
   ```
2. Uruchom:
   ```bash
   python -m venv .venv
   .\.venv\Scripts\activate
   pip install -r requirements.txt
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