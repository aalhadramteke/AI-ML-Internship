"""Multi-Agent Research Assistant - Streamlit dashboard.

A single-page workspace for the local LangGraph research workflow.
Run with:  streamlit run app.py
"""

from __future__ import annotations

import html
import os
import re
import sys
from datetime import datetime

import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import agents as agents_module
import config as config_module
import llm as llm_module
import tools as tools_module
from config import (
    BACKEND,
    DOCS_DIR,
    FETCH_TOP_N,
    HF_4BIT,
    HF_MODEL,
    MAX_ANALYSIS_ITERS,
    MAX_SOURCES_IN_PROMPT,
    MAX_WRITER_ITERS,
    MODEL,
    OLLAMA_MODEL,
    OPENAI_MODEL,
    PASS_SCORE,
    RESULTS_PER_QUERY,
    SOURCE_CHARS_IN_PROMPT,
    SOURCE_MODE,
)
from graph import build_graph

# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Research Workspace",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
.block-container { max-width: 1080px; padding: 2rem 2rem 3rem 2rem; }
header[data-testid="stHeader"] { display: none; }
#MainMenu, footer { visibility: hidden; }

[data-testid="stMarkdownContainer"] h1 { font-size: 1.55rem !important; font-weight: 600 !important; letter-spacing: -0.02em; margin-bottom: 0.1rem; }
[data-testid="stMarkdownContainer"] h2 { font-size: 1.1rem !important; font-weight: 600 !important; margin-top: 1.3rem; }
[data-testid="stMarkdownContainer"] h3 { font-size: 1rem !important; font-weight: 600 !important; margin-top: 1.1rem; }
h4 { font-size: 1.02rem; font-weight: 600; }
p, li { color: #374151; }

.stButton > button[kind="primary"],
.stButton > button[data-testid="stBaseButton-primary"] {
    color: #FFFFFF !important;
}

section[data-testid="stSidebar"] {
    background: #FAFAFA;
    border-right: 1px solid #EAECEF;
}
section[data-testid="stSidebar"] .block-container { padding: 1.4rem 1.1rem; }

div[data-testid="stMetric"] {
    background: #FFFFFF;
    border: 1px solid #E5E7EB;
    border-radius: 8px;
    padding: 0.6rem 0.8rem;
}
div[data-testid="stMetricLabel"] p { font-size: 0.78rem; color: #6B7280; }
div[data-testid="stMetricValue"] { font-size: 1.3rem; }

.status {
    display: inline-block;
    font-size: 0.78rem;
    font-weight: 600;
    padding: 0.12rem 0.5rem;
    border-radius: 5px;
    border: 1px solid transparent;
    vertical-align: middle;
}
.status-ok { color: #047857; background: #ECFDF5; border-color: #A7F3D0; }
.status-warn { color: #B45309; background: #FFFBEB; border-color: #FDE68A; }
.status-err { color: #B91C1C; background: #FEF2F2; border-color: #FECACA; }

.finding {
    border-left: 2px solid #D1D5DB;
    padding: 0.1rem 0 0.1rem 0.85rem;
    margin-bottom: 1rem;
}
.finding-claim { font-size: 0.92rem; line-height: 1.6; color: #111827; }
.finding-meta { font-size: 0.78rem; color: #6B7280; margin-top: 0.25rem; }
.chip {
    display: inline-block;
    font-size: 0.72rem;
    padding: 0.05rem 0.4rem;
    border-radius: 4px;
    background: #F3F4F6;
    color: #4B5563;
    margin-right: 0.3rem;
}

.source-row { border-top: 1px solid #E5E7EB; padding: 0.7rem 0; }
.source-row:first-child { border-top: 0; }
.source-title { font-size: 0.9rem; font-weight: 600; color: #111827; }
.source-url { font-size: 0.78rem; color: #6B7280; word-break: break-all; }
.source-url a { color: #2563EB; text-decoration: none; }
.source-url a:hover { text-decoration: underline; }

.log-line {
    font-family: ui-monospace, SFMono-Regular, Consolas, monospace;
    font-size: 0.78rem;
    line-height: 1.5;
    color: #4B5563;
    border-left: 2px solid #E5E7EB;
    padding: 0.15rem 0 0.15rem 0.6rem;
    margin-bottom: 0.2rem;
    word-break: break-word;
}

.empty {
    border: 1px dashed #D1D5DB;
    border-radius: 8px;
    padding: 2.2rem 1.2rem;
    text-align: center;
    color: #6B7280;
    font-size: 0.88rem;
}
.empty strong { display: block; color: #111827; font-size: 0.95rem; margin-bottom: 0.3rem; }
</style>
""",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------
BACKENDS = ["ollama", "openai_compat", "hf_local", "hf_api", "anthropic"]
BACKEND_LABELS = {
    "ollama": "Ollama (local)",
    "openai_compat": "OpenAI-compatible (local)",
    "hf_local": "Transformers (local)",
    "hf_api": "Hugging Face Inference API",
    "anthropic": "Anthropic API",
}
SOURCE_MODES = ["local", "web", "both"]
SOURCE_LABELS = {"local": "Local documents", "web": "Web search", "both": "Local and web"}

STAGES = ["coordinator_plan", "research", "analyzer", "critic_findings", "writer", "critic_draft", "finalize"]


def default_model(backend: str) -> str:
    if backend == "ollama":
        return OLLAMA_MODEL or "qwen2.5:3b"
    if backend == "openai_compat":
        return OPENAI_MODEL or "local-model"
    if backend in ("hf_local", "hf_api"):
        return HF_MODEL or "Qwen/Qwen2.5-3B-Instruct"
    return MODEL or "claude-sonnet-4-5"


if "settings" not in st.session_state:
    st.session_state.settings = {
        "backend": BACKEND if BACKEND in BACKENDS else "ollama",
        "source_mode": SOURCE_MODE if SOURCE_MODE in SOURCE_MODES else "local",
        "docs_dir": DOCS_DIR or "docs",
        "max_analysis": MAX_ANALYSIS_ITERS,
        "max_writer": MAX_WRITER_ITERS,
        "pass_score": PASS_SCORE,
    }
if "run_count" not in st.session_state:
    st.session_state.run_count = 0
if "results" not in st.session_state:
    st.session_state.results = None


def apply_settings(settings: dict) -> None:
    """Push dashboard settings into the modules that read them at call time."""
    overrides = {
        "BACKEND": settings["backend"],
        "SOURCE_MODE": settings["source_mode"],
        "DOCS_DIR": settings["docs_dir"],
        "MAX_ANALYSIS_ITERS": settings["max_analysis"],
        "MAX_WRITER_ITERS": settings["max_writer"],
        "PASS_SCORE": settings["pass_score"],
        "RESULTS_PER_QUERY": RESULTS_PER_QUERY,
        "FETCH_TOP_N": FETCH_TOP_N,
        "MAX_SOURCES_IN_PROMPT": MAX_SOURCES_IN_PROMPT,
        "SOURCE_CHARS_IN_PROMPT": SOURCE_CHARS_IN_PROMPT,
    }
    backend = settings["backend"]
    if backend == "ollama":
        overrides["OLLAMA_MODEL"] = settings["model"]
    elif backend == "openai_compat":
        overrides["OPENAI_MODEL"] = settings["model"]
    elif backend in ("hf_local", "hf_api"):
        overrides["HF_MODEL"] = settings["model"]
    else:
        overrides["MODEL"] = settings["model"]

    if backend == "hf_local" and "sb_hf_4bit" in st.session_state:
        overrides["HF_4BIT"] = bool(st.session_state["sb_hf_4bit"])

    for module in (config_module, agents_module, llm_module, tools_module):
        for key, value in overrides.items():
            if hasattr(module, key):
                setattr(module, key, value)


# ---------------------------------------------------------------------------
# Workflow
# ---------------------------------------------------------------------------
@st.cache_resource(show_spinner=False)
def get_graph():
    return build_graph()


def run_workflow(query: str) -> dict:
    graph = get_graph()
    initial_state = {
        "query": query,
        "log": [],
        "sources": [],
        "findings": {},
        "critique": {},
        "draft": "",
        "analysis_iter": 0,
        "writer_iter": 0,
    }
    results = {
        "query": query,
        "status": "running",
        "final_report": "",
        "findings": {},
        "critique": {},
        "draft_critique": {},
        "sources": [],
        "log": [],
        "steps": [],
        "forced_caveats": [],
        "started_at": datetime.now().isoformat(timespec="seconds"),
    }

    try:
        for update in graph.stream(initial_state, {"recursion_limit": 60}):
            for node, payload in update.items():
                results["steps"].append(node)
                results["log"].extend(payload.get("log") or [])
                for key in ("findings", "critique", "draft_critique", "sources", "forced_caveats"):
                    if payload.get(key):
                        results[key] = payload[key]
                if payload.get("final_report"):
                    results["final_report"] = payload["final_report"]
        results["status"] = "complete"
    except Exception as exc:  # noqa: BLE001 - shown in the interface
        results["status"] = "error"
        results["error"] = f"{type(exc).__name__}: {exc}"
        results["log"].append(f"Workflow error: {type(exc).__name__}: {exc}")

    if results["status"] == "complete" and not results["final_report"]:
        results["final_report"] = "The workflow finished without producing a report."
    results["finished_at"] = datetime.now().isoformat(timespec="seconds")
    return results


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------
VERDICTS = {
    "approve": ("Approved", "status-ok"),
    "revise": ("Revision requested", "status-warn"),
    "re_search": ("More research needed", "status-warn"),
}


def esc(value: object) -> str:
    return html.escape(str(value if value is not None else ""))


def status_label(text: str, css_class: str) -> str:
    return f"<span class='status {css_class}'>{esc(text)}</span>"


def cited_ids(text: str) -> list[int]:
    ids = set()
    for group in re.findall(r"\[(\d+(?:\s*,\s*\d+)*)\]", text or ""):
        for part in re.split(r"\s*,\s*", group):
            try:
                ids.add(int(part))
            except ValueError:
                continue
    return sorted(ids)


def empty_state(title: str, text: str) -> None:
    st.markdown(
        f"<div class='empty'><strong>{esc(title)}</strong>{esc(text)}</div>",
        unsafe_allow_html=True,
    )


def render_findings(findings: dict) -> None:
    items = findings.get("findings") or []
    if not items:
        empty_state(
            "No findings extracted",
            "The analyzer returned no source-backed claims. Try a more specific question, "
            "add documents to the docs folder, or use a larger model.",
        )
        return

    for index, item in enumerate(items, start=1):
        claim = str(item.get("claim", "")).strip() or "No claim text."
        try:
            confidence = f"Confidence {float(item.get('confidence')):.2f}"
        except (TypeError, ValueError):
            confidence = "Confidence not reported"
        chips = "".join(
            f"<span class='chip'>Source {esc(sid)}</span>" for sid in (item.get("source_ids") or [])
        )
        st.markdown(
            f"<div class='finding'><div class='finding-claim'>{index}. {esc(claim)}</div>"
            f"<div class='finding-meta'>{esc(confidence)} {chips}</div></div>",
            unsafe_allow_html=True,
        )

    themes = findings.get("themes") or []
    contradictions = findings.get("contradictions") or []
    gaps = findings.get("gaps") or []

    if themes:
        with st.expander("Themes"):
            for theme in themes:
                st.markdown(f"- {theme}")
    if contradictions:
        with st.expander(f"Contradictions ({len(contradictions)})"):
            for entry in contradictions:
                st.markdown(f"- {entry.get('description', '')}")
                refs = entry.get("source_ids") or []
                if refs:
                    st.caption("Sources: " + ", ".join(str(ref) for ref in refs))
    if gaps:
        with st.expander(f"Research gaps ({len(gaps)})"):
            for gap in gaps:
                st.markdown(f"- {gap}")


def render_review(results: dict) -> None:
    sections = [
        ("Findings review", results.get("critique") or {}),
        ("Draft review", results.get("draft_critique") or {}),
    ]
    sections = [(name, data) for name, data in sections if data]

    if not sections:
        empty_state("No review recorded", "The critic did not return a verdict for this run.")
        return

    for name, payload in sections:
        verdict = str(payload.get("verdict", "")).lower()
        label, css_class = VERDICTS.get(verdict, (verdict.title() or "Unknown", "status-warn"))
        try:
            score = f"{float(payload.get('score')):.1f} / 10"
        except (TypeError, ValueError):
            score = "not scored"

        st.markdown(f"**{name}**")
        st.markdown(
            f"{status_label(label, css_class)} &nbsp; <span style='color:#6B7280;font-size:0.82rem;'>"
            f"Score {esc(score)}</span>",
            unsafe_allow_html=True,
        )

        for issue in payload.get("issues") or []:
            severity = str(issue.get("severity", "medium")).lower()
            sev_class = {"high": "status-err", "medium": "status-warn", "low": "status-warn"}.get(
                severity, "status-warn"
            )
            st.markdown(
                f"{status_label(severity.upper(), sev_class)} {esc(issue.get('description', ''))}",
                unsafe_allow_html=True,
            )

        for follow_up in payload.get("gap_queries") or []:
            st.markdown(f"- {follow_up}")

        st.divider()

    caveats = results.get("forced_caveats") or []
    if caveats:
        st.markdown("**Recorded limitations**")
        for caveat in caveats:
            st.markdown(f"- {caveat}")


def render_sources(results: dict) -> None:
    sources = results.get("sources") or []
    if not sources:
        empty_state(
            "No sources",
            "Nothing was retrieved for this run. Check the docs folder or enable web search.",
        )
        return

    for source in sources:
        title = source.get("title") or "Untitled source"
        url = source.get("url") or ""
        snippet = (source.get("snippet") or "").strip()
        url_html = ""
        if url:
            safe = esc(url)
            url_html = f"<div class='source-url'><a href='{safe}' target='_blank' rel='noopener'>{safe}</a></div>"
        snippet_html = f"<div class='source-url'>{esc(snippet[:220])}</div>" if snippet else ""
        st.markdown(
            f"<div class='source-row'><div class='source-title'>[{esc(source.get('id', '?'))}] "
            f"{esc(title)}</div>{url_html}{snippet_html}</div>",
            unsafe_allow_html=True,
        )


def render_activity(results: dict) -> None:
    entries = results.get("log") or []
    if not entries:
        st.caption("No log entries recorded.")
        return
    for entry in entries:
        st.markdown(f"<div class='log-line'>{esc(entry)}</div>", unsafe_allow_html=True)


def render_results(results: dict) -> None:
    status = results.get("status", "running")
    badge = {
        "complete": status_label("Complete", "status-ok"),
        "error": status_label("Failed", "status-err"),
    }.get(status, status_label("Running", "status-warn"))

    st.markdown(f"#### {results.get('query', '')}")
    st.markdown(
        f"{badge} &nbsp; <span style='color:#6B7280;font-size:0.8rem;'>"
        f"Started {esc(results.get('started_at', '-'))} &middot; finished "
        f"{esc(results.get('finished_at', '-'))}</span>",
        unsafe_allow_html=True,
    )

    if status == "error":
        st.error(results.get("error", "The workflow failed."))

    sources = results.get("sources") or []
    findings = results.get("findings") or {}
    critique = results.get("critique") or {}

    columns = st.columns(3)
    columns[0].metric("Sources", len(sources))
    columns[1].metric("Findings", len(findings.get("findings") or []))
    try:
        score = f"{float(critique.get('score')):.1f}"
    except (TypeError, ValueError):
        score = "-"
    columns[2].metric("Critic score", score)

    completed = sum(1 for stage in STAGES if stage in (results.get("steps") or []))
    st.caption(f"Stages completed: {completed} of {len(STAGES)}")

    report_tab, findings_tab, review_tab, sources_tab, activity_tab = st.tabs(
        ["Report", "Findings", "Review", "Sources", "Activity"]
    )

    with report_tab:
        report = results.get("final_report") or ""
        body = report
        if body:
            first_line, _, remainder = body.partition("\n")
            if first_line.strip().lstrip("#").strip().lower() == str(results.get("query", "")).strip().lower():
                body = remainder.lstrip("\n")
        if body:
            st.markdown(body)
        else:
            st.caption("No report was produced.")

        by_id = {src.get("id"): src for src in sources}
        matched = [by_id[cid] for cid in cited_ids(report) if cid in by_id]
        if matched:
            with st.expander(f"References ({len(matched)})"):
                for source in matched:
                    st.markdown(f"**[{source.get('id')}]** {source.get('title') or 'Untitled'}")
                    if source.get("url"):
                        st.caption(source["url"])

        action_left, action_right = st.columns([2, 1])
        with action_left:
            if report:
                st.download_button(
                    "Download report (.md)",
                    data=report,
                    file_name=f"research_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
                    mime="text/markdown",
                    width="stretch",
                )
        with action_right:
            if st.button("Clear results", key="clear_results", width="stretch"):
                st.session_state.results = None
                st.rerun()

    with findings_tab:
        render_findings(findings)

    with review_tab:
        render_review(results)

    with sources_tab:
        render_sources(results)

    with activity_tab:
        render_activity(results)


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
settings = st.session_state.settings

with st.sidebar:
    st.markdown("### Research Workspace")
    st.caption("Local multi-agent research")
    st.divider()

    st.markdown("**Model**")
    backend = st.selectbox(
        "Backend",
        BACKENDS,
        index=BACKENDS.index(settings["backend"]),
        format_func=lambda name: BACKEND_LABELS.get(name, name),
        key="sb_backend",
    )
    model_value = st.text_input(
        "Model name",
        value=st.session_state.get(f"sb_model_{backend}", default_model(backend)),
        key=f"sb_model_{backend}",
    )

    if backend == "ollama":
        st.caption("Ollama must be running locally.")
    elif backend == "openai_compat":
        st.caption("Point at a local OpenAI-compatible server.")
    elif backend == "hf_local":
        st.caption("Weights download on first use.")
        st.checkbox("4-bit quantization", value=HF_4BIT, key="sb_hf_4bit")
    elif backend == "hf_api":
        st.caption("Requires HF_TOKEN.")
    else:
        st.caption("Requires ANTHROPIC_API_KEY.")

    st.divider()
    st.markdown("**Sources**")
    source_mode = st.selectbox(
        "Source mode",
        SOURCE_MODES,
        index=SOURCE_MODES.index(settings["source_mode"]),
        format_func=lambda name: SOURCE_LABELS[name],
        key="sb_source_mode",
    )
    docs_dir = st.text_input("Documents folder", value=settings["docs_dir"], key="sb_docs_dir")

    st.divider()
    st.markdown("**Quality controls**")
    max_analysis = st.slider("Analysis passes", 1, 6, int(settings["max_analysis"]), key="sb_max_analysis")
    max_writer = st.slider("Writing passes", 1, 4, int(settings["max_writer"]), key="sb_max_writer")
    pass_score = st.slider("Approval threshold", 1, 10, int(settings["pass_score"]), key="sb_pass_score")

    st.divider()
    runs_col, sources_col = st.columns(2)
    runs_col.metric("Runs", st.session_state.run_count)
    sources_col.metric("Sources", len((st.session_state.results or {}).get("sources") or []))

    st.caption("Runs locally. No external service is used unless you choose a hosted backend or web search.")

settings.update(
    {
        "backend": backend,
        "model": (model_value or "").strip() or default_model(backend),
        "source_mode": source_mode,
        "docs_dir": (docs_dir or "").strip() or "docs",
        "max_analysis": max_analysis,
        "max_writer": max_writer,
        "pass_score": pass_score,
    }
)
apply_settings(settings)

# ---------------------------------------------------------------------------
# Page content
# ---------------------------------------------------------------------------
st.title("Multi-Agent Research Assistant")
st.caption(
    "Ask a question and the agents plan, gather sources, analyse, critique, and write a cited report."
)

with st.container(border=True):
    query = st.text_area(
        "Research question",
        key="query_text",
        height=96,
        placeholder="e.g. What are the trade-offs of local versus cloud LLM inference?",
    )

    run_col, note_col = st.columns([1, 3])
    with run_col:
        run_clicked = st.button("Run research", type="primary", width="stretch")
    with note_col:
        st.caption("Completed runs are saved to the output folder.")

EXAMPLES = [
    ("AI code assistants", "What are the benefits of AI code assistants?"),
    ("Quantum computing", "How does quantum computing work?"),
    ("Fall of Rome", "What caused the fall of the Roman Empire?"),
    ("Python vs Rust", "Compare Python and Rust for systems programming"),
    ("Renewable energy", "What are the trends in renewable energy adoption?"),
]


def use_example(text: str) -> None:
    st.session_state.query_text = text


st.caption("Examples")
example_columns = st.columns(len(EXAMPLES))
for index, (label, prompt) in enumerate(EXAMPLES):
    example_columns[index].button(
        label,
        key=f"example_{index}",
        on_click=use_example,
        args=(prompt,),
        width="stretch",
    )

if run_clicked:
    question = (query or "").strip()
    if not question:
        st.warning("Enter a research question before running.")
    else:
        st.session_state.run_count += 1
        with st.spinner("Running the research workflow. Local models can take a few minutes."):
            st.session_state.results = run_workflow(question)
        st.rerun()

st.divider()

results = st.session_state.results
if results:
    render_results(results)
else:
    empty_state(
        "No results yet",
        "Enter a question above and start a run. Findings, review, sources, and the report appear here.",
    )
