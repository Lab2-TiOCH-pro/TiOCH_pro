# 📄 Module 2 - File Conversion

A FastAPI-powered web service for converting various file types into raw plain text.  
Supports popular formats like `.pdf`, `.docx`, `.xlsx`, `.csv`, `.txt`, `.json`, `.xml`, and `.html`.

## 🚀 Features

- Upload a file and get back extracted raw text
- Supports multiple file types
- FastAPI + Pydantic for robust and typed API
- File validation (size, extension, MIME type)
- Structured JSON response with metadata

## 🧠 Supported File Types

| Extension | MIME Type                                      |
|-----------|------------------------------------------------|
| `.pdf`    | `application/pdf`                              |
| `.docx`   | `application/vnd.openxmlformats-officedocument.wordprocessingml.document` |
| `.xlsx`   | `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` |
| `.csv`    | `text/csv`                                     |
| `.txt`    | `text/plain`                                   |
| `.html`   | `text/html`                                    |
| `.json`   | `application/json`                             |
| `.xml`    | `application/xml`                              |

Max upload size: **10 MB**
