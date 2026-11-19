"""Agent node functions with the LLM, search and storage layers mocked."""
import json

from research import agents

SRC = [{"id": 1, "title": "Doc", "url": "docs/a.md#chunk0", "snippet": "s", "text": "body"}]
FINDINGS = {
    "findings": [{"sub_question": "q", "claim": "c", "source_ids": [1], "confidence": 0.9}],
    "themes": [], "contradictions": [], "gaps": [],
}
PLAN = {"sub_questions": ["q"], "scope": ""}


# ---------- coordinator_plan ----------

def test_coordinator_plan_uses_llm_output(monkeypatch):
    monkeypatch.setattr(
        agents, "chat_json",
        lambda s, u, **k: {"sub_questions": ["a", "b"], "scope": "narrow", "search_queries": ["q1"]},
    )
    out = agents.coordinator_plan({"query": "Main question"})
    assert out["plan"] == {"sub_questions": ["a", "b"], "scope": "narrow"}
    assert out["search_queries"] == ["q1"]
    assert out["sources"] == [] and out["analysis_iter"] == 0 and out["writer_iter"] == 0
    assert "planned 2 sub-questions" in out["log"][0]


def test_coordinator_plan_falls_back_on_bad_output(monkeypatch):
    for bad in ({}, ["not", "a", "dict"], {"sub_questions": ""}):
        monkeypatch.setattr(agents, "chat_json", lambda s, u, _b=bad, **k: _b)
        out = agents.coordinator_plan({"query": "Main question"})
        assert out["plan"]["sub_questions"] == ["Main question"]
        assert out["search_queries"] == ["Main question"]


# ---------- research_agent ----------

def test_research_agent_adds_and_dedups_sources(monkeypatch):
    results = [
        {"title": "A", "url": "docs/a.md#chunk0", "snippet": "s", "text": "full A"},
        {"title": "B", "url": "docs/b.md#chunk0", "snippet": "s", "text": "full B"},
    ]
    monkeypatch.setattr(agents, "search", lambda q, n: results)
    out = agents.research_agent({"search_queries": ["q1", "q2"], "sources": []})
    assert [s["id"] for s in out["sources"]] == [1, 2]  # second query found only duplicates
    assert out["sources"][0]["text"] == "full A"
    assert out["sources"][0]["query"] == "q1"
    assert out["search_queries"] == []
    assert "+2 sources (total 2)" in out["log"][0]


def test_research_agent_fetches_at_most_n_web_pages(monkeypatch):
    results = [{"title": f"W{i}", "url": f"https://x.test/{i}", "snippet": "s"} for i in range(3)]
    monkeypatch.setattr(agents, "search", lambda q, n: results)
    fetched = []
    monkeypatch.setattr(agents, "fetch_text", lambda url: fetched.append(url) or "page text")
    out = agents.research_agent({"search_queries": ["q"], "sources": []})
    assert len(fetched) == agents.FETCH_TOP_N
    assert [s["text"] for s in out["sources"]] == ["page text"] * agents.FETCH_TOP_N + [""]


def test_research_agent_keeps_existing_sources_and_continues_ids(monkeypatch):
    monkeypatch.setattr(
        agents, "search", lambda q, n: [{"title": "N", "url": "new", "snippet": "", "text": "t"}]
    )
    out = agents.research_agent({"search_queries": ["q"], "sources": list(SRC)})
    assert [s["id"] for s in out["sources"]] == [1, 2]


# ---------- abort_no_sources ----------

def test_abort_no_sources_local_mode(monkeypatch):
    saved = {}
    monkeypatch.setattr(agents, "save_run", lambda st, rep, status: saved.update(status=status) or "RUN")
    monkeypatch.setattr(agents, "SOURCE_MODE", "local")
    out = agents.abort_no_sources({"query": "q", "sources": []})
    assert saved["status"] == "no_sources"
    assert out["final_report"].startswith("# No sources retrieved")
    assert "docs" in out["final_report"]
    assert any("aborted: no sources" in line for line in out["log"])


def test_abort_no_sources_web_mode_hint(monkeypatch):
    monkeypatch.setattr(agents, "save_run", lambda *a: "RUN")
    monkeypatch.setattr(agents, "SOURCE_MODE", "web")
    out = agents.abort_no_sources({"query": "q", "sources": []})
    assert "internet" in out["final_report"]


