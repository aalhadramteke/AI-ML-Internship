# Interview Questions and Answers

Ten technical questions on architecture, implementation, debugging, and future
work, with answers written to be spoken in about 90 seconds each.

## Numbers worth memorising

| Fact | Value |
| --- | --- |
| Graph nodes | 8 (5 agents plus plan, research, finalize stages) |
| Specialist agents | 5: coordinator, research, analyzer, critic, writer |
| Critic passes | 2: findings, draft |
| Loop caps | analysis 3, writer 2 |
| Approval threshold | 8 out of 10, and no high-severity issue |
| Model backends | 5 |
| Chunk size | 900 characters, 120 overlap |
| Prompt budget | 24 sources, 1200 characters each |
| Model calls per run | 5 on the happy path, about 11 worst case |

---

## 1. Walk me through the architecture end to end.

**Short answer:** It is a LangGraph state machine with eight nodes over one
shared `TypedDict`. The coordinator decomposes the question, the research agent
retrieves evidence, the analyzer extracts cited findings, a critic scores them,
the writer drafts from findings only, a second critic reviews the draft, and the
finalizer rebuilds citations and saves the run.

**Detail:**

1. `coordinator_plan` asks the model for three to five sub-questions and one or
   two search queries per sub-question. It caps at six sub-questions and ten
   queries, and resets the iteration counters.
2. `research` runs each query through local dense retrieval, optionally web
   search, deduplicates by URL, and assigns stable integer ids.
3. If no sources were found, the graph routes to a terminal `no_sources` node
   that explains the failure and stops.
4. `analyzer` receives the sources and extracts findings, each with a claim and a
   list of source ids, plus themes, contradictions, and coverage gaps.
5. `critic_findings` scores the findings and returns `approve`, `revise`, or
   `re_search`. `revise` loops to the analyzer; `re_search` writes new queries and
   loops to research.
6. `writer` drafts a structured Markdown report using only the findings, with
   inline `[n]` citations.
7. `critic_draft` reviews faithfulness, coverage, and citation validity.
8. `finalize` strips invalid citation ids, builds the reference list from what
   was actually cited, appends review notes if the loops hit their cap, and saves
   the artifacts.

**If they push on the "five agents" claim:** the coordinator does two jobs, plan
and finalize, so there are eight nodes and five distinct agent roles. I use
"agent" for a role with its own prompt and responsibility, not for a separate
process.

---

## 2. Why LangGraph and multiple agents instead of one prompt or a simple chain?

**Short answer:** Because the requirement is not "generate text", it is "produce
an answer I can audit and that can be rejected". A single prompt has no place to
remove an unsupported claim. A chain has a fixed order, so it cannot go back for
more evidence or redo a weak draft.

**Detail:**

- A linear chain handles the easy case and fails quietly on the hard one: if
  retrieval misses, the chain still writes a report from thin evidence.
- The graph gives three things: conditional routing (revise, re-search, abort),
  per-node streaming for progress, and a serialisable state that doubles as the
  saved artifact.
- Separate prompts mean separate context windows. The writer never sees raw
  source text; the critic never sees its own draft as the author. That keeps each
  prompt small enough for a 3B model and keeps the responsibilities testable.

**Trade-off I would state openly:** a graph is more machinery than a `while` loop
with a few `if` branches. At this size, either would work. I chose the graph
because routing becomes explicit and each edge is easy to reason about, which is
the point of a project about trust.

**If they ask "isn't this just prompt chaining?":** no, because the control flow
depends on model output. A chain's next step is fixed at build time; here the
critic's verdict chooses the edge, and the caps override it.

---

## 3. How does state work, and what happens when two nodes write the same key?

**Short answer:** State is a single `TypedDict` with `total=False`. Each node
returns only the keys it changes, and LangGraph merges that dict into the
previous state. Keys replace by default; `log` is annotated with `operator.add`,
so it concatenates instead of overwriting.

**Detail:**

