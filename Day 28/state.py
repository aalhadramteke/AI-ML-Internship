"""Shared LangGraph state definition for the multi-agent research workflow."""

import operator
from typing import Annotated, Any, Dict, List, TypedDict


class State(TypedDict, total=False):
    query: str
    plan: Dict[str, Any]            # sub_questions, scope
    search_queries: List[str]       # pending queries for Research Agent
    sources: List[Dict[str, Any]]   # {id, title, url, snippet, text}
    findings: Dict[str, Any]        # Analyzer output
    critique: Dict[str, Any]        # Critic verdict on findings
    draft: str
    draft_critique: Dict[str, Any]  # Critic verdict on draft
    analysis_iter: int
    writer_iter: int
    forced_caveats: List[str]       # limitations if loops hit their cap
    final_report: str
    log: Annotated[List[str], operator.add]
