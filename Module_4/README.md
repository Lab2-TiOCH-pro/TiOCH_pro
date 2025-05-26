# Sensitive Data Detection Service (Module 4)

This module implements a REST API for detecting sensitive information in text. It combines three detection strategies:

1. **Regex Detector**: Precise patterns and keyword-based detection for IDs, contact info, financial data, and context keywords.
2. **NER Detector**: Named Entity Recognition using spaCy (Polish or multilingual model) to identify people, locations, dates, etc.
3. **LLM Detector**: GPT-powered classifier using OpenAI API to identify and classify sensitive data with confidence scores.

## Features

- FastAPI-based HTTP server with Swagger (OpenAPI) documentation.
- `/health` endpoint for simple status checks.
- `/detect` endpoint accepts JSON payload and returns detected items.
- Extensible design: easily add new detectors or customize existing ones.

## Requirements

- Python 3.11+
- `venv` or other virtual environment
- OpenAI API key (for LLM-based detection)

## Installation

```bash
# Clone repository and navigate to this module
cd Module_4

# Create virtual environment
python -m venv venv

# Activate venv (PowerShell)
. venv/Scripts/Activate.ps1
# or in cmd.exe:
# venv\Scripts\activate.bat

# Install dependencies
pip install -r requirements.txt
# If no requirements.txt, run:
# pip install fastapi uvicorn python-dotenv openai spacy

# Download spaCy Polish model
python -m spacy download pl_core_news_sm
```

## Configuration

Create a `.env` file at the root of this module:

```ini
OPENAI_API_KEY=sk-<YOUR_OPENAI_KEY>
```

## Running the Server

```bash
uvicorn app.main:app --reload --port 8000
```

The API will be available at `http://127.0.0.1:8000`.

## Endpoints

### GET /health

Health check endpoint. Returns:

```json
{ "status": "ok" }
```

### POST /detect

Detect sensitive data in provided text.

- **Request Body**:
  ```json
  { "text": "Your input text here" }
  ```

- **Response**: Array of detection objects:
  ```json
  [
    { "type": "ID", "value": "12345678901", "label": "PESEL" },
    { "type": "kontakt", "value": "email@example.com", "label": "EMAIL" }
  ]
  ```

## Testing

You can test the endpoints with PowerShell:

```powershell
# Health check
Invoke-RestMethod -Uri http://127.0.0.1:8000/health -Method GET

# Detect example
Invoke-RestMethod `
  -Uri http://127.0.0.1:8000/detect `
  -Method POST `
  -ContentType 'application/json' `
  -Body '{"text":"Jan Kowalski, PESEL 12345678901, email: jan@example.com"}'
```

Alternatively, use any HTTP client (curl, Postman, HTTPie).