```python
class State(TypedDict, total=False):
    query: str
    plan: Dict[str, Any]
    search_queries: List[str]
    sources: List[Dict[str, Any]]
    findings: Dict[str, Any]
    critique: Dict[str, Any]
    draft: str
    draft_critique: Dict[str, Any]
    analysis_iter: int
    writer_iter: int
    forced_caveats: List[str]
    final_report: str
    log: Annotated[List[str], operator.add]
```

- `total=False` is what allows partial updates. Without it, every node would have
  to return a complete state object.
- The reducer matters because the log is written by seven different nodes. If it
  replaced, only the last node's line would survive.
- Everything else replaces on purpose. `sources` is the one list a node extends
  manually: `research` copies the existing list before appending, because the
  default merge would replace it.
- Because the state holds only JSON-serialisable values, `storage.py` dumps
  `sources.json` and `findings.json` directly, and the dashboard can render a
  finished run without re-executing anything.

**If they ask about mutation bugs:** the copy in `research_agent`
(`sources = list(state.get("sources", []))`) is deliberate. Mutating the incoming
list would make the node impure and produce different results on replay.

---

## 4. How do you prevent hallucinated citations?

**Short answer:** Six layers, and three of them are deterministic code, not
prompts. Retrieval or abort, cite or drop, two-sided critique, fabricated-id
detection, citation sanitising, and explicit caveats when a loop hits its cap.

**Detail:**

1. **Retrieve or abort.** If `sources` is empty after research, routing goes to
   `no_sources` and the run ends with an explanation. The model gets no chance to
   answer from memory.
2. **Cite or drop.** `_clean_findings` intersects every finding's `source_ids`
   with the ids that exist. A finding with an empty intersection is discarded,
   not repaired. Contradiction entries go through the same filter.
3. **Findings critique.** The critic sees the findings and the sources side by
   side and scores accuracy, bias, credibility, and coverage.
4. **Draft critique.** A second critic checks the draft against the approved
   findings, so prose cannot drift beyond the evidence.
5. **Fabrication detection.** `_cited_ids` extracts every `[n]` from the draft,
   subtracts the valid ids, and any remainder becomes a high-severity issue. A
   high-severity issue blocks approval regardless of score.
6. **Sanitising.** `finalize` rewrites citation groups, dropping ids that do not
   exist, and builds the reference list only from ids that survived.

**Why not just tell the model not to hallucinate:** because a prompt is a
suggestion. Layers 2, 5, and 6 cannot be argued with; they are string and set
operations. The prompts reduce the frequency, the code guarantees the invariant.

**Honest limitation:** this guarantees valid citations, not correct ones. A
finding can cite a real chunk that does not support it. Catching that needs
per-claim verification, which is the next improvement.

---

## 5. How do you handle structured output from a small model?

**Short answer:** Assume it will be wrong. Three mechanisms in order: an explicit
schema in the prompt, tolerant parsing, and one repair call. Then normalise the
result in code so the rest of the system only ever sees a valid structure.

**Detail:**

- `chat_json` appends "Return ONLY valid JSON. No prose, no markdown fences."
- Parsing first strips code fences and tries `json.loads`. If that fails, it
  scans for the first `{` or `[` and calls `raw_decode`, which tolerates trailing
  prose after a valid object.
- If parsing still fails, the malformed output is sent back once with a minimal
  repair prompt, and the result is parsed again. If that fails too, the exception
  propagates and the run fails visibly.
- Normalisation is separate and always runs. `_clean_findings` accepts a list or
  a dict, coerces ids with `_as_int`, clamps confidence to `[0, 1]`, and fills
  defaults for missing keys. `_evaluate_critique` normalises the verdict against
  an allowed set and clamps the score to `[0, 10]`.
- The analyzer has one extra retry with a schema reminder that names the exact
  required fields, because the most common failure was findings returned as plain
  strings with no ids.

**Why not force a stricter decoder:** Ollama's `format: json` helps, but it
guarantees syntactic JSON, not schema conformance. The schema still has to be
enforced.

**Trade-off:** the repair call adds latency and a model call on the failure path.
I accepted that because the alternative, continuing with an empty plan, produces
a confident report with no basis.

