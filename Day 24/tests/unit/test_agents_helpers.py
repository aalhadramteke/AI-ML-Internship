import pytest

from research import agents


def test_cited_ids():
    assert agents._cited_ids("See [1] and [2, 3] but not [x] or [4a]") == {1, 2, 3}
    assert agents._cited_ids("no citations") == set()


@pytest.mark.parametrize(
    "value,expected",
    [(5, 5), ("7", 7), ("[3]", 3), ("#2", 2), (3.0, 3), (True, None), ("abc", None), (None, None)],
)
def test_as_int(value, expected):
    assert agents._as_int(value) == expected


@pytest.mark.parametrize(
    "value,expected",
    [(" a ", ["a"]), ("", []), (["a", " ", "b"], ["a", "b"]), (None, []), (5, [])],
)
def test_str_list(value, expected):
    assert agents._str_list(value) == expected


@pytest.mark.parametrize(
    "value,expected",
    [("7.5", 7.5), (15, 10.0), (-3, 0.0), ("x", 0.0), (None, 0.0)],
)
def test_score_is_clamped(value, expected):
    assert agents._score(value) == expected


def test_norm_verdict():
    allowed = {"approve", "revise"}
    assert agents._norm_verdict(" APPROVE ", allowed, "revise") == "approve"
    assert agents._norm_verdict("maybe", allowed, "revise") == "revise"
    assert agents._norm_verdict(None, allowed, "revise") == "revise"


def test_norm_issues():
    assert agents._norm_issues("problem") == [{"severity": "medium", "description": "problem"}]
    assert agents._norm_issues({"severity": "HIGH", "description": "d"}) == [
        {"severity": "high", "description": "d"}
    ]
    assert agents._norm_issues([{"severity": "weird", "description": "d"}, "", "x"]) == [
        {"severity": "medium", "description": "d"},
        {"severity": "medium", "description": "x"},
    ]
    assert agents._norm_issues(None) == []


def test_high_issues():
    c = {"issues": [{"severity": "high"}, {"severity": "low"}]}
    assert agents._high_issues(c) == [{"severity": "high"}]
    assert agents._high_issues({}) == []


def test_clean_findings_keeps_only_supported_claims():
    raw = {
        "findings": [
            {"claim": "c1", "sub_question": "q", "source_ids": [1, "2", 99], "confidence": 2},
            "a bare string",
            {"claim": "no ids", "source_ids": []},
            {"claim": "unknown id only", "source_ids": [99]},
            {"claim": "default confidence", "source_ids": 1},
        ],
        "themes": "one theme",
        "contradictions": [{"description": "d", "source_ids": [1, 99]}, "text only"],
        "gaps": ["g"],
    }
    out = agents._clean_findings(raw, {1, 2})
    assert [f["claim"] for f in out["findings"]] == ["c1", "default confidence"]
    assert out["findings"][0]["source_ids"] == [1, 2]
    assert out["findings"][0]["confidence"] == 1.0
    assert out["findings"][1]["confidence"] == 0.5
    assert out["themes"] == ["one theme"]
    assert out["contradictions"] == [
        {"description": "d", "source_ids": [1]},
        {"description": "text only", "source_ids": []},
    ]
    assert out["gaps"] == ["g"]


@pytest.mark.parametrize("raw", [None, "text", 42, {}, {"findings": "nope"}])
def test_clean_findings_handles_garbage(raw):
    out = agents._clean_findings(raw, {1})
    assert out["findings"] == []


def test_clean_findings_accepts_bare_list():
    out = agents._clean_findings([{"claim": "c", "source_ids": [1]}], {1})
    assert len(out["findings"]) == 1


def test_sources_for_prompt_truncates_and_limits(monkeypatch):
    monkeypatch.setattr(agents, "MAX_SOURCES_IN_PROMPT", 2)
    monkeypatch.setattr(agents, "SOURCE_CHARS_IN_PROMPT", 5)
    sources = [
        {"id": 1, "title": "a", "url": "u1", "text": "0123456789", "snippet": "s"},
        {"id": 2, "title": "b", "url": "u2", "text": "", "snippet": "snippet-text"},
        {"id": 3, "title": "c", "url": "u3", "text": "zzz"},
    ]
    out = agents._sources_for_prompt(sources)
    assert [s["id"] for s in out] == [1, 2]
    assert out[0]["content"] == "01234"
    assert out[1]["content"] == "snipp"  # falls back to snippet


def test_route_after_research():
    assert agents.route_after_research({"sources": [{"id": 1}]}) == "analyzer"
    assert agents.route_after_research({"sources": []}) == "no_sources"
    assert agents.route_after_research({}) == "no_sources"


def test_route_after_findings_critic():
    r = agents.route_after_findings_critic
    cap = agents.MAX_ANALYSIS_ITERS
    assert r({"critique": {"verdict": "approve"}, "analysis_iter": 1}) == "writer"
    assert r({"critique": {"verdict": "revise"}, "analysis_iter": cap}) == "writer"
    assert r({"critique": {"verdict": "re_search"}, "analysis_iter": 1, "search_queries": ["q"]}) == "research"
    assert r({"critique": {"verdict": "re_search"}, "analysis_iter": 1, "search_queries": []}) == "analyzer"
    assert r({"critique": {"verdict": "revise"}, "analysis_iter": 1}) == "analyzer"


def test_route_after_draft_critic():
    r = agents.route_after_draft_critic
    cap = agents.MAX_WRITER_ITERS
    assert r({"draft_critique": {"verdict": "approve"}, "writer_iter": 1}) == "finalize"
    assert r({"draft_critique": {"verdict": "revise"}, "writer_iter": cap}) == "finalize"
    assert r({"draft_critique": {"verdict": "revise"}, "writer_iter": 1}) == "writer"
