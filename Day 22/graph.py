from langgraph.graph import END, START, StateGraph

from agents import (
    analyzer,
    coordinator_finalize,
    coordinator_plan,
    critic_draft,
    critic_findings,
    research_agent,
    route_after_draft_critic,
    route_after_findings_critic,
    writer,
)
from state import State


def build_graph():
    g = StateGraph(State)

    g.add_node("coordinator_plan", coordinator_plan)
    g.add_node("research", research_agent)
    g.add_node("analyzer", analyzer)
    g.add_node("critic_findings", critic_findings)
    g.add_node("writer", writer)
    g.add_node("critic_draft", critic_draft)
    g.add_node("finalize", coordinator_finalize)

    g.add_edge(START, "coordinator_plan")
    g.add_edge("coordinator_plan", "research")
    g.add_edge("research", "analyzer")
    g.add_edge("analyzer", "critic_findings")
    g.add_conditional_edges(
        "critic_findings",
        route_after_findings_critic,
        {"research": "research", "analyzer": "analyzer", "writer": "writer"},
    )
    g.add_edge("writer", "critic_draft")
    g.add_conditional_edges(
        "critic_draft",
        route_after_draft_critic,
        {"writer": "writer", "finalize": "finalize"},
    )
    g.add_edge("finalize", END)

    return g.compile()
