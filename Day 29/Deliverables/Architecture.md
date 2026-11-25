# Architecture

This document describes how the research assistant is built, why each decision
was made, and where the boundaries are.

---

## 1. Problem and constraints

The system answers a research question from a known document set, with evidence
the reader can check. That goal sets the constraints:

| Constraint | Consequence in the design |
| --- | --- |
| Answers must be traceable | Every finding carries source ids; the finalizer rewrites the reference list |
| Must run without cloud APIs | Local embeddings, local LLM by default, file-based storage |
| Small models are unreliable at structured output | Schema normalisation, a JSON repair retry, deterministic guards |
| Research is iterative, not one-shot | Two critic loops with explicit exit conditions |
| Single developer, small codebase | Plain Python modules, no framework beyond LangGraph |

The alternative design, one large prompt that says "research this and cite
sources", fails the first constraint: there is no point at which unsupported
claims can be removed.

## 2. System context

```
                 +---------------------------+
                 |  Streamlit dashboard      |
                 |  app.py                   |
                 +-------------+-------------+
                               |
                 +-------------v-------------+
                 |  CLI                      |
                 |  main.py                  |
                 +-------------+-------------+
                               |
                 +-------------v-------------+
                 |  LangGraph workflow       |
                 |  graph.py + agents.py     |
                 +------+-------------+------+
                        |             |
          +-------------v--+       +--v------------------+
          | llm.py         |       | tools.py            |
          | 5 backends     |       | local index + web   |
          +------+---------+       +--+---------------+--+
                 |                    |               |
        +--------v--------+   +-------v------+  +-----v------+
        | Ollama / HF /   |   | docs/*.txt   |  | DuckDuckGo |
        | OpenAI-compat / |   | *.md *.pdf   |  | + HTTP     |
        | Anthropic       |   +--------------+  +------------+
        +-----------------+

                 storage.py -> output/<run>/ + history.csv
```

Everything except the optional hosted backends and optional web search runs on
the local machine.

## 3. Module responsibilities

| Module | Owns | Does not own |
| --- | --- | --- |
| `config.py` | Environment parsing, defaults, thresholds | Runtime UI overrides |
| `state.py` | The shared state contract | Validation of values |
| `llm.py` | Provider selection, message shape, JSON extraction | Prompt content |
| `tools.py` | Chunking, embedding index, search, fetch | Deciding what to search for |
| `agents.py` | Prompts, normalisation, routing guards | Graph topology |
| `graph.py` | Nodes, edges, conditional routing | Node internals |
| `storage.py` | Artifacts, CSV history | Report content |
| `app.py` | UI, session state, runtime config | Workflow logic |

The dependency direction is one-way: `app.py` and `main.py` depend on `graph.py`,
which depends on `agents.py`, which depends on `llm.py`, `tools.py`, and
`storage.py`. No agent imports another agent.

## 4. Shared state

`state.py` defines a single `TypedDict` that every node reads and partially
updates.

```python
class State(TypedDict, total=False):
    query: str
    plan: Dict[str, Any]            # sub_questions, scope
    search_queries: List[str]       # pending queries for the research agent
    sources: List[Dict[str, Any]]   # {id, title, url, snippet, text, query}
    findings: Dict[str, Any]        # findings, themes, contradictions, gaps
    critique: Dict[str, Any]        # verdict, score, issues, gap_queries
    draft: str
    draft_critique: Dict[str, Any]
    analysis_iter: int
    writer_iter: int
    forced_caveats: List[str]
    final_report: str
    log: Annotated[List[str], operator.add]
```

Two properties matter:

1. **`total=False`** means a node returns only the keys it changes. LangGraph
   merges the returned dict into the previous state, so no node needs to
   reconstruct the whole object.
2. **`log` is annotated with `operator.add`**, which makes it a reducer: each
   node appends its lines and the runtime concatenates them instead of
   overwriting. This is the only accumulating field; everything else replaces.

The practical benefit is that the entire run is one serialisable value. That is
why `storage.py` can dump `findings.json` and `sources.json` straight from state
without a translation layer, and why the dashboard can render an old state
without replaying the graph.

## 5. Control flow

```
START
  |
coordinator_plan
  |
research ----------------------------> no_sources -> END
  |
analyzer
  |
critic_findings
  | approve / cap                      | revise        | re_search
  |                                    v               v
  |                                 analyzer        research
  v
writer
  |
critic_draft
  | approve / cap                      | revise
  |                                    v
  v                                 writer
finalize
  |
 END
```

