import os

from dotenv import load_dotenv

load_dotenv()  # reads .env if present; real environment variables take priority

# Backend: "ollama" | "hf_local" | "openai_compat" (LM Studio / llama.cpp server) | "hf_api" | "anthropic"
BACKEND = os.getenv("RA_BACKEND", "ollama")

MODEL = os.getenv("RA_MODEL", "claude-sonnet-5-5")                  # anthropic
HF_MODEL = os.getenv("RA_HF_MODEL", "Qwen/Qwen2.5-3B-Instruct")     # hf_api / hf_local

# Ollama (free, local, handles quantization + GPU automatically)
OLLAMA_MODEL = os.getenv("RA_OLLAMA_MODEL", "qwen2.5:3b")
OLLAMA_HOST = os.getenv("RA_OLLAMA_HOST", "http://localhost:11434")
OLLAMA_NUM_CTX = int(os.getenv("RA_OLLAMA_CTX", "8192"))

# OpenAI-compatible local server (LM Studio default port 1234; llama.cpp server 8080)
OPENAI_BASE = os.getenv("RA_OPENAI_BASE", "http://localhost:1234/v1")
OPENAI_MODEL = os.getenv("RA_OPENAI_MODEL", "local-model")

# Sources: "web" | "local" (your own docs, fully offline) | "both"
SOURCE_MODE = os.getenv("RA_SOURCE", "local")
DOCS_DIR = os.getenv("RA_DOCS_DIR", "docs")
EMBED_MODEL = os.getenv("RA_EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
CHUNK_CHARS = 900
CHUNK_OVERLAP = 120

MAX_ANALYSIS_ITERS = 3   # Critic -> Research/Analyzer loops
MAX_WRITER_ITERS = 2     # Writer <-> Critic loops
PASS_SCORE = 8           # Critic approval threshold (0-10)

RESULTS_PER_QUERY = 5
FETCH_TOP_N = 2          # pages fetched in full per query
MAX_SOURCES_IN_PROMPT = int(os.getenv("RA_MAX_SOURCES", "24"))
SOURCE_CHARS_IN_PROMPT = int(os.getenv("RA_SOURCE_CHARS", "1200"))

# hf_local settings (6GB GPU friendly)
HF_4BIT = os.getenv("RA_HF_4BIT", "1") == "1"
HF_MAX_NEW_TOKENS = int(os.getenv("RA_HF_MAX_NEW", "2048"))

OUTPUT_DIR = os.getenv("RA_OUTPUT_DIR", "output")