# ---------- analyzer ----------

def _analyzer_state(**extra):
    return {"query": "q", "plan": PLAN, "sources": list(SRC), **extra}


def test_analyzer_success_first_try(monkeypatch):
    calls = []
    monkeypatch.setattr(agents, "chat_json", lambda s, u, **k: calls.append(1) or FINDINGS)
    out = agents.analyzer(_analyzer_state(analysis_iter=1))
    assert len(calls) == 1
    assert out["analysis_iter"] == 2
    assert len(out["findings"]["findings"]) == 1


def test_analyzer_retries_once_when_schema_is_wrong(monkeypatch):
    answers = [{"findings": ["bare string"]}, FINDINGS]
    prompts = []

    def fake(system, user, **k):
        prompts.append(system)
        return answers.pop(0)

    monkeypatch.setattr(agents, "chat_json", fake)
    out = agents.analyzer(_analyzer_state())
    assert len(prompts) == 2
    assert "IMPORTANT" in prompts[1]
    assert len(out["findings"]["findings"]) == 1


def test_analyzer_gives_up_after_two_bad_answers(monkeypatch):
    calls = []
    monkeypatch.setattr(agents, "chat_json", lambda s, u, **k: calls.append(1) or {"findings": []})
    out = agents.analyzer(_analyzer_state())
    assert len(calls) == 2
    assert out["findings"]["findings"] == []
    assert out["analysis_iter"] == 1


# ---------- critic_findings ----------

def _critic_state(findings=FINDINGS, **extra):
    return {"plan": PLAN, "sources": list(SRC), "findings": findings, "analysis_iter": 1, **extra}


def test_critic_findings_high_score_is_approved(monkeypatch):
    monkeypatch.setattr(
        agents, "chat_json", lambda s, u, **k: {"verdict": "revise", "score": 9, "issues": []}
    )
    out = agents.critic_findings(_critic_state())
    assert out["critique"]["verdict"] == "approve"
    assert "forced_caveats" not in out


def test_critic_findings_empty_findings_can_never_be_approved(monkeypatch):
    monkeypatch.setattr(
        agents, "chat_json", lambda s, u, **k: {"verdict": "approve", "score": 10, "issues": []}
    )
    out = agents.critic_findings(_critic_state(findings={"findings": []}))
    assert out["critique"]["verdict"] == "revise"
    assert any(i["severity"] == "high" for i in out["critique"]["issues"])


def test_critic_findings_re_search_sets_queries(monkeypatch):
    monkeypatch.setattr(
        agents, "chat_json",
        lambda s, u, **k: {"verdict": "re_search", "score": 3, "issues": [], "gap_queries": ["more", "data"]},
    )
    out = agents.critic_findings(_critic_state())
    assert out["search_queries"] == ["more", "data"]


def test_critic_findings_cap_forces_caveats(monkeypatch):
    monkeypatch.setattr(
        agents, "chat_json",
        lambda s, u, **k: {"verdict": "revise", "score": 4, "issues": [{"severity": "high", "description": "weak"}]},
    )
    out = agents.critic_findings(_critic_state(analysis_iter=agents.MAX_ANALYSIS_ITERS))
    assert out["forced_caveats"] == ["weak"]
    assert any("cap hit" in line for line in out["log"])


def test_critic_findings_survives_non_dict_llm_output(monkeypatch):
    monkeypatch.setattr(agents, "chat_json", lambda s, u, **k: ["garbage"])
    out = agents.critic_findings(_critic_state())
    assert out["critique"]["verdict"] == "revise"
    assert out["critique"]["score"] == 0.0


# ---------- writer ----------

def test_writer_without_findings_does_not_call_llm(monkeypatch):
    def boom(*a, **k):
        raise AssertionError("LLM must not be called")

    monkeypatch.setattr(agents, "chat", boom)
    out = agents.writer({"query": "q", "findings": {"findings": []}, "sources": []})
    assert "No findings" in out["draft"]
    assert out["writer_iter"] == 1