The router predicates are deliberately small and pure:

| Router | Condition | Destination |
| --- | --- | --- |
| `route_after_research` | `bool(state["sources"])` | `analyzer` or `no_sources` |
| `route_after_findings_critic` | verdict `approve` or `analysis_iter >= 3` | `writer` |
| | verdict `re_search` and `gap_queries` present | `research` |
| | otherwise | `analyzer` |
| `route_after_draft_critic` | verdict `approve` or `writer_iter >= 2` | `finalize` |
| | otherwise | `writer` |

The loop caps are checked in both the router and the critic, because the critic
also needs to record caveats when the cap is reached. Keeping the check in both
places is intentional duplication of a safety condition, not accidental.

## 6. Node contracts

### 6.1 `coordinator_plan`

- **Input:** `query`
- **Output:** `plan`, `search_queries`, and resets `sources`, `analysis_iter`,
  `writer_iter`, `forced_caveats`
- **Guarantee:** at least one sub-question and one search query, even if the
  model returns malformed JSON. Sub-questions are capped at 6 and queries at 10.
- **Failure mode:** falls back to the raw question as the only sub-question.

It resets counters because the same state may be reused across runs in one
dashboard session.

### 6.2 `research`

- **Input:** `search_queries`, existing `sources`
- **Output:** `sources` (extended), empty `search_queries`
- **Guarantee:** no duplicate URLs, monotonically increasing integer ids
- **No LLM call:** retrieval is deterministic, which makes it the cheapest node
  and the easiest to reason about.

Ids are assigned from `len(sources) + 1`, so they remain stable across loop
iterations and are safe to use as citation keys.

### 6.3 `no_sources`

Terminal node. Writes a report explaining why the run stopped plus a concrete
fix (add documents, set `RA_SOURCE=web`), saves the run with status
`no_sources`, and returns it as `final_report`. This is the single most important
node for trustworthiness: the system refuses to answer rather than guess.

### 6.4 `analyzer`

- **Input:** `query`, `plan.sub_questions`, `sources`, prior `critique.issues`
- **Output:** `findings`, incremented `analysis_iter`
- **Guarantee:** every surviving finding cites at least one id present in
  `sources`; confidence is clamped to `[0, 1]`
- **Retry:** if normalisation leaves zero findings, one retry with an explicit
  schema reminder naming the required fields

`_clean_findings` is the busiest function in the project. It accepts a list or a
dict, coerces ids to ints, intersects them with the valid id set, drops findings
with an empty intersection, clamps confidence, and normalises contradictions the
same way. The model is asked for a schema; the function enforces it.

### 6.5 `critic_findings`

- **Input:** `plan`, `findings`, `sources`
- **Output:** `critique`
- **Possible verdicts:** `approve`, `revise`, `re_search`
- **Deterministic override:** a programmatic high-severity issue is injected when
  there are no valid findings, so an empty result can never be approved
- **Policy:** `score >= 8` and no high-severity issues forces `approve`
  regardless of what the model said

`re_search` additionally writes `gap_queries` back into `search_queries`, which
is what makes the loop able to add evidence rather than only rewrite prose.

On the cap, the critic copies its open issues into `forced_caveats` so they
survive into the final report.

### 6.6 `writer`

- **Input:** `query`, `findings`, previous `draft`, `draft_critique.issues`,
  `forced_caveats`
- **Output:** `draft`, incremented `writer_iter`
- **Guarantee:** if there are no findings, it writes an explicit "no content"
  report rather than calling the model
- **Prompt rules:** required sections, inline `[n]` citations only from
  `valid_source_ids`, no self-written references section

The writer never sees raw source text, only the analyzer's structured findings.
That is what keeps the citation contract narrow enough to verify.

### 6.7 `critic_draft`

- **Input:** `plan`, `findings`, `draft`
- **Output:** `draft_critique`
- **Deterministic check:** extracts every `[n]` from the draft, subtracts the
  valid source ids, and adds a high-severity issue for any fabricated id
- **Verdicts:** `approve` or `revise` only

This is the second independent check on grounding: the first checks findings
against sources, this one checks prose against findings plus citation ids.

### 6.8 `finalize`

Pure Python, no model call:

1. collect cited ids that exist in `sources`
2. rewrite `[n, m]` groups, dropping ids that do not exist
3. append a reference list built from the ids actually cited
4. append a "Review Notes" section when caveats or an unapproved draft remain
5. save artifacts with status `ok` or `ok_with_caveats`

