
import numpy as np

from research import tools


# ---------- _read_file / _load_chunks ----------

def test_read_file_txt_md_and_unknown(tmp_path):
    (tmp_path / "a.txt").write_text("hello", encoding="utf-8")
    (tmp_path / "b.md").write_text("# title", encoding="utf-8")
    (tmp_path / "c.bin").write_bytes(b"\x00\x01")
    assert tools._read_file(str(tmp_path / "a.txt")) == "hello"
    assert tools._read_file(str(tmp_path / "b.md")) == "# title"
    assert tools._read_file(str(tmp_path / "c.bin")) == ""


def test_read_file_missing_returns_empty(tmp_path):
    assert tools._read_file(str(tmp_path / "missing.txt")) == ""


def test_load_chunks_splits_with_overlap_and_skips_underscore_files(tmp_path, monkeypatch):
    monkeypatch.setattr(tools, "DOCS_DIR", str(tmp_path))
    (tmp_path / "a.txt").write_text("x" * 2000, encoding="utf-8")
    (tmp_path / "_ignored.txt").write_text("should not load", encoding="utf-8")
    (tmp_path / "c.bin").write_bytes(b"binary")
    chunks = tools._load_chunks()
    step = tools.CHUNK_CHARS - tools.CHUNK_OVERLAP
    expected = len(range(0, 2000, step))
    assert len(chunks) == expected
    assert {c["title"] for c in chunks} == {"a.txt"}
    assert chunks[0]["url"].endswith("a.txt#chunk0")
    assert all(len(c["text"]) <= tools.CHUNK_CHARS for c in chunks)


def test_load_chunks_empty_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(tools, "DOCS_DIR", str(tmp_path))
    assert tools._load_chunks() == []


# ---------- local_search with a fake embedding index ----------

class FakeModel:
    def encode(self, texts, normalize_embeddings=True):
        return np.array([[0.0, 1.0]])


def test_local_search_ranks_by_similarity(monkeypatch):
    chunks = [
        {"title": "zero", "url": "u0", "text": "t0"},
        {"title": "one", "url": "u1", "text": "t1"},
        {"title": "mix", "url": "u2", "text": "t2"},
    ]
    emb = np.array([[1.0, 0.0], [0.0, 1.0], [0.7, 0.7]])
    monkeypatch.setattr(tools, "_index", (chunks, emb, FakeModel()))
    res = tools.local_search("query", n=2)
    assert [r["title"] for r in res] == ["one", "mix"]
    assert res[0]["text"] == "t1" and res[0]["url"] == "u1"


def test_local_search_empty_index(monkeypatch):
    monkeypatch.setattr(tools, "_index", ([], None, None))
    assert tools.local_search("anything") == []


# ---------- dispatcher ----------

def test_search_dispatch_by_source_mode(monkeypatch):
    monkeypatch.setattr(tools, "local_search", lambda q, n: [{"src": "local"}])
    monkeypatch.setattr(tools, "web_search", lambda q, n: [{"src": "web"}])

    monkeypatch.setattr(tools, "SOURCE_MODE", "local")
    assert tools.search("q") == [{"src": "local"}]
    monkeypatch.setattr(tools, "SOURCE_MODE", "web")
    assert tools.search("q") == [{"src": "web"}]
    monkeypatch.setattr(tools, "SOURCE_MODE", "both")
    assert tools.search("q") == [{"src": "local"}, {"src": "web"}]


# ---------- fetch_text ----------

class FakeHttpResponse:
    def __init__(self, text, content_type="text/html; charset=utf-8"):
        self.text = text
        self.headers = {"content-type": content_type}

    def raise_for_status(self):
        pass


def test_fetch_text_strips_html_and_scripts(monkeypatch):
    html = "<html><script>var x=1;</script><body><p>Hello   world</p></body></html>"
    monkeypatch.setattr(tools.httpx, "get", lambda url, **k: FakeHttpResponse(html))
    assert tools.fetch_text("https://x.test") == "Hello world"


def test_fetch_text_respects_limit(monkeypatch):
    monkeypatch.setattr(tools.httpx, "get", lambda url, **k: FakeHttpResponse("<p>abcdefghij</p>"))
    assert tools.fetch_text("https://x.test", limit=4) == "abcd"


def test_fetch_text_non_html_returns_empty(monkeypatch):
    monkeypatch.setattr(
        tools.httpx, "get", lambda url, **k: FakeHttpResponse("%PDF", content_type="application/pdf")
    )
    assert tools.fetch_text("https://x.test/file.pdf") == ""


def test_fetch_text_network_error_returns_empty(monkeypatch):
    def boom(url, **k):
        raise OSError("network down")

    monkeypatch.setattr(tools.httpx, "get", boom)
    assert tools.fetch_text("https://x.test") == ""
