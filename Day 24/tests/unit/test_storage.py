import csv
import json
import os

from research import storage

STATE = {
    "query": "What is RAG?",
    "log": ["[coordinator] planned 2 sub-questions", "[research] +1 sources (total 1)"],
    "sources": [{"id": 1, "title": "Doc", "url": "docs/a.md#chunk0", "snippet": "s", "text": "big", "query": "q"}],
    "findings": {"findings": []},
    "analysis_iter": 2,
    "writer_iter": 1,
    "critique": {"score": 8},
    "draft_critique": {"score": 9},
    "plan": {"sub_questions": ["a"]},
}


def test_slug():
    assert storage._slug("Hello, World!!") == "hello-world"
    assert storage._slug("!!!") == "query"
    assert len(storage._slug("a" * 100)) <= 50


def test_model_name_per_backend(monkeypatch):
    monkeypatch.setattr(storage, "BACKEND", "ollama")
    assert storage._model_name() == storage.OLLAMA_MODEL
    monkeypatch.setattr(storage, "BACKEND", "mystery")
    assert storage._model_name() == "mystery"


def test_save_run_writes_all_files(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "OUTPUT_DIR", str(tmp_path / "out"))
    run_dir = storage.save_run(STATE, "# Report", "ok")

    for name in ("report.md", "run.log", "sources.json", "findings.json", "meta.json"):
        assert os.path.isfile(os.path.join(run_dir, name)), name

    assert open(os.path.join(run_dir, "report.md"), encoding="utf-8").read() == "# Report"
    assert "planned 2 sub-questions" in open(os.path.join(run_dir, "run.log"), encoding="utf-8").read()

    sources = json.load(open(os.path.join(run_dir, "sources.json"), encoding="utf-8"))
    assert sources == [{"id": 1, "title": "Doc", "url": "docs/a.md#chunk0", "snippet": "s", "query": "q"}]
    assert "text" not in sources[0]  # full text is not persisted

    meta = json.load(open(os.path.join(run_dir, "meta.json"), encoding="utf-8"))
    assert meta["query"] == "What is RAG?"
    assert meta["status"] == "ok"
    assert meta["num_sources"] == 1
    assert meta["findings_score"] == 8 and meta["draft_score"] == 9
    assert meta["analysis_iters"] == 2 and meta["writer_iters"] == 1


def test_history_csv_has_one_header_and_appends(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "OUTPUT_DIR", str(tmp_path / "out"))
    storage.save_run(STATE, "# R1", "ok")
    storage.save_run({**STATE, "query": "Second question"}, "# R2", "no_sources")

    with open(tmp_path / "out" / "history.csv", newline="", encoding="utf-8-sig") as f:
        rows = list(csv.reader(f))
    assert rows[0][:3] == ["timestamp", "query", "status"]
    assert len(rows) == 3
    assert rows[1][1] == "What is RAG?" and rows[1][2] == "ok"
    assert rows[2][1] == "Second question" and rows[2][2] == "no_sources"


def test_save_run_handles_minimal_state(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "OUTPUT_DIR", str(tmp_path / "out"))
    run_dir = storage.save_run({}, "x", "ok")
    assert os.path.basename(run_dir).endswith("_query")
