import os
import re
from typing import Dict, List

import httpx

from config import (
    CHUNK_CHARS,
    CHUNK_OVERLAP,
    DOCS_DIR,
    EMBED_MODEL,
    SOURCE_MODE,
)


# ---------- web (optional; needs internet) ----------

def web_search(query: str, n: int = 5) -> List[Dict[str, str]]:
    try:
        from ddgs import DDGS
    except ImportError:
        from duckduckgo_search import DDGS
    try:
        with DDGS() as d:
            res = list(d.text(query, max_results=n))
    except Exception:
        return []
    return [
        {"title": r.get("title", ""), "url": r.get("href", ""), "snippet": r.get("body", "")}
        for r in res
        if r.get("href")
    ]


def fetch_text(url: str, limit: int = 3000) -> str:
    try:
        r = httpx.get(
            url,
            timeout=10,
            follow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0 (ResearchAssistant)"},
        )
        r.raise_for_status()
        if "text/html" not in r.headers.get("content-type", ""):
            return ""
        html = r.text
    except Exception:
        return ""
    html = re.sub(r"(?is)<(script|style|nav|footer|header)[^>]*>.*?</\1>", " ", html)
    text = re.sub(r"<[^>]+>", " ", html)
    return re.sub(r"\s+", " ", text).strip()[:limit]


# ---------- local docs (fully offline) ----------

_index = None  # (chunks, embeddings, model)


def _read_file(path: str) -> str:
    ext = path.lower().rsplit(".", 1)[-1]
    try:
        if ext in ("txt", "md"):
            return open(path, encoding="utf-8", errors="ignore").read()
        if ext == "pdf":
            from pypdf import PdfReader
            return " ".join((p.extract_text() or "") for p in PdfReader(path).pages)
    except Exception:
        return ""
    return ""


def _load_chunks():
    chunks = []
    step = CHUNK_CHARS - CHUNK_OVERLAP
    for root, _, files in os.walk(DOCS_DIR):
        for f in sorted(files):
            if f.startswith("_"):
                continue
            path = os.path.join(root, f)
            text = re.sub(r"\s+", " ", _read_file(path)).strip()
            for k, i in enumerate(range(0, len(text), step)):
                piece = text[i : i + CHUNK_CHARS].strip()
                if piece:
                    chunks.append({"title": f, "url": f"{path}#chunk{k}", "text": piece})
    return chunks


def local_search(query: str, n: int = 5) -> List[Dict[str, str]]:
    global _index
    if _index is None:
        from sentence_transformers import SentenceTransformer

        chunks = _load_chunks()
        if not chunks:
            print(f"[tools] WARNING: no .txt/.md/.pdf files found in '{DOCS_DIR}/'")
        model = SentenceTransformer(EMBED_MODEL)
        emb = (
            model.encode([c["text"] for c in chunks], normalize_embeddings=True)
            if chunks
            else None
        )
        _index = (chunks, emb, model)
    chunks, emb, model = _index
    if not chunks:
        return []
    q = model.encode([query], normalize_embeddings=True)[0]
    top = (emb @ q).argsort()[::-1][:n]
    return [
        {
            "title": chunks[i]["title"],
            "url": chunks[i]["url"],
            "snippet": chunks[i]["text"][:300],
            "text": chunks[i]["text"],
        }
        for i in top
    ]


# ---------- dispatcher ----------

def search(query: str, n: int = 5) -> List[Dict[str, str]]:
    res = []
    if SOURCE_MODE in ("local", "both"):
        res += local_search(query, n)
    if SOURCE_MODE in ("web", "both"):
        res += web_search(query, n)
    return res
