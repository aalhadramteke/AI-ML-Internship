import json
import re

from config import (
    DOCS_DIR,
    FETCH_TOP_N,
    MAX_ANALYSIS_ITERS,
    MAX_SOURCES_IN_PROMPT,
    MAX_WRITER_ITERS,
    PASS_SCORE,
    RESULTS_PER_QUERY,
    SOURCE_CHARS_IN_PROMPT,
    SOURCE_MODE,
)
from llm import chat, chat_json
from state import State
from storage import save_run
from tools import fetch_text, search


# ---------- helpers (defensive: small models often break the JSON schema) ----------

def _sources_for_prompt(sources):
    out = []
    for s in sources[:MAX_SOURCES_IN_PROMPT]:
        body = (s.get("text") or s.get("snippet") or "")[:SOURCE_CHARS_IN_PROMPT]
        out.append({"id": s["id"], "title": s["title"], "url": s["url"], "content": body})
    return out


def _cited_ids(text: str):
    ids = set()
    for grp in re.findall(r"\[(\d+(?:\s*,\s*\d+)*)\]", text):
        ids.update(int(x) for x in re.split(r"\s*,\s*", grp))
    return ids


def _as_int(x):
    try:
        if isinstance(x, bool):
            return None
        if isinstance(x, int):
            return x
        return int(float(str(x).strip().strip("[]# ")))
    except (ValueError, TypeError):
        return None


def _str_list(x):
    if isinstance(x, str):
        return [x.strip()] if x.strip() else []
    if isinstance(x, list):
        return [str(i).strip() for i in x if str(i).strip()]
    return []


def _score(x) -> float:
    try:
        return max(0.0, min(10.0, float(x)))
    except (ValueError, TypeError):
        return 0.0


def _norm_verdict(v, allowed, default):
    v = str(v).strip().lower()
    return v if v in allowed else default


def _norm_issues(items):
    if isinstance(items, (str, dict)):
        items = [items]
    if not isinstance(items, list):
        return []
    out = []
    for i in items:
        if isinstance(i, dict):
            sev = str(i.get("severity", "medium")).lower()
            if sev not in ("high", "medium", "low"):
                sev = "medium"
            out.append({"severity": sev, "description": str(i.get("description", ""))})
        elif isinstance(i, str) and i.strip():
            out.append({"severity": "medium", "description": i.strip()})
    return out


def _high_issues(critique):
    return [i for i in critique.get("issues", []) if i.get("severity") == "high"]


def _clean_findings(raw, valid_ids):
    """Force the Analyzer output into the expected schema; drop unsupported findings."""
    if isinstance(raw, list):
        raw = {"findings": raw}
    if not isinstance(raw, dict):
        raw = {}
    items = raw.get("findings")
    if not isinstance(items, list):
        items = []

    kept = []
    for f in items:
        if not isinstance(f, dict):  # e.g. a bare string
            continue
        ids = f.get("source_ids", [])
        if not isinstance(ids, list):
            ids = [ids]
        ids = sorted({i for i in (_as_int(x) for x in ids) if i in valid_ids})
        if not ids:
            continue
        try:
            conf = max(0.0, min(1.0, float(f.get("confidence", 0.5))))
        except (TypeError, ValueError):
            conf = 0.5
        kept.append(
            {
                "sub_question": str(f.get("sub_question", "")),
                "claim": str(f.get("claim", "")),
                "source_ids": ids,
                "confidence": conf,
            }
        )

    contras = []
    raw_c = raw.get("contradictions")
    for c in raw_c if isinstance(raw_c, list) else []:
        if isinstance(c, dict):
            cid = [i for i in (_as_int(x) for x in c.get("source_ids", []) or []) if i in valid_ids]
            contras.append({"description": str(c.get("description", "")), "source_ids": cid})
        elif isinstance(c, str) and c.strip():
            contras.append({"description": c.strip(), "source_ids": []})

    return {
        "findings": kept,
        "themes": _str_list(raw.get("themes")),
        "contradictions": contras,
        "gaps": _str_list(raw.get("gaps")),
    }


