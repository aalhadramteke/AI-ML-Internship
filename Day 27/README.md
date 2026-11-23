# Day 27: Sprint Planning Exercise (MiniGPT)
**Date:** 23/11/2026

## Overview

A sprint plan for **MiniGPT**, a small GPT-style language model built from scratch in PyTorch. The plan covers effort estimation, prioritization by business value and dependencies, a project timeline, and risk analysis.

| Item | Details |
|---|---|
| Project | MiniGPT: small LLM built from scratch |
| Sprint goal | Train a small GPT that generates coherent text, with measured loss and perplexity, and serve it through a simple demo |
| Sprint length | 3 weeks (15 working days) |
| Model scale | About 10–30M parameters, 6 layers, 6 heads, 384 embedding dim, 256-token context |
| Hardware target | 6GB GPU (fp16, gradient accumulation) |
| Stack | Python, PyTorch, BPE tokenizer, FastAPI or Streamlit |

## Learning Objectives

- **Understand Sprint Planning:** Break an AI project into time-boxed sprints with a clear goal and Definition of Done.
- **Apply Effort Estimation:** Rate each task as Low, Medium, or High complexity based on difficulty, uncertainty, and risk.
- **Apply Prioritization:** Rank tasks by business value and dependencies using P1 to P4 levels.
- **Understand Task Dependencies:** Identify which tasks block others and sequence the work accordingly.
- **Design a Project Timeline:** Map phases, tasks, and milestones across the sprint, with risks and mitigation.

## Task Priority Table

| ID | Task | Complexity | Business Value | Depends On | Priority |
|----|------|-----------|----------------|-----------|----------|
| T1 | Define scope, model size, success metrics | Low | High | None | P1 |
| T2 | Environment setup (PyTorch CUDA, repo, logging) | Low | High | T1 | P1 |
| T3 | Dataset collection, cleaning, train/val split | Medium | High | T1 | P1 |
| T4 | BPE tokenizer (train, encode, decode) | Medium | High | T3 | P1 |
| T5 | Data pipeline (tokenized files, batch loader) | Low | High | T4 | P1 |
| T6 | Transformer architecture | High | High | T2 | P1 |
| T7 | Training loop (AdamW, LR schedule, fp16, checkpoints) | High | High | T5, T6 | P1 |
| T8 | Overfit-a-tiny-batch sanity test | Low | High | T7 | P1 |
| T9 | Full training run and hyperparameter tuning | High | High | T8 | P2 |
| T10 | Text generation (temperature, top-k, top-p) | Medium | High | T6, T9 | P2 |
| T11 | Evaluation (val loss, perplexity, sample quality) | Medium | High | T9, T10 | P2 |
| T12 | Experiment comparison (model size or context length) | Medium | Medium | T9 | P3 |
| T13 | Demo app (FastAPI or Streamlit) | Medium | Medium | T10 | P3 |
| T14 | Documentation, architecture diagram, results report | Low | Medium | T11, T13 | P3 |
| T15 | Stretch: fine-tune on a domain dataset | High | Low | T11 | P4 |

**Priority key:** P1 = core build, P2 = training and results, P3 = delivery, P4 = stretch.

**Effort summary:** 4 Low, 6 Medium, 5 High. The riskiest tasks are T6, T7, and T9.

## Project Timeline

| Days | Phase | Tasks | Milestone |
|------|-------|-------|-----------|
| Day 1 | Planning | T1, T2 | Scope fixed, GPU confirmed working |
| Days 2–3 | Data | T3 | Clean corpus ready |
| Days 3–5 | Tokenizer and pipeline | T4, T5 | Data loader returns token batches |
| Days 4–7 | Model | T6 | Forward pass works, parameter count verified |
| Days 7–9 | Training code | T7, T8 | Loss drops on a tiny batch |
| Days 9–12 | Full training | T9 | Final checkpoint saved |
| Days 11–13 | Generation and evaluation | T10, T11 | Perplexity and samples documented |
| Days 13–14 | Delivery | T12, T13 | Demo running |
| Day 15 | Wrap-up | T14 (T15 if time) | Report and demo complete |

## Risks and Mitigation

| Risk | Impact | Mitigation |
|------|--------|-----------|
| GPU runs out of memory | High | Small model, fp16, gradient accumulation, short context, gradient checkpointing if needed |
| Training too slow or unstable | High | Tiny-batch overfit test first, LR warmup and decay, frequent checkpoints |
| Model generates gibberish | Medium | Use a simple dataset like TinyStories, verify tokenizer and loss curve first |
| Scope creep | Medium | Freeze scope after T1, treat T15 as optional |

## Sprint Review Checklist

- [x] Sprint plan with goal and Definition of Done
- [x] Effort estimates for all 15 tasks
- [x] Priorities based on business value and dependencies
- [x] Timeline with milestones
- [x] Risks and mitigation documented
- [ ] Tokenizer round-trips text correctly (implementation phase)
- [ ] Tiny-batch overfit test passes (implementation phase)
- [ ] Validation loss and perplexity meet target (implementation phase)
- [ ] Demo runs and report is complete (implementation phase)

## Status

- Sprint Planning Document completed
- Task Priority Table with complexity and dependencies completed
- Project Timeline with milestones completed
- Risks, mitigation, and review checklist documented
- Deliverables compiled for submission
