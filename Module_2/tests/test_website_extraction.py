import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

# ------------------------
# Valid test (real site)
# ------------------------

def test_extract_text_from_valid_website():
    response = client.post(
        "/website",
        json={"website_url": "https://example.com"}
    )

    assert response.status_code == 200
    data = response.json()

    assert "text" in data
    assert "metadata" in data
    assert data["metadata"]["filename"] == "https://example.com"
    assert isinstance(data["metadata"]["size"], int)
    assert len(data["text"]) > 0


# ------------------------
# Invalid test (bad URL)
# ------------------------

def test_extract_text_from_invalid_website():
    response = client.post(
        "/website",
        json={"website_url": "http://invalid.url.1234"}
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
        "/website",
        json={"website_url": "w.prz.edu.pl"}  # missing http(s)://
    )

    assert response.status_code == 400 or response.status_code == 422
    # 400 if the server attempts to fetch, 422 if body validation fails