# ---------- 1. Coordinator: plan ----------

def coordinator_plan(state: State) -> dict:
    plan = chat_json(
        "You are the Coordinator of a research team. Decompose the research question.\n"
        'Schema: {"sub_questions": [str, 3-5 items], "scope": str, '
        '"search_queries": [str, 1-2 per sub-question, concise queries]}',
        state["query"],
    )
    if not isinstance(plan, dict):
        plan = {}
    subs = _str_list(plan.get("sub_questions"))[:6] or [state["query"]]
    queries = _str_list(plan.get("search_queries"))[:10] or subs
    return {
        "plan": {"sub_questions": subs, "scope": str(plan.get("scope", ""))},
        "search_queries": queries,
        "sources": [],
        "analysis_iter": 0,
        "writer_iter": 0,
        "forced_caveats": [],
        "log": [f"[coordinator] planned {len(subs)} sub-questions"],
    }


# ---------- 2. Research Agent ----------

def research_agent(state: State) -> dict:
    sources = list(state.get("sources", []))
    seen = {s["url"] for s in sources}
    added = 0
    for q in state.get("search_queries", []):
        results = search(q, RESULTS_PER_QUERY)
        fetched = 0
        for r in results:
            if r["url"] in seen:
                continue
            seen.add(r["url"])
            if r.get("text"):  # local doc chunk, already full text
                text = r["text"]
            elif r["url"].startswith("http") and fetched < FETCH_TOP_N:
                text = fetch_text(r["url"])
                fetched += 1
            else:
                text = ""
            sources.append(
                {
                    "id": len(sources) + 1,
                    "title": r["title"],
                    "url": r["url"],
                    "snippet": r["snippet"],
                    "text": text,
                    "query": q,
                }
            )
            added += 1
    return {
        "sources": sources,
        "search_queries": [],
        "log": [f"[research] +{added} sources (total {len(sources)})"],
    }


# ---------- 2b. Guard: stop if nothing was retrieved ----------

def route_after_research(state: State) -> str:
    return "analyzer" if state.get("sources") else "no_sources"


def abort_no_sources(state: State) -> dict:
    if SOURCE_MODE == "web":
        hint = "Check your internet connection and run: pip install -U ddgs"
    else:
        hint = (
            f"No readable .txt/.md/.pdf files were found in '{DOCS_DIR}/' "
            "(relative to the folder you run the command from). "
            "Copy your files there, or set RA_SOURCE=web / both."
        )
    msg = f"# No sources retrieved\n\nThe run was stopped so the model would not invent an answer.\n\n{hint}\n"
    run_dir = save_run(state, msg, "no_sources")
    return {
        "final_report": msg,
        "log": ["[coordinator] aborted: no sources retrieved", f"[coordinator] saved run to {run_dir}"],
    }


# ---------- 3. Analyzer ----------

_ANALYZER_SYSTEM = (
    "You are the Analyzer. Extract findings ONLY supported by the provided sources.\n"
    "Every finding must cite source ids that exist. Flag contradictions between sources.\n"
    'Schema: {"findings": [{"sub_question": str, "claim": str, "source_ids": [int], '
    '"confidence": float 0-1}], "themes": [str], '
    '"contradictions": [{"description": str, "source_ids": [int]}], "gaps": [str]}\n'
    'Example finding: {"sub_question": "...", "claim": "...", "source_ids": [1, 2], "confidence": 0.8}\n'
    "If prior critic issues are given, fix them."
)