def test_writer_calls_llm_and_passes_feedback_on_revision(monkeypatch):
    seen = {}

    def fake_chat(system, user, **k):
        seen["payload"] = json.loads(user)
        return "## Executive Summary\n\nText [1]."

    monkeypatch.setattr(agents, "chat", fake_chat)
    state = {
        "query": "q", "findings": FINDINGS, "sources": list(SRC), "writer_iter": 1,
        "draft": "old draft", "draft_critique": {"issues": [{"severity": "high", "description": "fix"}]},
    }
    out = agents.writer(state)
    assert out["draft"].startswith("## Executive Summary")
    assert out["writer_iter"] == 2
    assert seen["payload"]["previous_draft"] == "old draft"
    assert seen["payload"]["critic_feedback"][0]["description"] == "fix"
    assert seen["payload"]["valid_source_ids"] == [1]


def test_writer_first_draft_has_no_feedback(monkeypatch):
    seen = {}
    monkeypatch.setattr(agents, "chat", lambda s, u, **k: seen.update(p=json.loads(u)) or "draft")
    agents.writer({"query": "q", "findings": FINDINGS, "sources": list(SRC)})
    assert seen["p"]["critic_feedback"] == []


# ---------- critic_draft ----------

def test_critic_draft_without_findings_skips_llm(monkeypatch):
    def boom(*a, **k):
        raise AssertionError("LLM must not be called")

    monkeypatch.setattr(agents, "chat_json", boom)
    out = agents.critic_draft({"findings": {"findings": []}, "draft": "x", "sources": [], "plan": PLAN})
    assert out["draft_critique"]["verdict"] == "revise"
    assert out["draft_critique"]["score"] == 0.0


def test_critic_draft_flags_fabricated_citations(monkeypatch):
    monkeypatch.setattr(
        agents, "chat_json", lambda s, u, **k: {"verdict": "approve", "score": 10, "issues": []}
    )
    state = {"findings": FINDINGS, "draft": "Claim [1] and [9].", "sources": list(SRC), "plan": PLAN}
    out = agents.critic_draft(state)
    assert out["draft_critique"]["verdict"] == "revise"
    assert "[9]" in out["draft_critique"]["issues"][0]["description"]


def test_critic_draft_approves_clean_draft(monkeypatch):
    monkeypatch.setattr(
        agents, "chat_json", lambda s, u, **k: {"verdict": "revise", "score": 9, "issues": []}
    )
    state = {"findings": FINDINGS, "draft": "Claim [1].", "sources": list(SRC), "plan": PLAN}
    assert agents.critic_draft(state)["draft_critique"]["verdict"] == "approve"


# ---------- coordinator_finalize ----------

def _final_state(draft, verdict="approve", caveats=None):
    return {
        "query": "My question",
        "draft": draft,
        "sources": [
            {"id": 1, "title": "Doc A", "url": "docs/a.md#chunk0"},
            {"id": 2, "title": "Doc B", "url": "docs/b.md#chunk0"},
        ],
        "draft_critique": {"verdict": verdict, "issues": [{"severity": "low", "description": "minor"}]},
        "forced_caveats": caveats or [],
    }


def test_finalize_builds_references_and_strips_fake_ids(monkeypatch):
    saved = {}
    monkeypatch.setattr(agents, "save_run", lambda st, rep, status: saved.update(status=status) or "RUN")
    out = agents.coordinator_finalize(_final_state("Claim [1], and [2, 7]."))
    report = out["final_report"]
    assert report.startswith("# My question")
    assert "[2, 7]" not in report and "[7]" not in report
    assert "[1] Doc A. docs/a.md#chunk0" in report
    assert "[2] Doc B. docs/b.md#chunk0" in report
    assert "Review Notes" not in report
    assert saved["status"] == "ok"


def test_finalize_adds_review_notes_when_not_clean(monkeypatch):
    saved = {}
    monkeypatch.setattr(agents, "save_run", lambda st, rep, status: saved.update(status=status) or "RUN")
    out = agents.coordinator_finalize(_final_state("Claim [1].", verdict="revise", caveats=["weak source"]))
    assert "## Review Notes" in out["final_report"]
    assert "- weak source" in out["final_report"]
    assert saved["status"] == "ok_with_caveats"
