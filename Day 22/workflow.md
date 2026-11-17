# **Main flow**
1. **Coordinator: plan.** Splits your question into 3 to 5 sub-questions and search queries.
2. **Research Agent.** Searches `docs\` (or the web) and collects numbered source passages.
3. **Analyzer.** Turns sources into findings, each linked to source ids, with confidence and contradictions.
4. **Critic: findings.** Scores accuracy and coverage, then approves, asks for a revision, or asks for more research.
5. **Writer.** Writes the Markdown report with inline citations like [1].
6. **Critic: draft.** Checks the draft against the findings and catches fake citation ids.
7. **Coordinator: finalize.** Appends the reference list and saves the report, sources and log.

**Feedback loops (dashed arrows)**
- **Need more sources:** The Critic sends the run back to the Research Agent when coverage has gaps.
- **Revise:** The Critic sends reasoning or accuracy problems back to the Analyzer.
- **Revise draft:** The Critic sends the draft back to the Writer for corrections.

# Summary

I built a multi-agent research assistant that runs fully on your own PC. It reads your documents, checks its own work, and saves a cited report.

# Tools & Technologies

- **Python:** The language the whole project is written in.
- **LangGraph:** Connects the five agents into one workflow with feedback loops.
- **Ollama:** Runs the free AI model locally on the GPU.
- **Qwen2.5-3B:** The model that powers every agent.
- **sentence-transformers:** Turns text into vectors so search matches meaning, not keywords.
- **pypdf:** Reads PDF files from your `docs\` folder.
- **httpx:** Talks to the local Ollama server and fetches web pages.
- **ddgs :** Searches the web when you want online sources.
- **Markdown, CSV, JSON files:** Where each run's report, log and history are saved.
- **Backends:** Hugging Face, LM Studio and Claude can replace Ollama if needed.

# Final Output

- **Multi-agent system:** Specialised agents with one controller.
- **RAG:** Answers come from retrieved sources, not model memory.
- **Feedback loops:** The Critic can send work back for revision.
- **Quality gates:** Code rules stop fake citations and empty runs.
- **Local-first:** No cloud, no API keys, no cost.
