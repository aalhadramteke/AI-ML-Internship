import pytest

from research.service import run_research


class FakeApp:
    def __init__(self, updates):
        self.updates = updates
        self.calls = []

    def stream(self, state, config):
        self.calls.append((state, config))
        return iter(self.updates)


def _factory(updates):
    app = FakeApp(updates)
    return app, (lambda: app)


def test_run_research_collects_report_log_and_run_dir():
    app, factory = _factory(
        [
            {"coordinator_plan": {"log": ["[coordinator] planned 2 sub-questions"]}},
            {"finalize": {"final_report": "# Report", "log": ["[coordinator] saved run to output/run1"]}},
        ]
    )
    result = run_research("  What is RAG?  ", graph_factory=factory)
    assert result["query"] == "What is RAG?"
    assert result["status"] == "completed"
    assert result["report"] == "# Report"
    assert result["run_dir"] == "output/run1"
    assert len(result["log"]) == 2
    assert result["duration_s"] >= 0
    state, config = app.calls[0]
    assert state == {"query": "What is RAG?", "log": []}
    assert config == {"recursion_limit": 40}


def test_run_research_no_sources_status():
    _, factory = _factory(
        [
            {
                "abort_no_sources": {
                    "final_report": "# No sources retrieved",
                    "log": ["[coordinator] aborted: no sources retrieved", "[coordinator] saved run to out/x"],
                }
            }
        ]
    )
    result = run_research("question", graph_factory=factory)
    assert result["status"] == "no_sources"
    assert result["run_dir"] == "out/x"


def test_run_research_no_report_status():
    _, factory = _factory([{"coordinator_plan": {"log": ["[coordinator] planned 1 sub-questions"]}}])
    result = run_research("question", graph_factory=factory)
    assert result["status"] == "no_report"
    assert result["report"] == "No report produced."
    assert result["run_dir"] is None


@pytest.mark.parametrize("q", ["", "   ", None])
def test_run_research_rejects_empty_query(q):
    with pytest.raises(ValueError):
        run_research(q, graph_factory=lambda: None)


def test_run_research_propagates_pipeline_errors():
    class Broken:
        def stream(self, state, config):
            raise RuntimeError("llm exploded")

    with pytest.raises(RuntimeError, match="llm exploded"):
        run_research("question", graph_factory=lambda: Broken())
