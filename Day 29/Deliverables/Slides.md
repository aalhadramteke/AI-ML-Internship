# Slides

Twelve slides for a 10 to 15 minute talk, with the content and the speaker notes
for each. Paste the body text into PowerPoint, Google Slides, or Keynote, then
redraw the two diagrams.

Deck conventions: light background, one accent colour (`#2563EB`), one idea per
slide, no more than five lines of body text, no emoji.

---

## Slide 1 - Title

**Multi-Agent Research Assistant**
A local-first research pipeline that cites its sources

Your name, role, date

> **Notes:** Open by naming the one thing you want remembered: this system is
> built so it cannot cite something it did not retrieve. Keep the title slide up
> for under 15 seconds.

---

## Slide 2 - The problem

**A confident answer is not a supported answer**

- A single-prompt assistant answers whether or not it has evidence
- Citations are written by the same model that wrote the claim
- There is no point in the pipeline where a wrong claim can be removed
- For research work, an unsupported sentence is worse than no sentence

> **Notes:** Give one concrete example, ideally from your own testing: ask a model
> about a fact that is not in the documents and watch it produce a plausible
> number. Pause after the last line. This is the motivation for every design
> decision that follows.

---

## Slide 3 - What I set out to build

**Answer from a known corpus, with evidence a reader can check**

- Five specialised agents instead of one general prompt
- Every claim tied to a retrieved chunk by id
- Work that can be rejected and redone
- Runs fully locally: no API key, no document leaving the machine

**Constraints I accepted**

- A 3B parameter model, not a frontier model
- File-based storage, single user
- Minutes per run, not seconds

> **Notes:** Naming constraints early buys credibility and pre-empts the "why
> didn't you just use GPT-4" question. Say explicitly: the design has to work
> with a weak model, because that is the hard case.

---

## Slide 4 - Architecture

**One graph, eight nodes, one shared state**

```
question
   |
coordinator_plan -> research -> [no sources] -> no_sources -> stop
                       |
                    analyzer
                       |
                critic_findings <--- re_search --+
                  |        |                     |
               approve   revise -> analyzer      |
                  |                              |
                 writer                          |
                  |                              |
              critic_draft -- revise -> writer   |
                  |                              |
               finalize <------------------------+
                  |
        report + references + artifacts
```

> **Notes:** Do not read the diagram node by node. Point at three things: the
> loop back to research, the loop back to writer, and the abort branch. Then say
> the rest is a straight line. If asked why this is a graph rather than code, the
> answer is that routing is visible and each edge is testable.

---

## Slide 5 - The five agents

| Agent | Job | Can it change the plan? |
| --- | --- | --- |
| Coordinator | Split the question, assemble the report | Yes, owns the plan |
| Research | Retrieve and deduplicate evidence | No, but can be re-triggered |
| Analyzer | Extract cited findings, themes, contradictions | No |
| Critic | Score findings and drafts, request rework | Yes, via verdicts |
| Writer | Draft from findings only | No |

**Separation of powers:** the writer never sees raw sources; the critic never
writes the draft it reviews.

> **Notes:** Emphasise the last line. Independence is what makes the critic
> meaningful. A single agent checking its own output tends to agree with itself.

---

## Slide 6 - Shared state and control

**A single typed state, merged per node**

```python
class State(TypedDict, total=False):
    query, plan, search_queries, sources
    findings, critique, draft, draft_critique
    analysis_iter, writer_iter, forced_caveats
    final_report
    log: Annotated[List[str], operator.add]
```

- `total=False`: each node returns only what it changed
- `operator.add` on `log`: appends instead of overwriting
- State is serialisable, so it becomes the saved artifact for free

**Loop limits are explicit:** analysis 3, writer 2, approval 8/10

> **Notes:** The reducer is the one LangGraph detail worth explaining. Without
> it, every node would have to carry the log forward. Then state the caps: a
> loop that cannot converge is a bug, not a feature.

---

## Slide 7 - Retrieval

**Local dense retrieval, no vector database**

```
docs/ -> read (.txt .md .pdf) -> chunk 900 / overlap 120
      -> embed with all-MiniLM-L6-v2 -> normalised vectors
      -> query embed -> dot product -> top 5 per query
      -> deduplicate by URL, assign stable integer ids
```

