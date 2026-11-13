# Day 19: LangGraph Fundamentals
**Date:** 13/11/2026

---

## Learning Objectives

* **Understand Nodes:** Learn how Python functions read from and write updates to a shared workflow state.
* **Understand Graphs:** Build directed graph workflows (`StateGraph`) connecting functional nodes from entry point to `END`.
* **Apply State Management:** Define a structured schema (`GraphState`) to pass data, attempt counters, errors, and conversation history across steps.
* **Implement Conditional Flow & Loops:** Use conditional edges and router functions to dynamically branch execution and create self-correcting retry loops.
* **Implement Memory:** Persist workflow state and multi-turn conversation context across sessions using `MemorySaver` and `thread_id`.

---

## Tasks Completed

* **Stateful RAG Pipeline Implementation:** Built a LangGraph workflow (`User` → `Question` → `Retriever` → `LLM` → `Answer` → `Memory`) integrating local Ollama (`llama3.2`), HuggingFace embeddings, and a FAISS vector store.
* **State & Node Architecture:** Defined `GraphState` (`TypedDict`) and implemented seven modular nodes (`question_node`, `retriever_node`, `rewrite_query_node`, `llm_node`, `fallback_node`, `answer_node`, `memory_node`) to handle query normalization, retrieval, generation, and history tracking.
* **Conditional Routing & Self-Correction Loops:** Built `route_after_retrieval` and `route_after_llm` routers to handle empty retrieval results (via query rewriting loops) and LLM failures (via bounded retry loops).
* **Workflow Analysis Report & Error Handling:** Analyzed failure scenarios (e.g., zero retrieved documents for ambiguous queries or model runtime errors) and implemented recovery mechanisms using `try-except` blocks, retry caps (`MAX_RETRIEVAL_RETRIES`, `MAX_LLM_RETRIES`), and a graceful `fallback_node`.
* **Updated LangGraph Diagram (Project Practical):** Mapped the end-to-end graph topology including conditional decision branches, the query-rewrite loop, LLM retry loop, fallback path, and `MemorySaver` checkpointing.

---

## Status

* LangGraph notebook implementation and multi-turn memory testing completed.
* Workflow analysis report, error handling notes, and updated LangGraph diagram compiled.
* Learning objectives (nodes, graphs, state, conditional flow, loops, memory) covered and verified in code.
* Deliverables compiled for submission.
