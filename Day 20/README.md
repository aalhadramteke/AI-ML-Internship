# Day 20: AI Tools & Function Calling

Reusable, LLM-callable tools with function-calling schemas, a central dispatcher, tool chaining, and a uniform error-handling layer. Also includes a practical **CSV Analyzer** tool, built as both a Python module and a Jupyter Notebook.

**Date:** 14/11/2026

---

## Features

- 8 tools: Calculator, Web Search, Database Tool, File Reader, Weather Tool, Email Tool, Date Tool, Data Analyzer
- Central registry (`@tool` decorator) and dispatcher (`call_tool()`)
- Schema export in **OpenAI** and **Anthropic** function-calling formats
- Tool chaining with `run_chain()` (stops cleanly at the first failure)
- Uniform response format and layered error handling
- Practical project: **CSV Analyzer** (`.py` module and `.ipynb` notebook)

---

## Project Structure

```
tool_project/
├── agent_tools.py             # 8 tools, registry, dispatcher, chaining, demo
├── csv_analyzer_tool.py       # Practical project: CSV Analyzer
├── csv_analyzer_tool.ipynb    # CSV Analyzer as a self-contained notebook
├── db_query_tool.py           # Read-only SQL helper used by the Database Tool
└── README.md
```

---

## Tools

| Tool | Purpose |
|---|---|
| `calculator` | Exact math using a safe AST parser (no `eval`) |
| `web_search` | Current web information (Tavily API, mock fallback without a key) |
| `database_tool` | Read-only SQL on SQLite (`schema` and `query` actions) |
| `file_reader` | Reads `.txt`, `.md`, `.csv`, `.json`, `.pdf` from the data directory |
| `weather_tool` | Current weather by city (Open-Meteo, no API key) |
| `email_tool` | Sends email via SMTP (dry run by default) |
| `date_tool` | `now`, `add_days`, `diff_days`, `weekday` |
| `data_analyzer` | Quick CSV summary: shape, dtypes, missing values, stats |
| `csv_analyzer` | Practical project: deep CSV analysis (see below) |

---

## Response Format

Every tool returns the same structure:

```python
{"ok": True,  "data": {...}}                                         # success
{"ok": False, "error": {"type": "...", "message": "...", "retryable": False}}   # failure
```

---

## Safety and Error Handling

| Layer | Technique |
|---|---|
| Input | Required and unknown argument validation |
| Calculator | AST-based parser, exponent limit |
| Database | Single `SELECT`/`WITH` only, forbidden keyword check, read-only connection, row cap |
| Files | Path sandbox blocks `../` traversal |
| Email | `dry_run=True` by default |
| Network | Timeout plus retry with exponential backoff, `retryable` flag |
| Fallback | Web search returns a flagged mock result when no API key is set |
| Last resort | Catch-all returns `internal_error` instead of crashing |

---

## CSV Analyzer (Practical Project)

| Action | What it does |
|---|---|
| `profile` (default) | Stats, missing %, duplicates, outliers, quality warnings |
| `group_by` | Aggregate a metric per category (`sum`, `mean`, `count`, `min`, `max`, `median`) |
| `top_n` | Top or bottom N rows by a numeric column |
| `filter` | Rows matching a condition (`eq`, `ne`, `gt`, `gte`, `lt`, `lte`, `contains`) |
| `correlation` | Strongest numeric column pairs |

It detects the file encoding and delimiter, and flags missing values, duplicate rows, outliers, constant columns, and numbers stored as text.

---

## Quick Start

```bash
pip install -r requirements.txt
python agent_tools.py
```

The demo creates a `data/` folder with a sample CSV and SQLite database, runs every tool, shows the error cases, and runs a tool chain.

### Usage

```python
from agent_tools import call_tool, run_chain, openai_tools, anthropic_tools

# Single call
call_tool("calculator", {"expression": "12.5/100*2400"})

# CSV Analyzer
call_tool("csv_analyzer", {"path": "orders.csv"})
call_tool("csv_analyzer", {"path": "orders.csv", "action": "group_by",
                           "by": "category", "metric": "amount", "agg": "sum"})

# Tool schemas for an LLM API
tools = anthropic_tools()   # or openai_tools()
```

### Tool Chaining

```python
chain = run_chain([
    ("database_tool", {"action": "query", "sql": "SELECT region, SUM(amount) AS total FROM sales GROUP BY region ORDER BY total DESC"}),
    ("calculator",    lambda ctx: {"expression": "..."}),   # uses the previous result
    ("email_tool",    lambda ctx: {"to": "manager@example.com", "subject": "Report", "body": "..."}),
])
```

### Notebook

Open `csv_analyzer_tool.ipynb` in Jupyter, VS Code, or Colab and click **Run All**. To use your own file, add a cell at the end:

```python
show("profile", csv_analyzer(path="your_file.csv"))
```

---

## Function Calling Decision Matrix (sample)

| User request | Tool | Why |
|---|---|---|
| "What is 18% GST on 24,500?" | `calculator` | Exact arithmetic, no mental-math errors |
| "What's the latest Python release?" | `web_search` | Needs current external data |
| "Show total sales per region." | `database_tool` | Data is in the company database |
| "Will it rain in Nagpur today?" | `weather_tool` | Real-time structured weather data |
| "What date is 10 days from today?" | `date_tool` | Reliable calendar math |
| "Which columns in sales.csv have missing values?" | `csv_analyzer` | Exact profiling with pandas |
| "Find the top region and its % share." | `database_tool` → `calculator` | Chain: query first, then exact percentage |
| "Explain what overfitting is." | No tool | General knowledge, a tool call only adds cost |

The full matrix has 13 requests, including 2 chained requests and 1 "no tool needed" case.

---

## Configuration (optional)

| Variable | Used for |
|---|---|
| `TAVILY_API_KEY` | Real web search results |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD` | Sending real emails |
| `TOOL_FILES_DIR` | Data directory for file tools (default `./data`) |

---

## Status

- [x] All 8 required tools built and tested with a local demo run.
- [x] Function calling schemas, dispatcher, and tool chaining working end to end.
- [x] Error handling verified with deliberate failure cases (bad SQL, path traversal, division by zero, missing or empty files, wrong columns).
- [x] Decision matrix (13 requests) and documentation completed.
- [x] CSV Analyzer built as a Python module and a Jupyter Notebook.
- [x] Live testing of Weather, Web Search (with API key), and Email sending, which are coded but not yet tested with internet and credentials.
