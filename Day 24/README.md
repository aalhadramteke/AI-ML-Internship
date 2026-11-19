# Async API Practice + Multi-Agent Research Assistant

A production-ready FastAPI application demonstrating high-concurrency asynchronous I/O patterns (`v1` synchronous vs. `v2` asynchronous endpoints) alongside a LangGraph-powered Multi-Agent Research Assistant supporting local document retrieval and multiple LLM backends.

---

## Tech Stack

- **API Framework:** Python 3.11, FastAPI, Uvicorn
- **Multi-Agent Orchestration:** LangGraph, Sentence-Transformers (`all-MiniLM-L6-v2`)
- **LLM Backends:** Ollama (default), OpenAI-compatible endpoints, Anthropic, Hugging Face (local & API)
- **Containerization:** Docker & Docker Compose
- **Testing & Benchmarking:** Pytest, `pytest-cov`, HTTPX

---

## Project Structure

```text
Day 24/
├── app/                        # FastAPI application package
│   ├── main.py                 # App entrypoint, lifespan, health check, router registration
│   ├── settings.py             # Environment configuration & startup validation
│   ├── security.py             # API key authentication & CORS configuration
│   ├── logging_config.py       # Rotating file & structured console logging
│   ├── middleware.py           # Request ID injection & response timing headers
│   ├── schemas.py              # Pydantic request/response models
│   ├── deps.py                 # Dependency injection & concurrency semaphores
│   └── routers/
│       ├── v1.py               # Synchronous baseline endpoints (/api/v1/...)
│       ├── v2.py               # Asynchronous optimized endpoints (/api/v2/...)
│       └── research.py         # Multi-agent research endpoint (/api/v2/research)
├── research/                   # Multi-agent research engine
│   ├── cli.py                  # CLI runner invoked by main.py
│   ├── graph.py                # LangGraph workflow definition
│   ├── agents.py               # Planner, researcher, and synthesizer agents
│   ├── tools.py                # Local document & web search retrieval tools
│   ├── storage.py              # Report persistence and output formatting
│   ├── state.py                # Typed graph state definitions
│   ├── llm.py                  # Multi-provider LLM client wrapper
│   └── config.py               # Research pipeline configuration
├── tests/
│   ├── unit/                   # Unit tests for config, security, and research modules
│   └── api/                    # API integration tests for health, v1/v2, and auth
├── main.py                     # CLI entry point
├── benchmark.py                # Concurrency benchmark comparing v1 sync vs. v2 async
├── Dockerfile                  # Non-root production container definition
├── docker-compose.yml          # Service orchestration, volumes, and host Ollama networking
├── DEPLOYMENT_CHECKLIST.md     # Pre-deployment verification & rollback checklist
├── PRODUCTION_READINESS_REPORT.md # Formal production readiness assessment
├── .env.example                # Documented environment variable template
└── .gitignore                  # Git exclusion rules
```

---

## Getting Started

### Prerequisites

- **Docker & Docker Compose** (recommended for deployment)
- **Python 3.11+** (for local development and test execution)
- **Ollama** running locally on port `11434` (with `qwen2.5:3b` pulled) or credentials for an external LLM backend

### 1. Configure Environment Variables

Copy `.env.example` to `.env` and update values for your environment:

```bash
cp .env.example .env
```

#### API Configuration Variables

