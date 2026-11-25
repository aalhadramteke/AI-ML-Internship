# Demo Script

A rehearsed 4-minute live demonstration of the dashboard and the workflow behind
it. Every question used here has an answer that exists verbatim in `docs/`, so
the output is verifiable on screen.

Target time: 3 minutes 30 seconds, including one full run.

---

## Before you start

Complete [DEMO_CHECKLIST.md](DEMO_CHECKLIST.md) first. In short:

```powershell
ollama serve            # one terminal, leave running
ollama list             # confirm qwen2.5:3b is present
python -m streamlit run app.py --server.port 8520
```

Then open http://localhost:8520 and leave the dashboard loaded.

**Warm the model before the audience arrives.** A cold model adds 10 to 30
seconds to the first response, which reads as a hang:

```powershell
python main.py "What is the price of the Sunrise Notes Pro plan?"
```

That single run also confirms the workflow works and populates `output/` with a
fallback artifact.

## The question to use

Use this one, in this order:

> How many paid leave days do Sunrise Tech employees get?

Why this question:

- the answer ("18 paid leave days per year") is one line in
  `docs/company_info.txt`, so anyone can check it
- it produces a short report, so the demo does not stall on generation
- it exercises retrieval, analysis, both critics, and citation assembly
- a factual number makes hallucination visible if it happens

Alternatives, all answerable from `docs/`:

| Question | Expected answer |
| --- | --- |
| What is the price of the Sunrise Notes Pro plan? | 499 rupees per month |
| Can a small AI model run on a 6 GB graphics card? | Yes, about 2 GB in 4-bit |
| How many days per week can Sunrise Tech employees work from home? | Two |
| What are the drawbacks of multi-agent systems? | More time, more calls, error propagation |

Avoid questions that are only partially covered. A visible "gap" in the report
is honest but takes time to explain under pressure.

---

## Run of show

### 0:00 - Frame the problem (20 seconds)

Say:

> Research assistants built on a single prompt sound confident even with no
> evidence. This one is built so that unsupported claims cannot reach the report.
> It runs entirely on this machine.

Point at the sidebar: backend, model, source mode, documents folder.

### 0:20 - Show the corpus (15 seconds)

Click **Source mode** and show it is `Local documents`. Point at the sidebar
field for the documents folder (`docs`).

Say:

> Three text files: company information, notes on local AI models, and a
> description of multi-agent systems. No internet used.

### 0:35 - Submit the question (10 seconds)

Paste the question into the input and click **Run research**.

Say:

> Five agents now run in sequence, and two of them are allowed to send work back.

### 0:45 - Narrate the wait (60 to 120 seconds)

Do not stay silent. Point at the Activity tab as lines appear:

> The coordinator just split this into sub-questions. The research agent embedded
> the question and pulled the closest chunks. The analyzer is extracting claims
> and attaching source ids.

When the analyzer finishes:

> It has findings. Now the critic scores them out of ten. If the score is under
> eight, it either revises the analysis or asks for another search.

When the writer runs:

> The writer only sees the structured findings, not the raw documents. That is
> deliberate: it cannot cite anything the analyzer did not find.

If the run is slower than expected, fill the time with the architecture
explanation in [PRESENTATION_NOTES.md](PRESENTATION_NOTES.md), section 4. Do not
apologise for the wait; describe what is happening.

### 1:45 - Show the report

Switch to the **Report** tab.

- Read the executive summary line that contains **18**.
- Point at an inline citation such as `[2]`.
- Scroll to **References** and show that `[2]` resolves to `company_info.txt`.

Say:

> Every citation id is checked twice: once when findings are extracted, once when
> the draft is reviewed. The finalizer then rebuilds the reference list from the
> ids that survived, so a reference cannot point at something that was never
> retrieved.

### 2:20 - Show the critique

Switch to the **Review** tab.

- Point at the critic score and verdict.
- Point at the issues list, including any medium or low notes.

Say:

> The critic is a separate agent with a separate prompt. It is not grading its own
> work. Its verdict is also overridden in code: it cannot approve a score below
> eight, and it cannot approve a draft that cites an id outside the source list.

### 2:45 - Show the evidence

Switch to the **Sources** tab.

- Show the source titles and the query that retrieved each one.
- Expand one source to show the text the model actually saw.

Say:

> Each row records which sub-query retrieved it, so the report can be audited at
> the level of the chunk.

### 3:10 - Show the artifacts

Switch to **Activity**, then optionally open the run folder in Explorer.

Say:

> The run is saved as a folder: report, log, sources, findings, and metadata. The
> CLI writes exactly the same artifacts, which is how the two interfaces stay
> consistent.

### 3:30 - Close

Say:

> That is the whole design: retrieval that refuses to guess, two critics that can
> reject, and citation checks that are plain Python rather than prompt
> instructions.

---

## Optional second demo: the refusal path

If you have 90 seconds spare and want to show the safety behaviour, this is the
strongest thing in the project.

1. In the sidebar, set **Documents folder** to an empty folder name, for example
   `docs_empty`.
2. Ask the same question and run.
3. The run stops immediately with a "No sources retrieved" report that explains
   why and how to fix it.
4. Set the folder back to `docs`.

Say:

> With no evidence, the system does not answer. It exits and says so. That
> behaviour is a graph edge, not a suggestion in a prompt.

Only do this if the first run was fast. Restoring the folder is required before
any further questions.

---

## Fallback plan

If the live run fails or is too slow:

1. **Use a saved run.** Open `output/` and pick the most recent successful run
   folder. The dashboard does not reload old runs, so instead open `report.md`
   directly and walk through it, then show `meta.json` for the scores.
2. **Reuse the warm-up run.** The pre-demo `main.py` execution printed a full
   report in the terminal. Switch to that terminal and walk through the output
   and log lines.
3. **Explain the log instead of the UI.** `run.log` contains the sequence of
   agent decisions, including the critic verdict and score. That is enough to
   narrate the architecture.

Never debug live. If an error appears, say what the error means
(for example, "Ollama is not responding"), switch to the fallback, and move on.

## Recovery commands

```powershell
# check the model server
curl http://localhost:11434/api/tags

# check the dashboard
curl http://localhost:8520/_stcore/health

# restart the dashboard on a free port
python -m streamlit run app.py --server.port 8521

# find and kill a stale server on Windows
netstat -ano | findstr :8520
taskkill /F /PID <pid>
```

In Git Bash, replace `findstr` with `grep` and use `taskkill //F //PID <pid>`.