def analyzer(state: State) -> dict:
    valid = {s["id"] for s in state["sources"]}
    payload = json.dumps(
        {
            "query": state["query"],
            "sub_questions": state["plan"]["sub_questions"],
            "prior_critic_issues": state.get("critique", {}).get("issues", []),
            "sources": _sources_for_prompt(state["sources"]),
        }
    )
    findings = _clean_findings({}, valid)
    for attempt in range(2):
        extra = (
            ""
            if attempt == 0
            else "\nIMPORTANT: every item in 'findings' MUST be an object with 'claim' and "
            "'source_ids' (a list of integer ids from the sources). Plain strings are invalid."
        )
        raw = chat_json(_ANALYZER_SYSTEM + extra, payload, max_tokens=6000)
        findings = _clean_findings(raw, valid)
        if findings["findings"]:
            break
    n = state.get("analysis_iter", 0) + 1
    return {
        "findings": findings,
        "analysis_iter": n,
        "log": [f"[analyzer] iteration {n}: {len(findings['findings'])} findings"],
    }


# ---------- 4a. Critic: findings ----------

def critic_findings(state: State) -> dict:
    prog_issues = []
    if not state["findings"].get("findings"):
        prog_issues.append(
            {"severity": "high", "description": "No findings with valid source citations were produced."}
        )

    c = chat_json(
        "You are the Critic. Evaluate the findings for accuracy vs sources, bias, "
        "source credibility, and coverage of ALL sub-questions.\n"
        'Schema: {"verdict": "approve"|"revise"|"re_search", "score": 0-10, '
        '"issues": [{"severity": "high"|"medium"|"low", "description": str}], '
        '"gap_queries": [str]}\n'
        "Use re_search only for coverage gaps or weak sources (give gap_queries); "
        "use revise for reasoning or accuracy problems.",
        json.dumps(
            {
                "sub_questions": state["plan"]["sub_questions"],
                "findings": state["findings"],
                "sources": _sources_for_prompt(state["sources"]),
            }
        ),
        max_tokens=3000,
    )
    if not isinstance(c, dict):
        c = {}
    c["verdict"] = _norm_verdict(c.get("verdict"), {"approve", "revise", "re_search"}, "revise")
    c["score"] = _score(c.get("score"))
    c["issues"] = _norm_issues(c.get("issues")) + prog_issues
    c["gap_queries"] = _str_list(c.get("gap_queries"))

    # Code-enforced gate (LLM verdict alone is not trusted)
    if c["score"] >= PASS_SCORE and not _high_issues(c):
        c["verdict"] = "approve"
    elif prog_issues and c["verdict"] == "approve":
        c["verdict"] = "revise"

    update = {
        "critique": c,
        "log": [f"[critic:findings] {c['verdict']} score={c['score']:g} issues={len(c['issues'])}"],
    }
    if c["verdict"] == "re_search":
        update["search_queries"] = c["gap_queries"]
    if c["verdict"] != "approve" and state["analysis_iter"] >= MAX_ANALYSIS_ITERS:
        update["forced_caveats"] = [i["description"] for i in c["issues"]]
        update["log"].append("[coordinator] analysis loop cap hit; proceeding with caveats")
    return update


def route_after_findings_critic(state: State) -> str:
    v = state["critique"]["verdict"]
    if v == "approve" or state["analysis_iter"] >= MAX_ANALYSIS_ITERS:
        return "writer"
    if v == "re_search" and state.get("search_queries"):
        return "research"
    return "analyzer"


# ---------- 5. Writer ----------

def writer(state: State) -> dict:
    n = state.get("writer_iter", 0) + 1
    if not state["findings"].get("findings"):
        draft = (
            "## Executive Summary\n\nNo findings supported by the retrieved sources could be "
            "extracted, so no report content is provided.\n\n## Limitations\n\n"
            "The model could not produce source-backed findings. Try rephrasing the question, "
            "adding more documents to `docs/`, or using a larger model."
        )
        return {"draft": draft, "writer_iter": n, "log": [f"[writer] draft v{n} (no findings)"]}

    feedback = state.get("draft_critique", {}).get("issues", []) if state.get("draft") else []
    draft = chat(
        "You are the Writer. Produce a structured Markdown research report.\n"
        "Sections: Executive Summary, Key Findings (grouped by sub-question), "
        "Contradictions and Uncertainties, Limitations.\n"
        "Rules: use ONLY the provided findings; cite inline as [n] using source ids; "
        "never invent a citation; do NOT write a references section (it is added automatically); "
        "state limitations honestly. If previous draft feedback is given, revise accordingly.",
        json.dumps(
            {
                "query": state["query"],
                "findings": state["findings"],
                "known_limitations": state.get("forced_caveats", []),
                "previous_draft": state.get("draft", ""),
                "critic_feedback": feedback,
                "valid_source_ids": [s["id"] for s in state["sources"]],
            }
        ),
        max_tokens=6000,
    )
    return {"draft": draft, "writer_iter": n, "log": [f"[writer] draft v{n}"]}


