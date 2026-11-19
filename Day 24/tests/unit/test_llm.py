import json

import pytest

from research import llm


class FakeResponse:
    def __init__(self, data):
        self._data = data

    def raise_for_status(self):
        pass

    def json(self):
        return self._data


# ---------- _parse_json ----------

def test_parse_json_plain():
    assert llm._parse_json('{"a": 1}') == {"a": 1}


def test_parse_json_strips_markdown_fences():
    assert llm._parse_json('```json\n{"a": 1}\n```') == {"a": 1}


def test_parse_json_extracts_object_from_prose():
    assert llm._parse_json('Sure! Here it is: {"a": 2} hope it helps') == {"a": 2}


def test_parse_json_raises_when_no_json():
    with pytest.raises(json.JSONDecodeError):
        llm._parse_json("no json here")


# ---------- chat_json ----------

def test_chat_json_repairs_invalid_json_once(monkeypatch):
    answers = ["definitely not json", '{"fixed": true}']
    calls = []

    def fake_chat(system, user, max_tokens=4000, json_mode=False):
        calls.append(system)
        return answers.pop(0)

    monkeypatch.setattr(llm, "chat", fake_chat)
    assert llm.chat_json("sys", "user") == {"fixed": True}
    assert len(calls) == 2
    assert "Return ONLY valid JSON" in calls[0]
    assert calls[1].startswith("Fix this into valid JSON")


def test_chat_json_happy_path_single_call(monkeypatch):
    calls = []
    monkeypatch.setattr(llm, "chat", lambda *a, **k: calls.append(1) or '{"ok": 1}')
    assert llm.chat_json("s", "u") == {"ok": 1}
    assert len(calls) == 1


# ---------- chat dispatch ----------

def test_chat_unknown_backend_raises_clear_error(monkeypatch):
    monkeypatch.setattr(llm, "BACKEND", "nope")
    with pytest.raises(ValueError, match="Unknown RA_BACKEND"):
        llm.chat("s", "u")


def test_chat_dispatches_to_selected_backend(monkeypatch):
    seen = {}

    def fake_backend(system, user, max_tokens, json_mode):
        seen.update(system=system, user=user, max_tokens=max_tokens, json_mode=json_mode)
        return "answer"

    monkeypatch.setattr(llm, "BACKEND", "ollama")
    monkeypatch.setitem(llm._BACKENDS, "ollama", fake_backend)
    assert llm.chat("S", "U", max_tokens=10, json_mode=True) == "answer"
    assert seen == {"system": "S", "user": "U", "max_tokens": 10, "json_mode": True}


def test_chat_reraises_backend_errors(monkeypatch):
    def failing(*a):
        raise RuntimeError("backend down")

    monkeypatch.setattr(llm, "BACKEND", "ollama")
    monkeypatch.setitem(llm._BACKENDS, "ollama", failing)
    with pytest.raises(RuntimeError, match="backend down"):
        llm.chat("s", "u")


# ---------- HTTP backends ----------

def test_ollama_request_and_response(monkeypatch):
    captured = {}

    def fake_post(url, json=None, timeout=None):
        captured.update(url=url, payload=json, timeout=timeout)
        return FakeResponse({"message": {"content": "hi there"}})

    monkeypatch.setattr(llm.httpx, "post", fake_post)
    out = llm._ollama("sys", "usr", 123, json_mode=True)
    assert out == "hi there"
    assert captured["url"].endswith("/api/chat")
    p = captured["payload"]
    assert p["model"] == llm.OLLAMA_MODEL
    assert p["stream"] is False
    assert p["format"] == "json"
    assert p["options"]["num_predict"] == 123
    assert p["messages"][0] == {"role": "system", "content": "sys"}
    assert p["messages"][1] == {"role": "user", "content": "usr"}


def test_ollama_omits_json_format_by_default(monkeypatch):
    captured = {}
    monkeypatch.setattr(
        llm.httpx, "post",
        lambda url, json=None, timeout=None: captured.update(p=json) or FakeResponse({"message": {"content": "x"}}),
    )
    llm._ollama("s", "u", 10)
    assert "format" not in captured["p"]


def test_openai_compat_request_and_response(monkeypatch):
    captured = {}

    def fake_post(url, json=None, timeout=None):
        captured.update(url=url, payload=json)
        return FakeResponse({"choices": [{"message": {"content": "pong"}}]})

    monkeypatch.setattr(llm.httpx, "post", fake_post)
    assert llm._openai_compat("s", "u", 50) == "pong"
    assert captured["url"].endswith("/chat/completions")
    assert captured["payload"]["max_tokens"] == 50
