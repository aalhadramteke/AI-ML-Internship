"""Configuration settings and environment variable overrides for the research assistant."""

import os


def _env_int(name: str, default: int) -> int:
    """Parse an integer environment variable safely, falling back to default."""
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw.strip())
    except ValueError:
        return default


# Backend: "ollama" | "hf_local" | "openai_compat" | "hf_api" | "anthropic"
BACKEND = os.getenv("RA_BACKEND", "ollama")

MODEL = os.getenv("RA_MODEL", "claude-sonnet-4-5")
HF_MODEL = os.getenv("RA_HF_MODEL", "Qwen/Qwen2.5-3B-Instruct")

# Ollama local server settings
OLLAMA_MODEL = os.getenv("RA_OLLAMA_MODEL", "qwen2.5:3b")
OLLAMA_HOST = os.getenv("RA_OLLAMA_HOST", "http://localhost:11434")
OLLAMA_NUM_CTX = _env_int("RA_OLLAMA_CTX", 8192)

# OpenAI-compatible local server settings (e.g., LM Studio, llama.cpp)
OPENAI_BASE = os.getenv("RA_OPENAI_BASE", "http://localhost:1234/v1")
OPENAI_MODEL = os.getenv("RA_OPENAI_MODEL", "local-model")

# Source retrieval settings: "web" | "local" | "both"
SOURCE_MODE = os.getenv("RA_SOURCE", "local")
DOCS_DIR = os.getenv("RA_DOCS_DIR", "docs")
EMBED_MODEL = os.getenv("RA_EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
CHUNK_CHARS = max(100, _env_int("RA_CHUNK_CHARS", 900))
CHUNK_OVERLAP = max(0, min(CHUNK_CHARS // 2, _env_int("RA_CHUNK_OVERLAP", 120)))

# Workflow iteration and quality thresholds
MAX_ANALYSIS_ITERS = 3
MAX_WRITER_ITERS = 2
PASS_SCORE = 8

RESULTS_PER_QUERY = 5
FETCH_TOP_N = 2
MAX_SOURCES_IN_PROMPT = _env_int("RA_MAX_SOURCES", 24)
SOURCE_CHARS_IN_PROMPT = _env_int("RA_SOURCE_CHARS", 1200)

# Hugging Face local inference settings
HF_4BIT = os.getenv("RA_HF_4BIT", "1") == "1"
HF_MAX_NEW_TOKENS = _env_int("RA_HF_MAX_NEW", 2048)

OUTPUT_DIR = "output"
