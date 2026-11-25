"""Agent nodes, routing guards, and schema normalization helpers for the research workflow."""

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


def _sources_for_prompt(sources: list[dict]) -> list[dict]:
    formatted = []
    for src in sources[:MAX_SOURCES_IN_PROMPT]:
        body = (src.get("text") or src.get("snippet") or "")[:SOURCE_CHARS_IN_PROMPT]
        formatted.append(
            {"id": src["id"], "title": src["title"], "url": src["url"], "content": body}
        )
    return formatted


def _cited_ids(text: str) -> set[int]:
    ids: set[int] = set()
    for group in re.findall(r"\[(\d+(?:\s*,\s*\d+)*)\]", text):
        ids.update(int(item) for item in re.split(r"\s*,\s*", group))
    return ids


def _as_int(value) -> int | None:
    try:
        if isinstance(value, bool):
            return None
        if isinstance(value, int):
            return value
        return int(float(str(value).strip().strip("[]# ")))
    except (ValueError, TypeError):
        return None


def _str_list(value) -> list[str]:
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return []


def _score(value) -> float:
    try:
        return max(0.0, min(10.0, float(value)))
    except (ValueError, TypeError):
        return 0.0


def _norm_verdict(verdict, allowed: set[str], default: str) -> str:
    normalized = str(verdict).strip().lower()
    return normalized if normalized in allowed else default


def _norm_issues(items) -> list[dict[str, str]]:
    if isinstance(items, (str, dict)):
        items = [items]
    if not isinstance(items, list):
        return []
    normalized_issues = []
    for item in items:
        if isinstance(item, dict):
            severity = str(item.get("severity", "medium")).lower()
            if severity not in ("high", "medium", "low"):
                severity = "medium"
            normalized_issues.append(
                {"severity": severity, "description": str(item.get("description", ""))}
            )
        elif isinstance(item, str) and item.strip():
            normalized_issues.append({"severity": "medium", "description": item.strip()})
    return normalized_issues


def _high_issues(critique: dict) -> list[dict[str, str]]:
    return [issue for issue in critique.get("issues", []) if issue.get("severity") == "high"]


def _clean_contradictions(raw_contradictions, valid_ids: set[int]) -> list[dict]:
    if not isinstance(raw_contradictions, list):
        return []
    cleaned = []
    for entry in raw_contradictions:
        if isinstance(entry, dict):
            source_ids = [
                parsed_id
                for parsed_id in (_as_int(raw_id) for raw_id in (entry.get("source_ids") or []))
                if parsed_id in valid_ids
            ]
            cleaned.append(
                {"description": str(entry.get("description", "")), "source_ids": source_ids}
            )
        elif isinstance(entry, str) and entry.strip():
            cleaned.append({"description": entry.strip(), "source_ids": []})
    return cleaned


def _clean_findings(raw, valid_ids: set[int]) -> dict:
    """Normalize Analyzer output into the expected schema and drop unsupported findings."""
    if isinstance(raw, list):
        raw = {"findings": raw}
    if not isinstance(raw, dict):
        raw = {}
    items = raw.get("findings")
    if not isinstance(items, list):
        items = []

    kept_findings = []
    for finding in items:
        if not isinstance(finding, dict):
            continue
        raw_ids = finding.get("source_ids", [])
        if not isinstance(raw_ids, list):
            raw_ids = [raw_ids]
        source_ids = sorted(
            {
                parsed_id
                for parsed_id in (_as_int(raw_id) for raw_id in raw_ids)
                if parsed_id in valid_ids
            }
        )
        if not source_ids:
            continue
        try:
            confidence = max(0.0, min(1.0, float(finding.get("confidence", 0.5))))
        except (TypeError, ValueError):
            confidence = 0.5
        kept_findings.append(
            {
                "sub_question": str(finding.get("sub_question", "")),
                "claim": str(finding.get("claim", "")),
                "source_ids": source_ids,
                "confidence": confidence,
            }
        )

    return {
        "findings": kept_findings,
        "themes": _str_list(raw.get("themes")),
        "contradictions": _clean_contradictions(raw.get("contradictions"), valid_ids),
        "gaps": _str_list(raw.get("gaps")),
    }


def _evaluate_critique(
    raw_critique,
    allowed_verdicts: set[str],
    programmatic_issues: list[dict[str, str]],
) -> dict:
    critique = raw_critique if isinstance(raw_critique, dict) else {}
    verdict = _norm_verdict(critique.get("verdict"), allowed_verdicts, "revise")
    score = _score(critique.get("score"))
    issues = _norm_issues(critique.get("issues")) + programmatic_issues

    has_high = any(issue.get("severity") == "high" for issue in issues)
    if score >= PASS_SCORE and not has_high:
        verdict = "approve"
    elif programmatic_issues and verdict == "approve":
        verdict = "revise"

    return {
        "verdict": verdict,
        "score": score,
        "issues": issues,
        "gap_queries": _str_list(critique.get("gap_queries")),
    }


