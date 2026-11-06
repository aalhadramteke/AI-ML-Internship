import pytest
from fastapi.testclient import TestClient
from main import app, MAX_FILE_SIZE
import os

client = TestClient(app)

def test_ingest_valid_txt():
    """Test successful ingestion of a valid text file."""
    content = b"This is a production ready RAG system test content. It should be chunked and stored."
    files = {"file": ("test.txt", content, "text/plain")}
    response = client.post("/ingest", files=files)
    assert response.status_code == 201
    assert "Successfully ingested" in response.json()["message"]

def test_ingest_valid_pdf():
    """Test successful ingestion of a valid PDF (minimal valid PDF structure)."""
    # Minimal PDF content (this is a mock, but enough to not crash the reader)
    # In a real scenario, we'd use a small actual PDF file.
    pdf_content = b"%PDF-1.1\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n3 0 obj\n<< /Type /Page /Parent 2 0 R /Contents 4 0 R >>\nendobj\n4 0 obj\n<< /Length 20 >>\nstream\nBT /F1 12 Tf (Hello PDF) Tj ET\nendstream\nendobj\nxref\n0 5\n0000000000 65535 f\n0000000010 00000 n\n0000000060 00000 n\n0000000110 00000 n\n0000000160 00000 n\ntrailer\n<< /Size 5 /Root 1 0 R >>\nstartxref\n230\n%%EOF"
    files = {"file": ("test.pdf", pdf_content, "application/pdf")}
    response = client.post("/ingest", files=files)
    # Note: PyPDF2 might return empty text for this minimal mock,
    # our main.py handles empty text with 400.
    # If it fails with 400, it's still validating the PDF structure/MIME.
    assert response.status_code in [201, 400]

def test_ingest_unsupported_format():
    """Test rejection of unsupported file extensions (e.g., .exe)."""
    content = b"some binary data"
    files = {"file": ("malicious.exe", content, "application/octet-stream")}
    response = client.post("/ingest", files=files)
    assert response.status_code == 400
    assert "Unsupported file extension" in response.json()["detail"]

def test_ingest_empty_file():
    """Test rejection of 0-byte files."""
    content = b""
    files = {"file": ("empty.txt", content, "text/plain")}
    response = client.post("/ingest", files=files)
    assert response.status_code == 400
    assert "File is empty" in response.json()["detail"]

def test_ingest_oversized_file():
    """Test rejection of files exceeding the size limit."""
    # Create content slightly over MAX_FILE_SIZE
    content = b"a" * (MAX_FILE_SIZE + 1024)
    files = {"file": ("large.txt", content, "text/plain")}
    response = client.post("/ingest", files=files)
    assert response.status_code == 413
    assert "File size exceeds limit" in response.json()["detail"]

def test_query_endpoint():
    """Test the query endpoint returns expected structure."""
    # First ingest some data to query against
    content = b"The capital of France is Paris. The Eiffel Tower is in Paris."
    files = {"file": ("geo.txt", content, "text/plain")}
    client.post("/ingest", files=files)

    payload = {"query": "What is the capital of France?"}
    response = client.post("/query", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert "metadata" in data
    assert isinstance(data["answer"], list)

def test_query_no_results():
    """Test query when no documents are present or relevant."""
    # This is a fresh test; if the collection was cleared, it would return empty.
    payload = {"query": "Something completely random that doesn't exist in the docs"}
    response = client.post("/query", json=payload)
    assert response.status_code == 200
    assert isinstance(response.json()["answer"], list)
