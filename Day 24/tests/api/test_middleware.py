import logging

from fastapi.testclient import TestClient

from app.main import create_app
from app.settings import settings


def test_headers_present_on_success(client):
    r = client.get("/health")
    assert len(r.headers["X-Request-ID"]) == 8
    assert float(r.headers["X-Process-Time-ms"]) >= 0


def test_headers_present_on_errors(client):
    for r in (client.get("/nope"), client.get("/api/v1/report/abc")):
        assert "X-Request-ID" in r.headers
        assert "X-Process-Time-ms" in r.headers


def test_request_ids_are_unique(client):
    ids = {client.get("/health").headers["X-Request-ID"] for _ in range(5)}
    assert len(ids) == 5


def test_requests_are_logged(client, caplog):
    with caplog.at_level(logging.INFO):
        client.get("/health")
    assert "GET /health" in caplog.text
    assert "status=200" in caplog.text


def test_cors_allows_configured_origin_only(monkeypatch):
    monkeypatch.setattr(settings, "allowed_origins", ["http://allowed.example"])
    c = TestClient(create_app())
    ok = c.get("/health", headers={"Origin": "http://allowed.example"})
    bad = c.get("/health", headers={"Origin": "http://evil.example"})
    assert ok.headers.get("access-control-allow-origin") == "http://allowed.example"
    assert "access-control-allow-origin" not in bad.headers