---

## 6. Why two critics? Explain the exit conditions.

**Short answer:** Because "the evidence is weak" and "the writing drifted" need
different remedies. One critic cannot ask for more research and for a rewrite at
the same time without confusing the loop.

**Detail:**

`critic_findings` returns one of three verdicts:

- `approve`: score at least 8 and no high-severity issues
- `revise`: reasoning or accuracy problems, loop to `analyzer` with the issues in
  the prompt
- `re_search`: coverage gaps or weak sources, write `gap_queries` into
  `search_queries`, loop to `research`

`critic_draft` returns only `approve` or `revise`, because by then the evidence
is settled and the only question is whether the prose is faithful.

Exit conditions are enforced in two places. The router sends work to the writer
when the verdict is `approve` **or** `analysis_iter >= 3`; the critic records open
issues into `forced_caveats` when it hits the cap, so the final report carries an
explicit "Review Notes" section instead of pretending the draft passed.

**Why the caps are necessary:** a small model can oscillate between `revise` and
the same critique forever. A cap turns a potential infinite loop into a bounded
run with a visible quality signal.

**Trade-off:** two critics cost two extra model calls per full cycle. I kept them
because a single critic grading its own output tends to agree with itself, and
because the two verdicts map cleanly onto two different actions.

**If they ask what happens on a low score with no issues:** the score policy
forces `revise`; approval is only possible above the threshold.

---

## 7. Explain the retrieval design. Why dense-only, and how would you improve it?

**Short answer:** Documents are read recursively, whitespace-normalised, chunked
at 900 characters with 120 overlap, embedded locally with all-MiniLM-L6-v2, and
ranked by cosine similarity. Dense-only was the fastest path to semantic search
without a vector database. The improvement I would make first is hybrid retrieval
plus a reranker.

**Detail:**

- Chunking is character-based, not token-based, because the target model varies.
  900 characters keeps each chunk well inside the prompt budget while giving the
  analyzer enough context to extract a claim.
- Embeddings are L2-normalised, so the dot product is cosine similarity and no
  metric code is needed. Ranking is `argsort` descending, top five per query.
- The index is a module-level cache, built once per process. Repeat questions in
  one dashboard session pay only the query embedding.
- Deduplication is by URL, and ids come from `len(sources) + 1`, so they stay
  stable across loop iterations. That stability is what makes citation ids safe.
- Prompt construction caps at 24 sources and 1200 characters each to stay inside
  an 8k context.
- Web mode is bounded: five results per query, at most two page fetches per query,
  with a 10 second timeout and script and style tags stripped.

**What dense-only gets wrong:** exact identifiers, product codes, and rare names
often lose to semantically similar but wrong chunks. A keyword index such as BM25
combined with dense scores, then a cross-encoder reranker on the top 20, would fix
most of it.

**Other improvements:** token-aware chunking with heading structure preserved,
incremental indexing keyed on file mtime, and a per-chunk freshness timestamp.

---

## 8. How do you keep it local and swappable across backends?

**Short answer:** Two abstractions. Retrieval and embeddings are local by
default, and inference goes through a single `chat()` function that dispatches to
one of five provider implementations. Configuration is environment variables with
sane defaults, overridable at runtime from the dashboard.

**Detail:**

- `llm.py` exposes `chat()` and `chat_json()`, and a `_BACKENDS` dict maps a name
  to a function. Adding a provider means adding one function and one entry, with
  no change to `agents.py`.
- The five backends: Ollama over HTTP, an OpenAI-compatible endpoint (LM Studio,
  llama.cpp), local Transformers with optional 4-bit quantisation, the Hugging
  Face Inference API, and Anthropic.
- Documents never leave the machine in local mode. Embeddings are computed by
  sentence-transformers locally. In web mode only the generated queries go to
  DuckDuckGo, never document text.
- Fetched HTML is stripped of scripts, styles, navigation, header, and footer
  before it can enter a prompt.
- The dashboard applies settings by patching module attributes, because those
  modules bind config values at import time. Changing the model in the sidebar
  then affects the next run without a restart.

