"""Whole-graph tests. LLM, search and storage are mocked; needs `langgraph` installed."""
import pytest

pytest.importorskip("langgraph")

from research import agents  # noqa: E402
from research.graph import build_graph  # noqa: E402

FINDINGS = {
    "findings": [{"sub_question": "s1", "claim": "c", "source_ids": [1], "confidence": 0.9}],
    "themes": [], "contradictions": [], "gaps": [],
}


def _fake_chat_json(system, user, **kwargs):
    if system.startswith("You are the Coordinator"):
        return {"sub_questions": ["s1"], "scope": "x", "search_queries": ["q1"]}
    if system.startswith("You are the Analyzer"):
        return FINDINGS
    if system.startswith("You are the Critic. Evaluate"):
        return {"verdict": "approve", "score": 9, "issues": [], "gap_queries": []}
    if system.startswith("You are the Critic reviewing"):
        return {"verdict": "approve", "score": 9, "issues": []}
    raise AssertionError(f"unexpected prompt: {system[:40]}")


@pytest.fixture
def mocked(monkeypatch):
    calls = {"saved": [], "chat_json": 0}

    def counting_chat_json(system, user, **kwargs):
        calls["chat_json"] += 1
        return _fake_chat_json(system, user, **kwargs)

    monkeypatch.setattr(agents, "chat_json", counting_chat_json)
    monkeypatch.setattr(agents, "chat", lambda s, u, **k: "## Executive Summary\n\nRAG combines search and LLMs [1].")
    monkeypatch.setattr(agents, "save_run", lambda st, rep, status: calls["saved"].append(status) or "out/run")
    return calls


def test_graph_has_expected_nodes():
    nodes = set(build_graph().get_graph().nodes)
    expected = {
        "coordinator_plan", "research", "analyzer", "critic_findings",
        "writer", "critic_draft", "finalize", "abort_no_sources",
    }
    assert expected <= nodes


def test_full_pipeline_happy_path(monkeypatch, mocked):
    monkeypatch.setattr(
        agents, "search",
        lambda q, n: [{"title": "Doc", "url": "docs/a.md#chunk0", "snippet": "s", "text": "body"}],
    )
    result = build_graph().invoke({"query": "What is RAG?", "log": []}, {"recursion_limit": 40})
    report = result["final_report"]
    assert report.startswith("# What is RAG?")
    assert "[1] Doc. docs/a.md#chunk0" in report
    assert "Review Notes" not in report
    assert mocked["saved"] == ["ok"]
    assert any(line.startswith("[coordinator] planned") for line in result["log"])
    assert any(line.startswith("[writer]") for line in result["log"])


def test_pipeline_stops_when_no_sources(monkeypatch, mocked):
    monkeypatch.setattr(agents, "search", lambda q, n: [])
    result = build_graph().invoke({"query": "Unknown topic", "log": []}, {"recursion_limit": 40})
    assert result["final_report"].startswith("# No sources retrieved")
    assert mocked["saved"] == ["no_sources"]
    assert mocked["chat_json"] == 1  # only the Coordinator ran; the Analyzer/Critics never did