def coordinator_plan(state: State) -> dict:
    """Decompose the user query into sub-questions and initial search queries."""
    plan = chat_json(
        "You are the Coordinator of a research team. Decompose the research question.\n"
        'Schema: {"sub_questions": [str, 3-5 items], "scope": str, '
        '"search_queries": [str, 1-2 per sub-question, concise queries]}',
        state["query"],
    )
    if not isinstance(plan, dict):
        plan = {}
    sub_questions = _str_list(plan.get("sub_questions"))[:6] or [state["query"]]
    search_queries = _str_list(plan.get("search_queries"))[:10] or sub_questions
    return {
        "plan": {"sub_questions": sub_questions, "scope": str(plan.get("scope", ""))},
        "search_queries": search_queries,
        "sources": [],
        "analysis_iter": 0,
        "writer_iter": 0,
        "forced_caveats": [],
        "log": [f"[coordinator] planned {len(sub_questions)} sub-questions"],
    }


def _build_source_record(source_id: int, result: dict, text: str, query: str) -> dict:
    return {
        "id": source_id,
        "title": result["title"],
        "url": result["url"],
        "snippet": result["snippet"],
        "text": text,
        "query": query,
    }


def research_agent(state: State) -> dict:
    """Retrieve new sources from local documents and/or web search for pending queries."""
    sources = list(state.get("sources", []))
    seen_urls = {src["url"] for src in sources}
    added_count = 0

    for query in state.get("search_queries", []):
        results = search(query, RESULTS_PER_QUERY)
        fetched_count = 0
        for result in results:
            url = result["url"]
            if url in seen_urls:
                continue
            seen_urls.add(url)

            if result.get("text"):
                text = result["text"]
            elif url.startswith("http") and fetched_count < FETCH_TOP_N:
                text = fetch_text(url)
                fetched_count += 1
            else:
                text = ""

            sources.append(_build_source_record(len(sources) + 1, result, text, query))
            added_count += 1

    return {
        "sources": sources,
        "search_queries": [],
        "log": [f"[research] +{added_count} sources (total {len(sources)})"],
    }


def route_after_research(state: State) -> str:
    """Route to analysis if any sources were gathered; otherwise abort."""
    return "analyzer" if state.get("sources") else "no_sources"


def abort_no_sources(state: State) -> dict:
    """Stop execution cleanly and persist an explanatory report when no sources exist."""
    if SOURCE_MODE == "web":
        hint = "Check your internet connection and run: pip install -U ddgs"
    else:
        hint = (
            f"No readable .txt/.md/.pdf files were found in '{DOCS_DIR}/' "
            "(relative to the folder you run the command from). "
            "Copy your files there, or set RA_SOURCE=web / both."
        )
    message = (
        "# No sources retrieved\n\n"
        "The run was stopped so the model would not invent an answer.\n\n"
        f"{hint}\n"
    )
    run_dir = save_run(state, message, "no_sources")
    return {
        "final_report": message,
        "log": [
            "[coordinator] aborted: no sources retrieved",
            f"[coordinator] saved run to {run_dir}",
        ],
    }


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
    """Extract source-grounded findings and contradictions from retrieved sources."""
    valid_ids = {src["id"] for src in state["sources"]}
    payload = json.dumps(
        {
            "query": state["query"],
            "sub_questions": state["plan"]["sub_questions"],
            "prior_critic_issues": state.get("critique", {}).get("issues", []),
            "sources": _sources_for_prompt(state["sources"]),
        }
    )
    findings = _clean_findings({}, valid_ids)
    for attempt in range(2):
        schema_reminder = (
            ""
            if attempt == 0
            else "\nIMPORTANT: every item in 'findings' MUST be an object with 'claim' and "
            "'source_ids' (a list of integer ids from the sources). Plain strings are invalid."
        )
        raw = chat_json(_ANALYZER_SYSTEM + schema_reminder, payload, max_tokens=6000)
        findings = _clean_findings(raw, valid_ids)
        if findings["findings"]:
            break

    iteration = state.get("analysis_iter", 0) + 1
    return {
        "findings": findings,
        "analysis_iter": iteration,
        "log": [f"[analyzer] iteration {iteration}: {len(findings['findings'])} findings"],
    }


