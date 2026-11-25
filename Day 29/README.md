# Multi-Agent Research Assistant

A local-first research system built on LangGraph. Five specialised agents plan a
question, retrieve evidence, extract source-backed findings, critique their own
work, and produce a cited Markdown report. It runs against documents on your own
machine, with optional web search, and no cloud service or API key required.

The project ships with two interfaces over the same workflow:

- a Streamlit dashboard (`app.py`) for interactive use
- a command-line runner (`main.py`) for scripting and automation

---

## Why this exists

Large language models answer confidently even when they have no evidence. This
project constrains that behaviour structurally:

- every finding must cite a source id that actually exists, or it is discarded
- the critic can send work back for revision or for more research
- the finalizer strips citation ids that were never retrieved
- if retrieval returns nothing, the run stops instead of inventing an answer

## Architecture at a glance

```
question
   |
coordinator_plan ---> research ---> (no sources) ---> no_sources -> stop
                          |
                       analyzer
                          |
                   critic_findings <---- re_search ----+
                     |        |                       |
                  approve   revise ---> analyzer      |
                     |                                |
                    writer                            |
                     |                                |
                  critic_draft -- revise --> writer   |
                     |                                |
                  finalize <--------------------------+
                     |
            report.md + citations + run artifacts
```

Node names match `graph.py`: `coordinator_plan`, `research`, `no_sources`,
`analyzer`, `critic_findings`, `writer`, `critic_draft`, `finalize`.

Full detail is in [ARCHITECTURE.md](ARCHITECTURE.md).

## Quick start

```powershell
pip install -r requirements.txt

# local model (default backend)
ollama serve
ollama pull qwen2.5:3b

# dashboard
python -m streamlit run app.py

# or the CLI
python main.py "How many paid leave days do Sunrise Tech employees get?"
```

Put `.txt`, `.md`, or `.pdf` files in `docs/` for local retrieval. Runs are saved
under `output/`. See [setup.md](setup.md) for the full setup and troubleshooting
guide.

## Project layout

| File | Responsibility |
| --- | --- |
| `app.py` | Streamlit dashboard: configuration, run trigger, results views |
| `main.py` | CLI entrypoint |
| `graph.py` | LangGraph wiring: nodes, edges, conditional routing |
| `agents.py` | The five agents, routing guards, output normalisation |
| `state.py` | Shared `State` TypedDict |
| `llm.py` | Backend abstraction (`chat`, `chat_json`) for five providers |
| `tools.py` | Local document index, web search, page fetch |
| `storage.py` | Run artifacts, JSON dumps, `history.csv` |
| `config.py` | Environment-driven settings and defaults |
| `docs/` | Your source documents |
| `output/` | Saved runs |

## Interfaces

### Dashboard

```powershell
python -m streamlit run app.py
```

Sidebar controls backend, model name, source mode, documents folder, and the
quality thresholds. The main pane holds the question, five example prompts, and
the results: status, source and finding counts, critic score, then tabs for
Report, Findings, Review, Sources, and Activity. Reports download as Markdown.
Settings are applied to the running workflow immediately, without a restart.

### Command line

```powershell
python main.py "Your research question"
```

Prints the workflow log and the final report to stdout, and writes the same
artifacts to `output/`.

## Configuration

Defaults live in `config.py` and can be overridden with environment variables.

| Variable | Default | Purpose |
| --- | --- | --- |
| `RA_BACKEND` | `ollama` | `ollama`, `openai_compat`, `hf_local`, `hf_api`, `anthropic` |
| `RA_OLLAMA_MODEL` | `qwen2.5:3b` | Local model name |
| `RA_OLLAMA_HOST` | `http://localhost:11434` | Ollama endpoint |
| `RA_OLLAMA_CTX` | `8192` | Context window |
| `RA_OPENAI_BASE` | `http://localhost:1234/v1` | OpenAI-compatible server |
| `RA_MODEL` | `claude-sonnet-4-5` | Model name for the Anthropic backend |
| `RA_HF_MODEL` | `Qwen/Qwen2.5-3B-Instruct` | Transformers or Inference API model |
| `RA_EMBED_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` | Local embedding model |
| `RA_SOURCE` | `local` | `local`, `web`, or `both` |
| `RA_DOCS_DIR` | `docs` | Document folder |
| `RA_MAX_SOURCES` | `24` | Sources passed to prompts |
| `RA_SOURCE_CHARS` | `1200` | Characters per source in prompts |
| `RA_CHUNK_CHARS` | `900` | Retrieval chunk size |
| `RA_CHUNK_OVERLAP` | `120` | Chunk overlap |

Loop limits `MAX_ANALYSIS_ITERS` (3) and `MAX_WRITER_ITERS` (2), and the approval
score `PASS_SCORE` (8), are defined in `config.py` and adjustable from the
dashboard sidebar.

## Output artifacts

Each run creates `output/<timestamp>_<slug>/`:

```
report.md        final report with references
run.log          agent log lines
sources.json     retrieved sources and metadata
findings.json    structured findings, themes, contradictions, gaps
meta.json        backend, model, scores, iteration counts, plan
```

`output/history.csv` accumulates one row per run.

## Design principles

1. **Grounding over fluency.** Unsupported findings are dropped before they can
   reach the writer.
2. **Deterministic guards around a probabilistic core.** Citation validation,
   loop caps, and citation stripping are plain Python, not model behaviour.
3. **Local by default.** Dense retrieval uses a local sentence-transformers
   model; the default LLM is a local Ollama model.
4. **Small, inspectable modules.** Each agent is a function over shared state, so
   it can be tested and replaced independently.

## Known limitations

- Small local models are slower and less consistent than hosted models, and
  occasionally need the JSON repair path.
- Retrieval is dense-only, with no reranking or hybrid keyword search.
- Reports inherit the quality of the retrieved documents; the system flags gaps
  but cannot fill them.
- No authentication or multi-user isolation; the dashboard is a single-user tool.

## Further reading

- [ARCHITECTURE.md](ARCHITECTURE.md) - design, state schema, control flow
- [setup.md](setup.md) - install, run, troubleshoot
- [DEMO.md](DEMO.md) - rehearsed demo script
- [INTERVIEW_QA.md](INTERVIEW_QA.md) - technical questions and answers
- [PRESENTATION_NOTES.md](PRESENTATION_NOTES.md) - timed talk track
- [DEMO_CHECKLIST.md](DEMO_CHECKLIST.md) - practice and pre-demo checks
- [SLIDES.md](SLIDES.md) - slide deck with speaker notes
