"""Search and document retrieval tools for local files and optional web search."""

from dataclasses import dataclass
import logging
import os
import re
from typing import Dict, List, Optional

import httpx

from config import (
    CHUNK_CHARS,
    CHUNK_OVERLAP,
    DOCS_DIR,
    EMBED_MODEL,
    SOURCE_MODE,
)

logger = logging.getLogger(__name__)


@dataclass
class LocalIndex:
    chunks: List[Dict[str, str]]
    embeddings: object
    model: object


_local_index: Optional[LocalIndex] = None


def _get_ddgs_class():
    try:
        from ddgs import DDGS

        return DDGS
    except ImportError:
        from duckduckgo_search import DDGS

        return DDGS


def web_search(query: str, n: int = 5) -> List[Dict[str, str]]:
    """Search DuckDuckGo for query results."""
    try:
        ddgs_cls = _get_ddgs_class()
        with ddgs_cls() as client:
            results = list(client.text(query, max_results=n))
    except Exception as exc:
        logger.warning("Web search failed for query '%s': %s", query, exc)
        return []

    return [
        {
            "title": item.get("title", ""),
            "url": item.get("href", ""),
            "snippet": item.get("body", ""),
        }
        for item in results
        if item.get("href")
    ]


def fetch_text(url: str, limit: int = 3000) -> str:
    """Fetch and strip HTML text from a URL up to `limit` characters."""
    try:
        response = httpx.get(
            url,
            timeout=10,
            follow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0 (ResearchAssistant)"},
        )
        response.raise_for_status()
        if "text/html" not in response.headers.get("content-type", ""):
            return ""
        html = response.text
    except Exception as exc:
        logger.warning("Failed to fetch URL '%s': %s", url, exc)
        return ""

    cleaned_html = re.sub(r"(?is)<(script|style|nav|footer|header)[^>]*>.*?</\1>", " ", html)
    plain_text = re.sub(r"<[^>]+>", " ", cleaned_html)
    return re.sub(r"\s+", " ", plain_text).strip()[:limit]


def _read_file(path: str) -> str:
    ext = path.lower().rsplit(".", 1)[-1]
    try:
        if ext in ("txt", "md"):
            with open(path, encoding="utf-8", errors="ignore") as handle:
                return handle.read()
        if ext == "pdf":
            from pypdf import PdfReader

            return " ".join((page.extract_text() or "") for page in PdfReader(path).pages)
    except Exception as exc:
        logger.warning("Failed to read local document '%s': %s", path, exc)
        return ""
    return ""


def _load_chunks() -> List[Dict[str, str]]:
    chunks: List[Dict[str, str]] = []
    step = max(1, CHUNK_CHARS - CHUNK_OVERLAP)
    for root, _, files in os.walk(DOCS_DIR):
        for filename in sorted(files):
            if filename.startswith("_"):
                continue
            filepath = os.path.join(root, filename)
            normalized_text = re.sub(r"\s+", " ", _read_file(filepath)).strip()
            for chunk_idx, start_idx in enumerate(range(0, len(normalized_text), step)):
                piece = normalized_text[start_idx : start_idx + CHUNK_CHARS].strip()
                if piece:
                    chunks.append(
                        {
                            "title": filename,
                            "url": f"{filepath}#chunk{chunk_idx}",
                            "text": piece,
                        }
                    )
    return chunks


def _get_or_build_index() -> LocalIndex:
    global _local_index
    if _local_index is None:
        from sentence_transformers import SentenceTransformer

        chunks = _load_chunks()
        if not chunks:
            logger.warning("No .txt/.md/.pdf files found in '%s/'", DOCS_DIR)
        model = SentenceTransformer(EMBED_MODEL)
        embeddings = (
            model.encode([chunk["text"] for chunk in chunks], normalize_embeddings=True)
            if chunks
            else None
        )
        _local_index = LocalIndex(chunks=chunks, embeddings=embeddings, model=model)
    return _local_index


def local_search(query: str, n: int = 5) -> List[Dict[str, str]]:
    """Retrieve top-n matching document chunks using dense cosine similarity."""
    index = _get_or_build_index()
    if not index.chunks or index.embeddings is None:
        return []
    query_vec = index.model.encode([query], normalize_embeddings=True)[0]
    top_indices = (index.embeddings @ query_vec).argsort()[::-1][:n]
    return [
        {
            "title": index.chunks[idx]["title"],
            "url": index.chunks[idx]["url"],
            "snippet": index.chunks[idx]["text"][:300],
            "text": index.chunks[idx]["text"],
        }
        for idx in top_indices
    ]


def search(query: str, n: int = 5) -> List[Dict[str, str]]:
    """Dispatch query to local and/or web search based on SOURCE_MODE."""
    results: List[Dict[str, str]] = []
    if SOURCE_MODE in ("local", "both"):
        results.extend(local_search(query, n))
    if SOURCE_MODE in ("web", "both"):
        results.extend(web_search(query, n))
    return results
