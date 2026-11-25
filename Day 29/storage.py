"""Run artifact persistence and execution history logging."""

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


def _slug(text: str, max_len: int = 50) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()[:max_len].strip("-")
    return slug or "query"


def _write_json(path: str, payload) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)


def _write_run_artifacts(run_dir: str, state: dict, report: str, metadata: dict) -> list[dict]:
    with open(os.path.join(run_dir, "report.md"), "w", encoding="utf-8") as handle:
        handle.write(report)
    with open(os.path.join(run_dir, "run.log"), "w", encoding="utf-8") as handle:
        handle.write("\n".join(state.get("log", [])))

    serialized_sources = [
        {k: src.get(k) for k in ("id", "title", "url", "snippet", "query")}
        for src in state.get("sources", [])
    ]
    _write_json(os.path.join(run_dir, "sources.json"), serialized_sources)
    _write_json(os.path.join(run_dir, "findings.json"), state.get("findings", {}))
    _write_json(os.path.join(run_dir, "meta.json"), metadata)
    return serialized_sources


def _append_history_csv(run_dir: str, status: str, metadata: dict, num_sources: int) -> None:
    history_path = os.path.join(OUTPUT_DIR, "history.csv")
    is_new_file = not os.path.exists(history_path)
    with open(history_path, "a", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        if is_new_file:
            writer.writerow(
                [
                    "timestamp",
                    "query",
                    "status",
                    "model",
                    "source_mode",
                    "num_sources",
                    "findings_score",
                    "draft_score",
                    "folder",
                ]
            )
        writer.writerow(
            [
                metadata["timestamp"],
                metadata["query"],
                status,
                metadata["model"],
                SOURCE_MODE,
                num_sources,
                metadata["findings_score"],
                metadata["draft_score"],
                run_dir,
            ]
        )


def save_run(state: dict, report: str, status: str) -> str:
    """Persist run report, logs, JSON artifacts, and CSV history; return run directory."""
    now = datetime.now()
    stamp = now.strftime("%Y%m%d_%H%M%S")
    run_dir = os.path.join(OUTPUT_DIR, f"{stamp}_{_slug(state.get('query', ''))}")
    os.makedirs(run_dir, exist_ok=True)

    metadata = {
        "timestamp": now.isoformat(timespec="seconds"),
        "query": state.get("query", ""),
        "status": status,
        "backend": BACKEND,
        "model": _model_name(),
        "source_mode": SOURCE_MODE,
        "num_sources": len(state.get("sources", [])),
        "analysis_iters": state.get("analysis_iter", 0),
        "writer_iters": state.get("writer_iter", 0),
        "findings_score": state.get("critique", {}).get("score"),
        "draft_score": state.get("draft_critique", {}).get("score"),
        "plan": state.get("plan", {}),
    }
    sources = _write_run_artifacts(run_dir, state, report, metadata)
    _append_history_csv(run_dir, status, metadata, len(sources))
    return run_dir
