# Presentation Notes

Talk track for a 12-minute presentation with a 3 minute 30 second demo inside it.
The deck is [SLIDES.md](SLIDES.md); the demo procedure is [DEMO.md](DEMO.md).

Target: 12 minutes 15 seconds. Safe range: 10 to 15 minutes.

---

## Timing plan

| Time | Section | Slides | Mode |
| --- | --- | --- | --- |
| 0:00 | Opening and problem | 1 to 2 | Talk |
| 1:00 | Goal and constraints | 3 | Talk |
| 2:00 | Architecture walkthrough | 4 | Talk, point at diagram |
| 3:30 | Agents and shared state | 5 to 6 | Talk |
| 4:30 | Retrieval | 7 | Talk |
| 5:15 | Trust enforced in code | 8 | Talk, slow down here |
| 6:15 | Working with a small model | 9 | Talk |
| 6:45 | Live demo | none | Screen share |
| 10:15 | Challenges and trade-offs | 11 | Talk |
| 11:15 | Results, roadmap, close | 12 | Talk |
| 12:15 | Questions | appendix | Q&A |

Two rules for keeping time: the demo has a hard stop at 10:15, and slide 8 is the
only slide you are allowed to spend more than 60 seconds on.

---

## 0:00 Opening

> "A language model will answer a research question whether or not it has any
> evidence. It will even produce citations. I built a research assistant where
> that is structurally impossible: if the evidence is not there, the run stops,
> and if a claim cannot be traced to a source, it does not reach the report."

Then, in one sentence:

> "It is five agents on a LangGraph, running entirely on this laptop, with three
> local documents as the corpus."

**Do not** open with "so for my project I decided to...". Open with the problem.

## 1:00 Goal and constraints

> "The goal was not a chatbot. It was an answer a reader can audit. That meant
> three things: every claim tied to a chunk by id, work that can be rejected and
> redone, and no dependency on a cloud API."

Name the constraints plainly:

> "I chose a 3 billion parameter model, not a frontier model, because the hard
> case is making a weak model trustworthy. File-based storage, single user,
> minutes per run. Those are deliberate limits, not oversights."

**Pause** after "deliberate limits". It pre-empts half the objections.

## 2:00 Architecture

Point at the loop back to research, then the loop back to the writer, then the
abort branch. Do not read node names left to right.

> "Eight nodes, one shared state. The straight line is the happy path. The two
> branches going backwards are the interesting part: the critic can send work back
> for more evidence, or back for a rewrite. And this branch exits without
> answering if retrieval returns nothing."

> "It is a graph rather than a chain because the next step depends on what the
> critic decides, and a chain's next step is fixed when you build it."

## 3:30 Agents and state

Cover the separation of powers, not the table row by row.

> "Five roles. The coordinator plans and assembles. Research retrieves. The
> analyzer turns sources into claims with ids. The critic scores and can reject.
> The writer drafts. The important part is what they cannot see: the writer never
> sees raw documents, and the critic never writes the draft it reviews."

On state, one sentence is enough:

> "One typed state, partial updates merged per node, and the log is an appending
> reducer. Everything in it is serialisable, so the saved run is literally a dump
> of the final state."

Then the caps:

> "Analysis is capped at three passes, the writer at two, and approval needs eight
> out of ten with no high-severity issue. A loop that cannot converge is a bug."

## 4:30 Retrieval

> "Local dense retrieval, no vector database. Documents are chunked at 900
> characters with 120 overlap, embedded with a small sentence-transformers model,
> and ranked by cosine similarity. Vectors are normalised, so the dot product is
> the cosine."

> "Every chunk gets a stable integer id, and that id is what the report cites.
> Deduplication is by URL, so two queries cannot produce the same citation twice."

Mention the budget:

> "Prompts are capped at 24 sources and 1200 characters each, which keeps the
> analyzer inside an 8k context."

## 5:15 Trust enforced in code

This is the slide to slow down on. Say the framing sentence, then the table.

> "Six layers. Three of them are code, not prompts: no sources means no run,
> findings without valid ids are dropped, and unknown citation ids are stripped at
> the end."

> "A prompt is a suggestion. A set intersection is not."

> "What this guarantees is that every citation resolves. It does not guarantee the
> citation supports the claim. That is the honest limit, and it is why per-claim
> verification is next."

The last sentence is important: volunteering the limitation is more convincing
than being caught by it in questions.

## 6:15 Small model reliability

> "A 3B model drifts from the schema. In practice it returned findings as plain
> strings with no ids, and it wrapped JSON in prose. So there are three defences:
> normalise in code, parse tolerantly, and allow exactly one repair call that sends
> the bad output back."

> "If repair fails, the run fails visibly. I would rather have a red error than a
> confident report built on an empty plan."

