# 🧠 TiOCH Text Extractor API

A **FastAPI-powered** backend service for extracting clean, readable text from various file formats or from public web pages.

---

## 🚀 Features

* 📄 Extracts text from PDF, DOCX, XLSX, CSV, HTML, TXT, JSON, and XML
* 🌐 Extracts readable text from websites via HTML parsing (in the same endpoint)
* 🛡️ Validates file size and type
* 🧼 Cleans and normalizes the output
* 📦 Supports MIME-type and extension checking
* 🧪 Well-structured and testable with `pytest`

---

## 📁 Supported File Types

| Extension | MIME Type                                                               |
| --------- | ----------------------------------------------------------------------- |
| `.docx`   | application/vnd.openxmlformats-officedocument.wordprocessingml.document |
| `.pdf`    | application/pdf                                                         |
| `.xlsx`   | application/vnd.openxmlformats-officedocument.spreadsheetml.sheet       |
| `.csv`    | text/csv                                                                |
| `.html`   | text/html                                                               |
| `.txt`    | text/plain                                                              |
| `.json`   | application/json                                                        |
| `.xml`    | application/xml                                                         |

> **Max upload file size**: `10 MB`

---

## 📂 Project Structure

```
TiOCH_pro/
│
├── app/
│   ├── main.py               # FastAPI app entry point
│   ├── routes.py             # API routes
│   ├── models.py             # Pydantic models
│   ├── config.py             # Config constants
│   └── utils.py              # Extraction logic and helpers
├── FileConversion/
│   └── converter.py          # FileConversion class
├── tests/
│   ├── test_file_upload.py         # File upload & website tests
│   └── test_file_conversion.py     # File parsing unit tests
```

---

## 🔌 API Usage

### `POST /file`

Uploads a document **or** a URL and extracts text from it.

#### 📄 Request

Use `multipart/form-data`:

**Example with `curl` (upload file):**

```bash
curl -X POST "http://localhost:8000/file" \
  -F "file=@path/to/your/file.pdf"
```

**Example with `curl` (extract website):**

```bash
curl -X POST "http://localhost:8000/file" \
  -F "website_url=https://example.com"
```

#### ✅ Response

```json
{
  "text": "Extracted text content...",
  "metadata": {
    "filename": "example.pdf or https://example.com",
    "size": 1024
  }
}
```

#### ⚠️ Errors

* `400` – Invalid file type, URL, or unreachable site
* `413` – File exceeds 10MB
* `422` – Neither file nor website\_url provided

---

## 🧪 Running Tests

Install dev dependencies:

```bash
pip install -r requirements.txt
```

Then run all tests:

```bash
pytest tests/
```

---

## 🛠 Setup & Run

### 🔧 Install

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

### ▶️ Run the App

```bash
uvicorn app.main:app --reload
```

App will be available at:
[http://localhost:8000/docs](http://localhost:8000/docs) – FastAPI Swagger UI
