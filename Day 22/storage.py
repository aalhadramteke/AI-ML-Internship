import csv
import json
import os
import re
from datetime import datetime

from config import (
    BACKEND,
    HF_MODEL,
    MODEL,
    OLLAMA_MODEL,
    OPENAI_MODEL,
    OUTPUT_DIR,
    SOURCE_MODE,
)


def _model_name() -> str:
    return {
        "ollama": OLLAMA_MODEL,
        "hf_local": HF_MODEL,
        "hf_api": HF_MODEL,
        "openai_compat": OPENAI_MODEL,
        "anthropic": MODEL,
    }.get(BACKEND, BACKEND)


def _slug(text: str, n: int = 50) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()[:n].strip("-")
    return s or "query"


def _dump(path: str, obj) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)


def save_run(state: dict, report: str, status: str) -> str:
    """Save everything about one run. Returns the run folder path."""
    now = datetime.now()
    stamp = now.strftime("%Y%m%d_%H%M%S")
    run_dir = os.path.join(OUTPUT_DIR, f"{stamp}_{_slug(state.get('query', ''))}")
    os.makedirs(run_dir, exist_ok=True)

    with open(os.path.join(run_dir, "report.md"), "w", encoding="utf-8") as f:
        f.write(report)
    with open(os.path.join(run_dir, "run.log"), "w", encoding="utf-8") as f:
        f.write("\n".join(state.get("log", [])))

    sources = [
        {k: s.get(k) for k in ("id", "title", "url", "snippet", "query")}
        for s in state.get("sources", [])
    ]
    _dump(os.path.join(run_dir, "sources.json"), sources)
    _dump(os.path.join(run_dir, "findings.json"), state.get("findings", {}))

    meta = {
        "timestamp": now.isoformat(timespec="seconds"),
        "query": state.get("query", ""),
        "status": status,
        "backend": BACKEND,
        "model": _model_name(),
        "source_mode": SOURCE_MODE,
        "num_sources": len(sources),
        "analysis_iters": state.get("analysis_iter", 0),
        "writer_iters": state.get("writer_iter", 0),
        "findings_score": state.get("critique", {}).get("score"),
        "draft_score": state.get("draft_critique", {}).get("score"),
        "plan": state.get("plan", {}),
    }
    _dump(os.path.join(run_dir, "meta.json"), meta)

    hist = os.path.join(OUTPUT_DIR, "history.csv")
    new = not os.path.exists(hist)
    with open(hist, "a", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        if new:
            w.writerow(
                ["timestamp", "query", "status", "model", "source_mode",
                 "num_sources", "findings_score", "draft_score", "folder"]
            )
        w.writerow(
            [meta["timestamp"], meta["query"], status, meta["model"], SOURCE_MODE,
             meta["num_sources"], meta["findings_score"], meta["draft_score"], run_dir]
        )
    return run_dir