- Normalised embeddings mean dot product equals cosine similarity
- The index is built once per process and reused
- Prompt budget: max 24 sources, 1200 chars each
- Web mode is optional, bounded to 5 results and 2 page fetches per query

> **Notes:** Mention the failure handling: every network call is wrapped and
> returns empty on error, so a dead connection degrades to local results instead
> of killing the run.

---

## Slide 8 - Trust is enforced in code

**Six layers, three of them deterministic**

| Layer | Mechanism |
| --- | --- |
| 1 | No sources means no run |
| 2 | Findings without valid source ids are dropped |
| 3 | Findings critiqued against sources |
| 4 | Draft critiqued against findings |
| 5 | Unknown `[n]` ids flagged, then stripped |
| 6 | Loop caps produce explicit caveats |

> **Notes:** This is the central slide. Say the key sentence: layers 2, 4 and 5
> are plain Python, so a persuasive model cannot override them. If you only get
> one slide in a short talk, use this one.

---

## Slide 9 - Working with a small model

**Reliability features that exist because 3B models are inconsistent**

- Schema normalisation: accept a list or a dict, coerce ids, clamp scores
- One retry with an explicit schema reminder if extraction returns nothing
- JSON extraction tolerant of prose and code fences
- One repair call that sends malformed output back for correction
- Deterministic overrides: a score below 8 cannot be approved

> **Notes:** Be specific about what failed first. The honest version: the model
> sometimes returned findings as plain strings with no ids, and sometimes wrapped
> JSON in prose. Each feature here maps to an observed failure.

---

## Slide 10 - Interfaces

**Same workflow, two entry points**

- **Dashboard:** configure, run, then inspect Report, Findings, Review, Sources,
  Activity
- **CLI:** `python main.py "question"` for scripting and batch use
- Both write identical artifacts: report, log, sources, findings, metadata
- Settings apply at runtime by patching module configuration, no restart

> **Notes:** Show the dashboard here if the demo is separate, or skip this slide
> and let the demo cover it. Call out the artifact folder: it is why runs are
> auditable after the fact.

---

## Slide 11 - Challenges and trade-offs

**What was hard, and what it cost**

- Small-model JSON drift, solved with normalisation plus one repair, not with a bigger model
- Hallucinated citation ids, solved by validating twice and sanitising at the end
- Two critic loops doubled calls, accepted for separable remedies
- Runtime settings versus config read at import, solved by explicit patching
- Dense-only retrieval has no reranking, so weak chunks can win

> **Notes:** Pick two of these to tell as stories with the bug, the diagnosis,
> and the fix. Do not list all five at equal weight; the audience remembers
> stories, not inventories.

---

## Slide 12 - Results and next steps

**What works today**

- End-to-end runs on three local documents, fully offline
- Reports with verifiable citations and honest limitations
- Refuses to answer when evidence is missing

**Next, in order**

1. Hybrid retrieval with a reranker
2. Per-claim verification against the cited chunk
3. An evaluation set with citation-validity scoring in CI
4. Background job queue and run history in the dashboard

> **Notes:** End on the refusal behaviour, because it is the most defensible
> design choice in the project. Then invite questions with a specific hook: "the
> part I would most like a second opinion on is evaluation."

---

## Optional appendix slides

Keep these after the closing slide, for questions only.

**A. Backend matrix**

| Backend | Transport | Requires |
| --- | --- | --- |
| ollama | HTTP `/api/chat` | Local Ollama server |
| openai_compat | HTTP `/chat/completions` | LM Studio or llama.cpp |
| hf_local | Transformers pipeline | torch, optional 4-bit |
| hf_api | huggingface_hub | `HF_TOKEN` |
| anthropic | anthropic SDK | `ANTHROPIC_API_KEY` |

**B. Run artifacts**

```
output/<timestamp>_<slug>/
  report.md  run.log  sources.json  findings.json  meta.json
output/history.csv
```

**C. Call budget**

| Path | Model calls |
| --- | --- |
| Happy path | 5 |
| One retry | 6 |
| One re-search | 7 |
| One writer revision | 9 |
| Worst case at caps | about 11 |

**D. Configuration defaults**

`RA_BACKEND=ollama`, `RA_OLLAMA_MODEL=qwen2.5:3b`, `RA_SOURCE=local`,
`RA_DOCS_DIR=docs`, analysis cap 3, writer cap 2, pass score 8.
