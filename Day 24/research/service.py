"""Single entry point used by the API (and the CLI) to run the multi-agent pipeline."""
import logging
import re
import time
from typing import Callable, Optional

logger = logging.getLogger(__name__)

_RUN_DIR_RE = re.compile(r"saved run to (.+)$")


def run_research(query: str, graph_factory: Optional[Callable] = None) -> dict:
    """Run User -> Coordinator -> Research -> Analyzer -> Critic -> Writer -> Answer.

    Blocking (LLM calls can take minutes); the API calls it through a worker thread.
    `graph_factory` exists so tests can inject a fake graph without LangGraph/LLMs.
    """
    query = (query or "").strip()
    if not query:
        raise ValueError("query must not be empty")

    if graph_factory is None:
        from research.graph import build_graph  # lazy: keeps API start-up light

        graph_factory = build_graph

    start = time.perf_counter()
    logger.info("Research started: %r", query)
    app = graph_factory()

    final = None
    log: list = []
    for update in app.stream({"query": query, "log": []}, {"recursion_limit": 40}):
        for _node, out in update.items():
            for line in out.get("log", []):
                log.append(line)
                logger.info("%s", line)
            if "final_report" in out:
                final = out["final_report"]

    run_dir = None
    for line in log:
        m = _RUN_DIR_RE.search(line)
        if m:
            run_dir = m.group(1).strip()

    if any("aborted: no sources" in line for line in log):
        status = "no_sources"
    elif final is None:
        status = "no_report"
    else:
        status = "completed"

    duration = round(time.perf_counter() - start, 2)
    logger.info("Research finished: status=%s in %.1fs", status, duration)
    return {
        "query": query,
        "status": status,
        "report": final or "No report produced.",
        "run_dir": run_dir,
        "log": log,
        "duration_s": duration,
    }