| Variable | Description | Default / Example |
| :--- | :--- | :--- |
| `APP_ENV` | Runtime mode (`development` or `production`) | `development` |
| `LOG_LEVEL` | Logging verbosity (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`) | `INFO` |
| `LOG_DIR` | Directory where rotating application logs are written | `logs` |
| `ALLOWED_ORIGINS` | Comma-separated allowed CORS origins (empty disables CORS) | `http://localhost:3000` |
| `API_KEY` | Secret token required in `X-API-Key` header for protected endpoints | `change-to-32-char-random-key` |
| `MAX_CONCURRENT_RESEARCH` | Maximum parallel research runs allowed | `1` |
| `DB_DELAY` | Simulated database latency (seconds) for benchmark routes | `0.3` |
| `EXTERNAL_DELAY` | Simulated external API latency (seconds) for benchmark routes | `0.2` |
| `EMAIL_DELAY` | Simulated email dispatch latency (seconds) for benchmark routes | `2.0` |

#### Multi-Agent Research Assistant Variables

| Variable | Description | Default / Example |
| :--- | :--- | :--- |
| `RA_BACKEND` | LLM provider (`ollama`, `openai_compat`, `hf_local`, `hf_api`, `anthropic`) | `ollama` |
| `RA_OLLAMA_MODEL` | Ollama model identifier | `qwen2.5:3b` |
| `RA_OLLAMA_HOST` | Ollama server URL (`http://host.docker.internal:11434` inside Docker) | `http://localhost:11434` |
| `RA_OLLAMA_CTX` | Context window token limit for Ollama | `8192` |
| `RA_SOURCE` | Knowledge retrieval source (`local`, `web`, `both`) | `local` |
| `RA_DOCS_DIR` | Directory containing local reference documents | `docs` |
| `RA_OUTPUT_DIR` | Directory where generated research reports are saved | `output` |
| `RA_EMBED_MODEL` | Hugging Face sentence-transformer model for local embeddings | `sentence-transformers/all-MiniLM-L6-v2` |
| `RA_MAX_SOURCES` | Maximum number of source chunks retrieved per query | `8` |
| `RA_SOURCE_CHARS` | Maximum character length per retrieved chunk | `800` |

---

### 2. Run with Docker (Recommended)

Build and start the API service in detached mode:

```bash
docker compose up -d --build
```

Verify container health and non-root execution:

```bash
docker compose ps
curl http://localhost:8000/health
```

---

### 3. Run Locally (Without Docker)

```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate        # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start the FastAPI server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### Run the Research Assistant via CLI

```bash
python main.py "What are the best practices for async FastAPI services?"
```

---

## Testing & Benchmarking

### Run Unit and API Tests

```bash
# Run unit tests
pytest tests/unit -v

# Run API integration tests
pytest tests/api -v

# Run full test suite with coverage report
pytest --cov=app --cov=research --cov-report=term-missing
```

### Run Concurrency Benchmark (`v1` Sync vs. `v2` Async)

With the API server running on `http://127.0.0.1:8000`:

```bash
python benchmark.py
```

---

## API Reference & Error Codes

Interactive OpenAPI documentation is available when the server is running:
- **Swagger UI:** `http://localhost:8000/docs`
- **OpenAPI Schema:** `http://localhost:8000/openapi.json`

### Key Endpoints

| Method | Endpoint | Auth Required | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/health` | No | Service health check (`{"status": "ok"}`) |
| `GET` | `/api/v1/report/{id}` | No | Synchronous baseline report endpoint |
| `GET` | `/api/v2/report/{id}` | No | Asynchronous concurrent report endpoint |
| `POST` | `/api/v2/research` | Yes (`X-API-Key`) | Execute multi-agent research query with citations |

### Standard HTTP Error Codes

| Status Code | Meaning | Cause |
| :--- | :--- | :--- |
| `401` | Unauthorized | Missing or invalid `X-API-Key` header |
| `422` | Unprocessable Entity | Request payload failed Pydantic schema validation |
| `429` | Too Many Requests | Concurrent research execution limit (`MAX_CONCURRENT_RESEARCH`) reached |
| `500` | Internal Server Error | Unexpected server failure (details logged with `X-Request-ID`) |
| `503` | Service Unavailable | Upstream LLM backend (e.g., Ollama) is unreachable or offline |

---

## Logging & Observability

- **Log Location:** Logs write to `stdout` and `logs/app.log` with automatic rotation (`5 MB` per file, up to `5` backups).
- **Request Tracing:** Every request receives a unique `X-Request-ID` header and logs processing duration via `X-Process-Time-ms`.
- **Secret Hygiene:** API keys, tokens, and raw user documents are excluded from log output.
