import pytest
import requests_mock
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


import requests_mock
from fastapi.testclient import TestClient
from app.main import app  # upewnij się, że ścieżka jest poprawna

client = TestClient(app)

# ------------------------
# Valid test (real site)
# ------------------------

def test_extract_text_from_valid_website():
    with requests_mock.Mocker() as m:
        html = "<html><body>Example Domain</body></html>"
        m.get("https://example.com", text=html)

        response = client.post(
            "/file",
            data={"website_url": "https://example.com"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "text" in data
        assert "metadata" in data
        assert data["metadata"]["filename"] == "https://example.com"
        assert isinstance(data["metadata"]["size"], int)
        assert "Example Domain" in data["text"]


# ------------------------
# Invalid test (bad URL)
# ------------------------

def test_extract_text_from_invalid_website():
    with requests_mock.Mocker() as m:
        m.get("http://invalid.url.1234", status_code=404)

        response = client.post(
            "/file",
            data={"website_url": "http://invalid.url.1234"}
        )

        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "Failed to fetch URL" in data["detail"]

# ------------------------
# Edge case: No protocol
# ------------------------

def test_extract_text_from_url_without_protocol():
    response = client.post(
        "/file",
        json={"website_url": "w.prz.edu.pl"}  # missing http(s)://
    )

    assert response.status_code == 400 or response.status_code == 422
    # 400 if the server attempts to fetch, 422 if body validation fails
