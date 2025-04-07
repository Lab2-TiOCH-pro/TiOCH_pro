# 🧠 TiOCH Text Extractor API

A FastAPI-powered backend service for extracting clean, readable text from various file formats including PDF, DOCX, XLSX, CSV, HTML, TXT, JSON, and XML.

---

## 🚀 Features

- 📄 Extracts text from multiple file types
- 🛡️ Validates file size and type
- 🧼 Cleans and normalizes the output
- 📦 Supports MIME-type and extension checking
- 🧪 Well-structured and testable with pytest

---

## 📁 Supported File Types

| Extension | MIME Type                                           |
|-----------|-----------------------------------------------------|
| `.docx`   | application/vnd.openxmlformats-officedocument.wordprocessingml.document |
| `.pdf`    | application/pdf                                     |
| `.xlsx`   | application/vnd.openxmlformats-officedocument.spreadsheetml.sheet |
| `.csv`    | text/csv                                            |
| `.html`   | text/html                                           |
| `.txt`    | text/plain                                          |
| `.json`   | application/json                                    |
| `.xml`    | application/xml                                     |

> Max upload file size: **10 MB**

---

## 📂 Project Structure

```
TiOCH_pro/
│
├── app/
│   ├── main.py           # FastAPI app entry point
│   ├── routes.py         # API routes
│   ├── models.py         # Pydantic models
│   ├── config.py         # Config constants (MIME types, size)
│   └── utils.py          # Validation helpers
│── FileConversion/
│   └── converter.py           # FileConversion class for text extraction
├── tests/
│   ├── test_file_upload.py         # Integration tests for /file endpoint
│   ├── test_website_extraction.py  # Integration tests for /website endpoint
│   └── test_file_conversion.py     # Unit tests for file content parsing
```

---

## 🔌 API Usage

### `POST /file`

Uploads a document and extracts plain text content from supported formats. Supports PDF, DOCX, XLSX, CSV, HTML, TXT, JSON, and XML. Max file size: 10MB.

#### Request

Send a `multipart/form-data` request:

**Example with `curl`:**
```bash
curl -X POST "http://localhost:8000/file" \
  -F "file=@path/to/your/file.pdf"
```

#### Response
```json
{
  "text": "Extracted text content...",
  "metadata": {
    "filename": "example.pdf",
    "size": 1024,
    "date": "2025-04-07T18:19:00"
  }
}
```

#### Errors

- `400 Bad Request` – File type not allowed
- `413 Payload Too Large` – File exceeds 10 MB

---

### `POST /website`

Fetches the contents of a public webpage and extracts clean text from its HTML using BeautifulSoup.

#### Request

Send a `application/json` body request:

**Example with `curl`:**
```bash
curl -X POST "http://localhost:8000/website" \
  -H "Content-Type: application/json" \
  -d '{"website_url": "https://example.com"}'
```

#### Response
```json
{
  "text": "Extracted text content...",
  "metadata": {
    "filename": "w.prz.edu.pl",
    "size": 1024,
    "date": "2025-04-07T18:19:00"
  }
}
```

#### Errors

- `400 Bad Request` – File type not allowed
- `422 Unprocessable Entity` –Validation error due to malformed request body.

---

## 🧪 Running Tests

Install test dependencies:
```bash
pip install -r requirements.txt
```

Then run tests:
```bash
pytest tests/
```

> Includes both unit and integration tests for all supported formats.

---

## 🛠 Setup & Run

### 🔧 Install

```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### ▶️ Run the App

```bash
uvicorn app.main:app --reload
```

App will be available at: [http://localhost:8000/docs](http://localhost:8000/docs)

---