def critic_findings(state: State) -> dict:
    """Critique extracted findings and decide whether to approve, revise, or re-search."""
    programmatic_issues = []
    if not state["findings"].get("findings"):
        programmatic_issues.append(
            {
                "severity": "high",
                "description": "No findings with valid source citations were produced.",
            }
        )

    raw_critique = chat_json(
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
    critique = _evaluate_critique(
        raw_critique, {"approve", "revise", "re_search"}, programmatic_issues
    )

    update = {
        "critique": critique,
        "log": [
            f"[critic:findings] {critique['verdict']} "
            f"score={critique['score']:g} issues={len(critique['issues'])}"
        ],
    }
    if critique["verdict"] == "re_search":
        update["search_queries"] = critique["gap_queries"]
    if critique["verdict"] != "approve" and state["analysis_iter"] >= MAX_ANALYSIS_ITERS:
        update["forced_caveats"] = [issue["description"] for issue in critique["issues"]]
        update["log"].append("[coordinator] analysis loop cap hit; proceeding with caveats")
    return update


def route_after_findings_critic(state: State) -> str:
    """Route to writer on approval or loop cap, or loop back to research/analyzer."""
    verdict = state["critique"]["verdict"]
    if verdict == "approve" or state["analysis_iter"] >= MAX_ANALYSIS_ITERS:
        return "writer"
    if verdict == "re_search" and state.get("search_queries"):
        return "research"
    return "analyzer"


def writer(state: State) -> dict:
    """Draft or revise the structured Markdown research report from approved findings."""
    iteration = state.get("writer_iter", 0) + 1
    if not state["findings"].get("findings"):
        draft = (
            "## Executive Summary\n\nNo findings supported by the retrieved sources could be "
            "extracted, so no report content is provided.\n\n## Limitations\n\n"
            "The model could not produce source-backed findings. Try rephrasing the question, "
            "adding more documents to `docs/`, or using a larger model."
        )
        return {
            "draft": draft,
            "writer_iter": iteration,
            "log": [f"[writer] draft v{iteration} (no findings)"],
        }

    feedback = (
        state.get("draft_critique", {}).get("issues", []) if state.get("draft") else []
    )
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
                "valid_source_ids": [src["id"] for src in state["sources"]],
            }
        ),
        max_tokens=6000,
    )
    return {"draft": draft, "writer_iter": iteration, "log": [f"[writer] draft v{iteration}"]}


def critic_draft(state: State) -> dict:
    """Review the drafted report for grounding, sub-question coverage, and valid citations."""
    if not state["findings"].get("findings"):
        critique = {
            "verdict": "revise",
            "score": 0.0,
            "issues": [
                {"severity": "high", "description": "No source-backed findings were available."}
            ],
            "gap_queries": [],
        }
        return {"draft_critique": critique, "log": ["[critic:draft] revise score=0 (no findings)"]}

    valid_ids = {src["id"] for src in state["sources"]}
    fabricated_ids = sorted(_cited_ids(state.get("draft", "")) - valid_ids)
    programmatic_issues = (
        [{"severity": "high", "description": f"Fabricated citation ids: {fabricated_ids}"}]
        if fabricated_ids
        else []
    )

    raw_critique = chat_json(
        "You are the Critic reviewing a draft report against the approved findings. "
        "Check faithfulness (no claims beyond findings), coverage of all sub-questions, "
        "clarity, and honest limitations.\n"
        'Schema: {"verdict": "approve"|"revise", "score": 0-10, '
        '"issues": [{"severity": "high"|"medium"|"low", "description": str}]}',
        json.dumps(
            {
                "sub_questions": state["plan"]["sub_questions"],
                "findings": state["findings"],
                "draft": state.get("draft", ""),
            }
        ),
        max_tokens=2500,
    )
    critique = _evaluate_critique(raw_critique, {"approve", "revise"}, programmatic_issues)
    return {
        "draft_critique": critique,
        "log": [f"[critic:draft] {critique['verdict']} score={critique['score']:g}"],
    }


def route_after_draft_critic(state: State) -> str:
    """Finalize report when draft is approved or writer loop cap is reached."""
    draft_critique = state.get("draft_critique", {})
    if draft_critique.get("verdict") == "approve" or state.get("writer_iter", 0) >= MAX_WRITER_ITERS:
        return "finalize"
    return "writer"


def coordinator_finalize(state: State) -> dict:
    """Sanitize citations, assemble final report with references, and save run artifacts."""
    draft = state.get("draft", "")
    sources_by_id = {src["id"]: src for src in state.get("sources", [])}
    cited_ids = sorted(cid for cid in _cited_ids(draft) if cid in sources_by_id)

    def _strip_invalid_citations(match) -> str:
        valid_group_ids = [
            int(token)
            for token in re.split(r"\s*,\s*", match.group(1))
            if int(token) in sources_by_id
        ]
        return f"[{', '.join(map(str, valid_group_ids))}]" if valid_group_ids else ""

    sanitized_draft = re.sub(r"\[(\d+(?:\s*,\s*\d+)*)\]", _strip_invalid_citations, draft)
    references = "\n".join(
        f"[{cid}] {sources_by_id[cid]['title']}. {sources_by_id[cid]['url']}"
        for cid in cited_ids
    )
    report = (
        f"# {state.get('query', '')}\n\n"
        f"{sanitized_draft}\n\n"
        f"## References\n\n{references}\n"
    )

    caveats = state.get("forced_caveats", [])
    draft_critique = state.get("draft_critique", {})
    has_caveats = bool(caveats) or draft_critique.get("verdict") != "approve"
    if has_caveats:
        report += "\n## Review Notes\n\nThe quality loop hit its iteration cap. Open issues:\n"
        open_issues = caveats + [
            issue.get("description", "") for issue in draft_critique.get("issues", [])
        ]
        report += "\n".join(f"- {desc}" for desc in open_issues if desc) + "\n"

    status = "ok_with_caveats" if has_caveats else "ok"
    run_dir = save_run(state, report, status)
    return {"final_report": report, "log": [f"[coordinator] saved run to {run_dir}"]}