Sanitising here rather than trusting the writer is deliberate: the last step
before the user sees the text is deterministic.

## 7. Anti-hallucination layers

| Layer | Mechanism | Where |
| --- | --- | --- |
| 1. Retrieve or abort | Empty source list ends the run | `route_after_research` |
| 2. Cite or drop | Findings without valid ids are removed | `_clean_findings` |
| 3. Two-sided critique | Findings checked against sources, draft against findings | `critic_findings`, `critic_draft` |
| 4. Fabrication detection | Unknown `[n]` ids become high-severity issues | `critic_draft` |
| 5. Citation sanitising | Unknown ids removed, references rebuilt from what survives | `coordinator_finalize` |
| 6. Honest failure | Loop caps produce explicit caveats, not silent acceptance | `forced_caveats` |

No single layer is sufficient. Layers 2, 4, and 5 are deterministic and cannot be
talked out of their decision by a persuasive model output.

## 8. LLM abstraction

`llm.py` exposes two functions:

```python
chat(system, user, max_tokens=4000, json_mode=False) -> str
chat_json(system, user, max_tokens=4000) -> dict
```

`chat` dispatches to one of five provider functions through a dict lookup, so
adding a backend means adding one function and one entry, with no changes in
`agents.py`.

| Backend | Transport | Notes |
| --- | --- | --- |
| `ollama` | HTTP `/api/chat` | `format: json` when structured output is needed |
| `openai_compat` | HTTP `/chat/completions` | LM Studio, llama.cpp server |
| `hf_local` | Transformers pipeline | Optional 4-bit quantisation, cached pipeline |
| `hf_api` | `huggingface_hub` | Needs `HF_TOKEN` |
| `anthropic` | `anthropic` SDK | Needs `ANTHROPIC_API_KEY` |

### JSON reliability

Three mechanisms, in order:

1. **Append an instruction:** `Return ONLY valid JSON. No prose, no markdown fences.`
2. **Parse defensively:** strip code fences, try `json.loads`, then scan for the
   first `{` or `[` and use `raw_decode`, which tolerates trailing prose.
3. **Repair once:** if parsing still fails, send the bad output back with a
   minimal "fix this into valid JSON" prompt.

If repair also fails, the exception propagates and the run fails visibly. That is
preferable to silently continuing with an empty plan, which would produce a
confident but baseless report.

## 9. Retrieval pipeline

```
docs/ (recursive)
   -> read .txt/.md as UTF-8, .pdf via pypdf
   -> collapse whitespace
   -> chunk: 900 chars, 120 overlap, step 780
   -> embed: all-MiniLM-L6-v2, normalised
   -> cache in a module-level LocalIndex
   -> query embed -> dot product -> argsort -> top n
```

Because embeddings are L2-normalised, the dot product equals cosine similarity;
no separate metric implementation is needed. The index is built once per process
and reused, so repeat questions in one dashboard session pay only the query
embedding cost.

Web mode adds a second path: DuckDuckGo search (5 results per query), and for at
most the top 2 results per query an HTTP fetch with a 10 second timeout, script
and style tags removed, text truncated to 3000 characters. Every network call is
wrapped and returns `[]` or `""` on failure, so a dead network degrades to local
results instead of crashing the run.

Prompt construction is budgeted in `agents.py`: at most 24 sources and 1200
characters each, which keeps the analyzer prompt inside an 8k context on a small
model.

## 10. Persistence

`storage.py` writes one directory per run plus one CSV row.

```
output/
  20261125_121500_how-many-paid-leave-days/
    report.md
    run.log
    sources.json
    findings.json
    meta.json
  history.csv
```

`meta.json` carries the fields needed to reconstruct a run for analysis: query,
backend, model, source mode, source count, both critic scores, both iteration
counts, and the plan. `history.csv` is append-only with a UTF-8 BOM so it opens
correctly in Excel on Windows.

Reports are Markdown by design: portable, diffable, and renderable by both the
CLI and the dashboard.

## 11. Dashboard design

`app.py` is a single Streamlit script with three concerns:

1. **Configuration.** The sidebar writes to `st.session_state`, then
   `apply_settings()` patches attributes on the already-imported `config`,
   `agents`, `llm`, and `tools` modules. Those modules bind values at import
   time, so patching is what allows a settings change to take effect without a
   process restart. It also invalidates the cached document index when the docs
   folder or embedding model changes.
2. **Execution.** A run streams graph updates, appends log lines, and stores the
   final state in `st.session_state.results`. The UI reads only from session
   state, so tab switches and reruns never re-execute the workflow.
