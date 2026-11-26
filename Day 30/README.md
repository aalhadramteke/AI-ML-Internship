# Internship Reflection Report

### **Aalhad M. Ramteke** · B.E. CSE (Data Science), PRMCEAM, Badnera-Amravati
### **Role:** AI/ML Project Intern, Linkific
### **Period:** October 2026 – November 2026 (Training)

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Technical Skills Acquired](#2-technical-skills-acquired)
3. [Challenges and How I Worked Through Them](#3-challenges-and-how-i-worked-through-them)
4. [Key Achievements](#4-key-achievements)
5. [Lessons Learned](#5-lessons-learned)
6. [Personal Learning Roadmap (90 Days)](#6-personal-learning-roadmap-90-days)
7. [Acknowledgements](#7-acknowledgements)
8. [Closing Reflection](#8-closing-reflection)

---

## 1. Introduction

When I joined Linkific in October 2026, most of my experience with machine learning lived inside notebooks: load a dataset, train a model, report an accuracy score. This internship changed how I think about the work. Over the following weeks, each daily task added another layer to a real AI system: retrieval, tools, agents, asynchronous APIs, provider selection, and project planning.

The biggest shift was in the question I asked myself. I stopped asking only *"Does the model work?"* and started asking *"Does the whole system work reliably, quickly, and at a sensible cost?"* This reflection looks back at what I learned, what was difficult, what I am proud of, and where I want to go next.

---

## 2. Technical Skills Acquired

| Area | What I learned and built |
|---|---|
| **Retrieval-Augmented Generation (RAG)** | Built a pipeline connecting documents, embeddings, retrieval and an LLM. Ran chunk-size experiments, compared response quality and documented the best configuration with an evaluation table. |
| **Tool and function calling** | Designed tools including a Calculator, Web Search, File Reader and Data Analyzer. Created a Tool Selection Matrix and a practical CSV Analyzer for the company project. Learned tool chaining and error handling. |
| **Multi-agent systems** | Built a Research Assistant with Coordinator, Research, Analyzer, Critic and Writer agents using LangGraph, running locally on Ollama (qwen2.5:3b). Documented the agent communication flow and responsibilities. |
| **Asynchronous API engineering** | Converted a synchronous API to async. Worked with async/await, middleware, background tasks, dependency injection and API versioning, then benchmarked response times before and after. |
| **LLM provider analysis** | Compared OpenAI, Claude, Gemini and Groq on cost, speed and accuracy. Studied token usage and cost optimization for production use. |
| **Project planning** | Planned MiniGPT, a small GPT-style language model built from scratch in PyTorch, as a 15-day sprint with 15 prioritized tasks, complexity estimates and a timeline. |
| **Professional practice** | Wrote structured daily task reports and clear technical documentation, including matrices, flow documents, sequence diagrams and benchmark tables. |

**Core stack:** Python, LangGraph, Ollama, async API patterns, embeddings and vector retrieval, Hugging Face models, Jupyter, PyTorch (planning).

---

## 3. Challenges and How I Worked Through Them

**Running agents on modest hardware.** I chose to run the multi-agent system on a small local model instead of a hosted API. The model was less capable at reasoning, so I compensated with tighter prompts, clearly separated agent roles and a Critic stage that catches mistakes before the final answer.

**Finding the right RAG chunk size.** There was no obvious answer, and my first instinct was unreliable. I learned to test several sizes systematically and judge them with an evaluation table instead of intuition.

**Benchmarking async fairly.** Async programming does not automatically make everything faster. I had to measure before and after under the same conditions so the comparison was honest and meaningful.

**Making tools dependable.** Early versions failed on bad input, missing files and empty results. Adding validation and graceful error handling taught me that an agent is only as reliable as the tools it can call.

**Coordinating several agents.** Deciding who owns which responsibility, and how outputs flow from one agent to the next, took more thought than writing the code. The responsibility matrix and communication log turned out to be as valuable as the implementation.

**Keeping pace with daily deliverables.** Every day brought working code plus documentation. This pushed me to scope tasks carefully, prioritize, and finish things properly instead of leaving them half-polished.

---

## 4. Key Achievements

- Delivered a working RAG pipeline with a documented chunk-size comparison and evaluation table.
- Built a tool-calling toolkit and a CSV Analyzer for the company project.
- Designed and ran a local multi-agent Research Assistant, with a communication flow document and sequence diagram.
- Completed a synchronous-to-asynchronous API migration with a benchmark report and updated documentation.
- Produced a provider comparison covering cost, speed and accuracy across four LLM providers.
- Created a complete sprint plan for MiniGPT with prioritized tasks and a timeline.
- Maintained consistent, structured daily reports throughout the internship.

---

## 5. Lessons Learned

### Technical lessons

- **Retrieval sets the ceiling for RAG.** Chunking, embeddings and retrieval quality matter more than which LLM sits at the end.
- **Agents need clear boundaries.** Narrow roles, defined inputs and outputs, and a reviewing step produce far better results than one large, general agent.
- **Tools should be small, validated and predictable.** The model's decisions are only as good as the tools available to it.
- **Measure before optimizing.** Benchmarks, evaluation tables and cost comparisons beat guesswork every time.
- **There is no single best model.** Choosing a provider is a trade-off between cost, latency and accuracy, and the right answer depends on the use case.

### Professional lessons

- **Documentation is part of the deliverable.** A clear matrix, diagram or report makes work usable by other people, not just by me.
- **Planning saves time.** Estimating complexity, mapping dependencies and setting priorities early prevents wasted effort later.
- **Consistency compounds.** Small, steady daily progress added up to a complete system faster than I expected.
- **Organization matters.** A tidy, reproducible project structure makes every later task easier.

---

## 6. Personal Learning Roadmap (90 Days)

Over the 90 days from December 2026 to February 2027, I will move from building core model components to deploying a production-style AI system and presenting it to employers.

| Phase | Days | Focus | Key activities | Deliverable | Checkpoint |
|---|---|---|---|---|---|
| **1. Foundations** | 1–30 (December) | Core model skills | Weeks 1–2: tokenizer, embeddings, self-attention. Weeks 3–4: transformer block, training loop, text generation. In parallel: hybrid search, re-ranking and evaluation metrics for RAG. | MiniGPT repository with README; improved RAG notebook with metrics | MiniGPT trains and generates text |
| **2. Production engineering** | 31–60 (January) | Deployment and reliability | Weeks 5–6: Dockerize the async API and add basic CI. Weeks 7–8: logging, monitoring, caching, and token and cost optimization on a real workload. | Containerized AI API with benchmark report | API runs from one Docker command with logged requests |
| **3. Showcase and careers** | 61–90 (February) | Capstone and job search | Weeks 9–11: build and publish an end-to-end capstone combining RAG, agents and an API. Weeks 12–13: update portfolio and resume, then apply to AI/ML and Data Science roles. | Published capstone, refreshed portfolio and resume | Capstone live and at least 10 applications sent |

---

## 7. Acknowledgements

I am grateful to the team at Linkific for the opportunity, the structure and the steady stream of practical, well-designed tasks. Each assignment pushed me slightly beyond what I already knew, which is exactly where learning happens. I am also thankful to my college and mentors for the foundation that made this experience possible.

---

## 8. Closing Reflection

This internship gave me hands-on experience across the full AI application stack and a clearer picture of the engineer I want to become: someone who builds AI systems that are reliable, measurable and well documented. I leave with working projects, stronger habits and a realistic plan for what comes next. I intend to carry these lessons into my final two years of study and into my career in applied machine learning and AI engineering.