# ---------- 4b. Critic: draft ----------

def critic_draft(state: State) -> dict:
    if not state["findings"].get("findings"):
        c = {
            "verdict": "revise",
            "score": 0.0,
            "issues": [{"severity": "high", "description": "No source-backed findings were available."}],
        }
        return {"draft_critique": c, "log": ["[critic:draft] revise score=0 (no findings)"]}

    valid_ids = {s["id"] for s in state["sources"]}
    bad = sorted(_cited_ids(state["draft"]) - valid_ids)
    prog_issues = (
        [{"severity": "high", "description": f"Fabricated citation ids: {bad}"}] if bad else []
    )

    c = chat_json(
        "You are the Critic reviewing a draft report against the approved findings. "
        "Check faithfulness (no claims beyond findings), coverage of all sub-questions, "
        "clarity, and honest limitations.\n"
        'Schema: {"verdict": "approve"|"revise", "score": 0-10, '
        '"issues": [{"severity": "high"|"medium"|"low", "description": str}]}',
        json.dumps(
            {
                "sub_questions": state["plan"]["sub_questions"],
                "findings": state["findings"],
                "draft": state["draft"],
            }
        ),
        max_tokens=2500,
    )
    if not isinstance(c, dict):
        c = {}
    c["verdict"] = _norm_verdict(c.get("verdict"), {"approve", "revise"}, "revise")
    c["score"] = _score(c.get("score"))
    c["issues"] = _norm_issues(c.get("issues")) + prog_issues
    if c["score"] >= PASS_SCORE and not _high_issues(c):
        c["verdict"] = "approve"
    elif prog_issues:
        c["verdict"] = "revise"
    return {
        "draft_critique": c,
        "log": [f"[critic:draft] {c['verdict']} score={c['score']:g}"],
    }


def route_after_draft_critic(state: State) -> str:
    if state["draft_critique"]["verdict"] == "approve" or state["writer_iter"] >= MAX_WRITER_ITERS:
        return "finalize"
    return "writer"


# ---------- 1b. Coordinator: finalize ----------

def coordinator_finalize(state: State) -> dict:
    draft = state["draft"]
    by_id = {s["id"]: s for s in state["sources"]}
    cited = sorted(i for i in _cited_ids(draft) if i in by_id)

    # strip any fabricated citation ids that survived the loop cap
    def _clean(m):
        ids = [int(x) for x in re.split(r"\s*,\s*", m.group(1))]
        ids = [i for i in ids if i in by_id]
        return f"[{', '.join(map(str, ids))}]" if ids else ""

    draft = re.sub(r"\[(\d+(?:\s*,\s*\d+)*)\]", _clean, draft)

    refs = "\n".join(f"[{i}] {by_id[i]['title']}. {by_id[i]['url']}" for i in cited)
    report = f"# {state['query']}\n\n{draft}\n\n## References\n\n{refs}\n"

    caveats = state.get("forced_caveats", [])
    dc = state["draft_critique"]
    not_clean = bool(caveats) or dc.get("verdict") != "approve"
    if not_clean:
        report += "\n## Review Notes\n\nThe quality loop hit its iteration cap. Open issues:\n"
        issues = caveats + [i.get("description", "") for i in dc.get("issues", [])]
        report += "\n".join(f"- {x}" for x in issues if x) + "\n"

    run_dir = save_run(state, report, "ok_with_caveats" if not_clean else "ok")
    return {"final_report": report, "log": [f"[coordinator] saved run to {run_dir}"]}