## 6:45 Demo

Switch to the dashboard. Follow [DEMO.md](DEMO.md). Keep talking through the run;
the narration is in that file at the 0:45 mark.

Hard stop at 10:15. If the run is still going, switch to the warm-up output in
the terminal and narrate the log.

## 10:15 Challenges

Pick two stories, not five bullets.

> "The two hardest problems were both integration, not algorithms. One: the
> dashboard crashed on load because the file had two sidebar blocks registering
> the same widget, so Streamlit raised a duplicate id. Two: changing the model in
> the sidebar had no effect, because four modules had already copied config values
> at import time."

For each, give diagnosis and fix in one sentence:

> "The fix for the first was one sidebar, explicit keys on every widget. For the
> second, an apply-settings function that patches each module and invalidates the
> document index. The clean fix would be passing a settings object into the graph;
> patching is what I did, and it is documented."

## 11:15 Results and close

> "What works today: end-to-end runs on three local documents, fully offline,
> reports with citations that resolve, and a refusal path when evidence is
> missing."

> "What is next, in order: hybrid retrieval with a reranker, per-claim
> verification, then an evaluation set that gates prompt changes."

Close on the design principle, not on the feature list:

> "The thing I would defend is the refusal. Most assistants are optimised to
> always produce something. This one is optimised to know when it cannot."

Then: "Happy to take questions."

---

## Cue card

Print or keep this beside the laptop.

```
PROBLEM     confident answers, no evidence
GOAL        auditable answer, local, weak model
ARCH        8 nodes, 2 loops, 1 abort branch
ROLES       writer never sees sources
            critic never writes the draft
STATE       1 TypedDict, log is a reducer
RETRIEVAL   900/120 chunks, cosine, stable ids
TRUST       6 layers, 3 deterministic
            cites resolve, support not guaranteed
MODEL       schema drift -> normalise, repair once
DEMO        leave days -> 18 -> [2] -> company_info
CHALLENGE   duplicate widget id; config at import
NEXT        hybrid + reranker, per-claim, eval gate
CLOSE       optimised to know when it cannot
```

---

## If you have only 10 minutes

Cut: slide 9 (small model reliability) down to one sentence on slide 8, and skip
the retrieval chunking detail. Keep the demo and the refusal slide untouched.

Revised: 2:00 architecture, 4:30 trust, 6:00 demo, 9:30 close.

## If you have 15 minutes

Add: a 90 second appendix walkthrough of `meta.json` and `history.csv` after the
demo, and the optional refusal demo from [DEMO.md](DEMO.md). Add one more
challenge story rather than more slides.

---

## Delivery notes

- **Point, do not read.** Every slide has fewer than five lines so you can speak
  around them.
- **Pause in three places:** after "deliberate limits", after "a set intersection
  is not", and after the closing line.
- **Do not apologise for latency.** Say "the analyzer is extracting claims now"
  and keep going.
- **Numbers, not adjectives.** "Three deterministic layers", not "very robust".
- **One claim per sentence** during the demo narration. The audience is reading
  the screen while listening.
- **Hands off the keyboard** while talking about architecture; cursor movement
  distracts.
- If a run errors, name the cause in one sentence, switch to the saved artifact,
  and continue. No debugging in front of an audience.

## Likely questions, and where the full answer lives

| Question | One-line response | Full answer |
| --- | --- | --- |
| Why not one prompt? | No point at which an unsupported claim can be removed | Q2 |
| How do you stop hallucinated citations? | Six layers, three deterministic | Q4 |
| What if the model returns bad JSON? | Normalise, parse tolerantly, repair once, then fail loudly | Q5 |
| Why two critics? | Different remedies: more evidence versus a rewrite | Q6 |
| How would you scale retrieval? | Hybrid retrieval plus reranking, then a vector store | Q7 |
| Is it production ready? | No, and it does not claim to be; invariants hold, evaluation is next | Q10 |
| What was the hardest bug? | Duplicate Streamlit widget ids, then config bound at import | Q9 |

Full written answers: [INTERVIEW_QA.md](INTERVIEW_QA.md).

---

## Rehearsal plan

Three passes, each with one goal.

1. **Timing pass, no audience.** Read the cue card only. Record yourself. Mark
   the time at each slide change. Goal: finish between 11:30 and 12:30.
2. **Demo pass, live model.** Run the full deck with the real demo. Goal: the run
   completes inside its slot and the narration covers the wait without gaps.
3. **Hostile pass, one person.** They interrupt with two questions from the table
   above. Goal: answer in under 30 seconds and return to the next slide with a
   transition sentence.

After pass three, trim anything you stumbled on twice. A sentence you cannot say
smoothly will not survive the real room.