**Honest caveats:** hosted backends are opt-in and read keys from environment
variables. There is no authentication and no per-user isolation; this is a
single-user local tool, and the README states that rather than implying
otherwise.

**If they ask about secret handling:** no key is ever written to state or to
`output/`; `meta.json` records the backend name and model name only.

---

## 9. Tell me about the hardest bug you hit and how you diagnosed it.

**Short answer:** Two, and both were integration bugs rather than algorithm bugs.
The dashboard crashed on load with a duplicate widget id because the file
contained two sidebar blocks that registered the same selectbox. And settings
changed in the UI had no effect, because four modules had already bound config
values at import time.

**Detail, duplicate element id:**

- The symptom was `StreamlitDuplicateElementId` on first render, before any user
  input.
- Streamlit assigns widget ids from label, key, and position, so two selectboxes
  with the same label in two `with st.sidebar:` blocks collide.
- The file had grown by copy-paste and held the same panel twice, about three
  thousand lines with two of almost everything.
- Fix: rewrite the file around a single sidebar function, and give every widget
  an explicit unique key (`sb_backend`, `sb_model_ollama`, `query_text`). Explicit
  keys make the failure impossible to reintroduce by moving code around.

**Detail, settings not applying:**

- The symptom was changing the model in the sidebar and still getting answers
  from the old model.
- Cause: `agents.py`, `llm.py`, and `tools.py` do `from config import BACKEND`,
  which copies the value at import. Updating `config.BACKEND` afterwards has no
  effect on the already-bound name.
- Fix: `apply_settings()` sets the attributes on all four modules explicitly, and
  invalidates the cached document index when the docs folder or embedding model
  changes.
- What I would do differently: pass a settings object into the graph at
  construction time. That is the clean fix; patching is the pragmatic one, and it
  is documented in the architecture so the next person is not surprised.

**What this taught me:** with Streamlit specifically, verify the app with a real
render, not just an import. I used Streamlit's `AppTest` harness afterwards to
load the app, click an example, submit an empty query, and inject sample results,
checking for zero exceptions each time.

---

## 10. How would you test and evaluate this, and what would you improve next?

**Short answer:** Today the guards are deterministic and testable, but there is no
evaluation harness, which is the biggest gap. Next I would build a fixed question
set with expected claims and score citation validity, claim coverage, and refusal
behaviour on every prompt change.

**Detail, testing layers:**

- **Unit:** `_clean_findings`, `_evaluate_critique`, citation sanitising, and the
  routers are pure functions over dicts. They are the highest-value tests because
  they enforce the trust invariants.
- **Contract:** feed each agent canned model output, including malformed JSON,
  and assert the normalised shape and the routing decision.
- **Integration:** run the graph with a stub `chat()` that returns fixture
  responses. That tests topology without a model.
- **UI:** Streamlit's `AppTest` for load, submit, empty query, and populated
  results.
- **End to end:** a small set of questions with answers known to be in `docs/`,
  run against the real model, checked by hand.

**Detail, evaluation:**

- Build 20 questions: some answerable, some deliberately unanswerable, some with
  a contradiction between two documents.
- Metrics: citation validity (must be 100 percent, it is enforced), claim
  support rate (sampled), coverage of sub-questions, refusal rate on unanswerable
  questions, and latency.
- Compare prompt and model changes against a baseline stored in `history.csv`,
  which already records both critic scores and iteration counts per run.

**Roadmap, in priority order:**

1. Hybrid retrieval with a reranker, to reduce weak-chunk wins.
2. Per-claim verification: check each sentence against the chunk it cites, rather
   than reviewing the draft as a whole.
3. The evaluation harness above, wired as a gate.
4. A job queue so long runs survive a browser refresh, and run history in the
   dashboard.
5. Streaming tokens, so the wait shows progress instead of a spinner.

**Closing line if asked "is it production ready":** no, and it does not claim to
be. It is a correct-by-construction prototype: the invariants hold, the scale
story is documented, and the next step is measurement, not more features.
