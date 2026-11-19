import httpx
import pytest

from app.routers import research as research_router
from app.settings import settings
from research import service

URL = "/api/v2/research"
BODY = {"query": "What is RAG?"}


def _result(**over):
    base = {
        "query": "What is RAG?",
        "status": "completed",
        "report": "# What is RAG?\n\nText [1].",
        "run_dir": "output/run1",
        "log": ["[coordinator] planned 2 sub-questions"],
        "duration_s": 1.5,
    }
    base.update(over)
    return base


@pytest.fixture
def fake_pipeline(monkeypatch):
    calls = []

    def fake(query):
        calls.append(query)
        return _result(query=query)

    monkeypatch.setattr(service, "run_research", fake)
    return calls


def test_research_success(client, fake_pipeline):
    r = client.post(URL, json=BODY)
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "completed"
    assert body["report"].startswith("# What is RAG?")
    assert body["run_dir"] == "output/run1"
    assert fake_pipeline == ["What is RAG?"]


def test_research_strips_query_whitespace(client, fake_pipeline):
    client.post(URL, json={"query": "   What is RAG?   "})
    assert fake_pipeline == ["What is RAG?"]


@pytest.mark.parametrize("payload", [{}, {"query": ""}, {"query": "    "}, {"query": "abc"}, {"query": "x" * 501}])
def test_research_validation_errors(client, fake_pipeline, payload):
    assert client.post(URL, json=payload).status_code == 422
    assert fake_pipeline == []


def test_research_is_open_when_no_api_key_configured(client, fake_pipeline):
    assert client.post(URL, json=BODY).status_code == 200


def test_research_requires_api_key_when_configured(client, fake_pipeline, monkeypatch):
    monkeypatch.setattr(settings, "api_key", "secret")
    assert client.post(URL, json=BODY).status_code == 401
    assert client.post(URL, json=BODY, headers={"X-API-Key": "wrong"}).status_code == 401
    assert client.post(URL, json=BODY, headers={"X-API-Key": "secret"}).status_code == 200
    assert len(fake_pipeline) == 1  # rejected requests never reached the pipeline


def test_research_returns_429_when_busy(client, fake_pipeline):
    research_router._active = settings.max_concurrent_research
    r = client.post(URL, json=BODY)
    assert r.status_code == 429
    assert r.headers["Retry-After"] == "30"
    assert fake_pipeline == []


def test_research_slot_is_released_after_success(client, fake_pipeline):
    client.post(URL, json=BODY)
    assert research_router._active == 0
    assert client.post(URL, json=BODY).status_code == 200


def test_research_llm_backend_down_returns_503(client, monkeypatch):
    def down(query):
        raise httpx.ConnectError("connection refused")

    monkeypatch.setattr(service, "run_research", down)
    r = client.post(URL, json=BODY)
    assert r.status_code == 503
    assert research_router._active == 0


def test_research_pipeline_error_returns_500_without_leaking_details(client, monkeypatch):
    def broken(query):
        raise RuntimeError("secret internal detail")

    monkeypatch.setattr(service, "run_research", broken)
    r = client.post(URL, json=BODY)
    assert r.status_code == 500
    assert "secret internal detail" not in r.text
    assert research_router._active == 0
