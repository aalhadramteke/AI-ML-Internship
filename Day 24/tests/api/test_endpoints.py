import importlib
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(monkeypatch):
    """Create a FastAPI TestClient with predictable test environment settings."""
    monkeypatch.setenv("APP_ENV", "testing")
    monkeypatch.setenv("API_KEY", "test-api-key-1234567890")
    monkeypatch.setenv("DB_DELAY", "0.01")
    monkeypatch.setenv("EXTERNAL_DELAY", "0.01")
    monkeypatch.setenv("EMAIL_DELAY", "0.01")

    # Reload settings and main app so test env vars take effect
    settings_mod = importlib.import_module("app.settings")
    importlib.reload(settings_mod)
    main_mod = importlib.import_module("app.main")
    importlib.reload(main_mod)

    with TestClient(main_mod.app) as test_client:
        yield test_client


def test_health_endpoint(client):
    """GET /health returns 200 OK and status payload."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data.get("status") == "ok"


def test_request_id_header_present(client):
    """Middleware attaches X-Request-ID header to responses."""
    response = client.get("/health")
    assert "X-Request-ID" in response.headers


def test_v1_and_v2_report_endpoints(client):
    """Verify both v1 sync and v2 async report endpoints succeed."""
    r_v1 = client.get("/api/v1/report/1")
    assert r_v1.status_code == 200

    r_v2 = client.get("/api/v2/report/1")
    assert r_v2.status_code == 200


def test_research_requires_api_key(client):
    """POST /api/v2/research rejects missing or invalid X-API-Key with 401."""
    res_missing = client.post("/api/v2/research", json={"query": "What is FastAPI?"})
    assert res_missing.status_code == 401

    res_wrong = client.post(
        "/api/v2/research",
        headers={"X-API-Key": "wrong-key"},
        json={"query": "What is FastAPI?"},
    )
    assert res_wrong.status_code == 401


def test_research_validation_error(client):
    """POST /api/v2/research returns 422 on invalid/short query payload."""
    response = client.post(
        "/api/v2/research",
        headers={"X-API-Key": "test-api-key-1234567890"},
        json={"query": "hi"},  # Below minimum length (5-500 chars)
    )
    assert response.status_code == 422
