import json
import os
import re
from datetime import datetime

from config import (
    FETCH_TOP_N,
    MAX_ANALYSIS_ITERS,
    MAX_SOURCES_IN_PROMPT,
    MAX_WRITER_ITERS,
    OUTPUT_DIR,
    PASS_SCORE,
    RESULTS_PER_QUERY,
    SOURCE_CHARS_IN_PROMPT,
)
from llm import chat, chat_json
from state import State
from tools import fetch_text, search


# ---------- helpers ----------

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


def _high_issues(critique):
    return [i for i in critique.get("issues", []) if i.get("severity") == "high"]


# ---------- 1. Coordinator: plan ----------

def coordinator_plan(state: State) -> dict:
    plan = chat_json(
        "You are the Coordinator of a research team. Decompose the research question.\n"
        'Schema: {"sub_questions": [str, 3-5 items], "scope": str, '
        '"search_queries": [str, 1-2 per sub-question, concise web queries]}',
        state["query"],
    )
    return {
        "plan": {"sub_questions": plan["sub_questions"], "scope": plan.get("scope", "")},
        "search_queries": plan["search_queries"],
        "sources": [],
        "analysis_iter": 0,
        "writer_iter": 0,
        "forced_caveats": [],
        "log": [f"[coordinator] planned {len(plan['sub_questions'])} sub-questions"],
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


# ---------- 3. Analyzer ----------

def analyzer(state: State) -> dict:
    prior = state.get("critique", {}).get("issues", [])
    findings = chat_json(
        "You are the Analyzer. Extract findings ONLY supported by the provided sources.\n"
        "Every finding must cite source ids that exist. Flag contradictions between sources.\n"
        'Schema: {"findings": [{"sub_question": str, "claim": str, "source_ids": [int], '
        '"confidence": float 0-1}], "themes": [str], '
        '"contradictions": [{"description": str, "source_ids": [int]}], "gaps": [str]}\n'
        "If prior critic issues are given, fix them.",
        json.dumps(
            {
                "query": state["query"],
                "sub_questions": state["plan"]["sub_questions"],
                "prior_critic_issues": prior,
                "sources": _sources_for_prompt(state["sources"]),
            }
        ),
        max_tokens=6000,
    )
    n = state.get("analysis_iter", 0) + 1
    return {
        "findings": findings,
        "analysis_iter": n,
        "log": [f"[analyzer] iteration {n}: {len(findings.get('findings', []))} findings"],
    }


# ---------- 4a. Critic: findings ----------

def critic_findings(state: State) -> dict:
    valid_ids = {s["id"] for s in state["sources"]}
    prog_issues = []
    for f in state["findings"].get("findings", []):
        bad = [i for i in f.get("source_ids", []) if i not in valid_ids]
        if bad or not f.get("source_ids"):
            prog_issues.append(
                {
                    "severity": "high",
                    "description": f"Unsupported/invalid sources {bad} for claim: {f.get('claim', '')[:80]}",
                }
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
    c["issues"] = c.get("issues", []) + prog_issues

    # Code-enforced gate (LLM verdict alone is not trusted)
    if c.get("score", 0) >= PASS_SCORE and not _high_issues(c):
        c["verdict"] = "approve"
    elif prog_issues and c.get("verdict") == "approve":
        c["verdict"] = "revise"

    update = {
        "critique": c,
        "log": [f"[critic:findings] {c['verdict']} score={c.get('score')} issues={len(c['issues'])}"],
    }
    if c["verdict"] == "re_search":
        update["search_queries"] = c.get("gap_queries", [])
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
    n = state.get("writer_iter", 0) + 1
    return {"draft": draft, "writer_iter": n, "log": [f"[writer] draft v{n}"]}


# ---------- 4b. Critic: draft ----------

def critic_draft(state: State) -> dict:
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
    c["issues"] = c.get("issues", []) + prog_issues
    if c.get("score", 0) >= PASS_SCORE and not _high_issues(c):
        c["verdict"] = "approve"
    elif prog_issues:
        c["verdict"] = "revise"
    return {
        "draft_critique": c,
        "log": [f"[critic:draft] {c['verdict']} score={c.get('score')}"],
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
    if caveats or state["draft_critique"]["verdict"] != "approve":
        report += "\n## Review Notes\n\nThe quality loop hit its iteration cap. Open issues:\n"
        issues = caveats + [i["description"] for i in state["draft_critique"].get("issues", [])]
        report += "\n".join(f"- {x}" for x in issues) + "\n"

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(OUTPUT_DIR, f"report_{stamp}.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(report)
    with open(os.path.join(OUTPUT_DIR, f"run_{stamp}.log"), "w", encoding="utf-8") as f:
        f.write("\n".join(state.get("log", [])))

    return {"final_report": report, "log": [f"[coordinator] saved {path}"]}
