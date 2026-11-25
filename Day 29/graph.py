"""LangGraph workflow definition for the multi-agent research assistant."""

from langgraph.graph import END, START, StateGraph

from agents import (
    abort_no_sources,
    analyzer,
    coordinator_finalize,
    coordinator_plan,
    critic_draft,
    critic_findings,
    research_agent,
    route_after_draft_critic,
    route_after_findings_critic,
    route_after_research,
    writer,
)
from state import State


def build_graph():
    """Compile and return the research assistant state graph."""
    graph = StateGraph(State)

    graph.add_node("coordinator_plan", coordinator_plan)
    graph.add_node("research", research_agent)
    graph.add_node("no_sources", abort_no_sources)
    graph.add_node("analyzer", analyzer)
    graph.add_node("critic_findings", critic_findings)
    graph.add_node("writer", writer)
    graph.add_node("critic_draft", critic_draft)
    graph.add_node("finalize", coordinator_finalize)

    graph.add_edge(START, "coordinator_plan")
    graph.add_edge("coordinator_plan", "research")
    graph.add_conditional_edges(
        "research",
        route_after_research,
        {"analyzer": "analyzer", "no_sources": "no_sources"},
    )
    graph.add_edge("no_sources", END)
    graph.add_edge("analyzer", "critic_findings")
    graph.add_conditional_edges(
        "critic_findings",
        route_after_findings_critic,
        {"research": "research", "analyzer": "analyzer", "writer": "writer"},
    )
    graph.add_edge("writer", "critic_draft")
    graph.add_conditional_edges(
        "critic_draft",
        route_after_draft_critic,
        {"writer": "writer", "finalize": "finalize"},
    )
    graph.add_edge("finalize", END)

    return graph.compile()