3. **Presentation.** Five tabs (Report, Findings, Review, Sources, Activity) over
   one result object, with metrics for sources, findings, and critic score. All
   model-derived text is HTML-escaped before entering markup; the report body is
   rendered as Markdown rather than injected HTML.

The theme lives in `.streamlit/config.toml` (`base = "light"`) instead of CSS
overrides, because Streamlit's widget internals follow the base theme; forcing
colours with CSS leaves inputs and selectboxes unreadable.

## 12. Cost and latency profile

Per run, LLM calls are:

| Path | Calls |
| --- | --- |
| Happy path | plan + analyze + critic + write + critic = 5 |
| One analyzer retry | +1 |
| One re-search round | +2 (analyze, critic) |
| One writer revision | +2 (write, critic) |
| Worst case at caps | about 11 |

Retrieval costs no model tokens. The dominant cost is prompt size in the analyzer
and writer, which is why both are capped in `config.py`. With a 3B local model,
wall-clock time is dominated by generation on CPU or a small GPU; the dashboard
shows progress incrementally for that reason.

## 13. Security and privacy

- No document text leaves the machine in `local` mode; embeddings and inference
  are local.
- Hosted backends are opt-in and require their own keys, read from environment
  variables only.
- Web mode sends only the generated search queries to DuckDuckGo, not document
  contents.
- Fetched HTML is stripped of scripts, styles, navigation, header, and footer
  elements before entering a prompt.
- There is no authentication, no multi-user state, and no write access outside
  `output/`; it is a single-user local tool, and the README says so.

## 14. Failure modes

| Failure | Detection | Behaviour |
| --- | --- | --- |
| No documents / empty retrieval | `sources` empty | Stop, explain, save run |
| Model returns prose instead of JSON | Parse failure | Fence strip, `raw_decode`, repair retry |
| Findings cite nonexistent ids | `_clean_findings` | Drop those findings |
| Draft cites nonexistent ids | `_cited_ids` diff | High-severity issue, revise |
| Critic too lenient | Score and severity policy | `approve` forced only above threshold |
| Loops never converge | Iteration counters | Cap, record caveats, finish |
| Ollama not running | `httpx` exception | Surfaced in the UI error panel |
| Embedding model not cached | First-run download | One-time delay, documented |

## 15. Decisions and trade-offs

**LangGraph over a hand-written loop.** The graph makes routing visible and
testable, and gives per-node streaming for free. The cost is a dependency and a
small amount of indirection. At this size, a `while` loop would also work; the
graph is chosen for inspectability, which is the point of the project.

**Two critics instead of one.** A single critic cannot separate "the evidence is
weak" from "the writing drifted from the evidence". Splitting them gives distinct
remedies: `re_search` versus `revise`. The cost is one extra model call per
cycle.

**Structure-then-prose.** The writer sees findings, not sources. This narrows the
verification surface and shortens the prompt, at the price of losing nuance that
exists only in raw text.

**Deterministic guards around a probabilistic core.** Schema enforcement,
citation filtering, and caps are Python. This is less flexible than prompting but
predictable, which matters more for a trust-focused tool.

**File-based storage instead of a database.** Zero setup, inspectable output,
trivially portable. It does not scale to concurrent writers, which is acceptable
for a single-user tool.

**Module attribute patching for settings.** Pragmatic given config-at-import
design. A dependency-injected settings object would be cleaner; the patch is
documented so the next maintainer is not surprised.

## 16. Extension points

| Goal | Change |
| --- | --- |
| Add a model provider | One function and one dict entry in `llm.py` |
| Add a retrieval source (SQL, Confluence) | A function in `tools.py`, dispatch in `search()` |
| Add an agent stage | Node function in `agents.py`, node and edges in `graph.py`, key in `State` |
| Improve retrieval quality | Add a reranker between `local_search` and prompt construction |
| Add evaluation | Run a fixed question set, compare `meta.json` scores across runs |

## 17. What changes at scale

- Retrieval would move to a vector store with incremental indexing instead of a
  full in-memory rebuild per process.
- Runs would be queued as background jobs with a progress channel, not held open
  in a Streamlit session.
- Storage would move to a database with per-user isolation.
- The critic contract would gain a per-claim verification step, checking each
  sentence against its cited chunk rather than reviewing the draft as a whole.
- The evaluation harness would become a gate: a fixed question set with expected
  claims, scored on citation validity and coverage, run before every prompt
  change.
