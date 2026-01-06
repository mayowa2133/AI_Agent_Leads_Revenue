from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from src.agents.nodes.closer import closer_node
from src.agents.nodes.communicator import communicator_node
from src.agents.nodes.human_review import human_review_node
from src.agents.nodes.researcher import researcher_node
from src.agents.state import AOROState
from src.core.observability import audit_event


async def lead_ingestion_node(state: AOROState) -> AOROState:
    # Normalize minimal required fields into state.
    permit = state.get("permit_data") or {}
    company_name = state.get("company_name") or permit.get("applicant_name") or "Unknown"
    return {
        **state,
        "company_name": company_name,
        "outreach_channel": state.get("outreach_channel", "email"),
        "response_history": state.get("response_history", []),
    }


async def qualification_check_node(state: AOROState) -> AOROState:
    permit = state.get("permit_data") or {}
    status = str(permit.get("status") or "").lower()
    ptype = str(permit.get("permit_type") or "").lower()

    score = 0.2
    if "issued" in status or "approved" in status:
        score += 0.3
    if "inspection" in status or "passed" in status:
        score += 0.2
    if "fire" in ptype:
        score += 0.2
    if state.get("decision_maker"):
        score += 0.1
    score = min(score, 1.0)

    return {**state, "qualification_score": score}


async def send_outreach_node(state: AOROState) -> AOROState:
    """
    Placeholder 'send' step. Real delivery (email/WhatsApp/voice) comes later.
    """
    history = list(state.get("response_history") or [])
    history.append(
        {
            "type": "outreach_ready",
            "channel": state.get("outreach_channel"),
            "draft": state.get("outreach_draft"),
        }
    )
    audit_event(
        "outreach_ready",
        {
            "lead_id": state.get("lead_id"),
            "channel": state.get("outreach_channel"),
            "confidence": state.get("qualification_score"),
        },
    )
    return {**state, "response_history": history}


def build_graph():
    graph = StateGraph(AOROState)

    graph.add_node("LeadIngestion", lead_ingestion_node)
    graph.add_node("Research", researcher_node)
    graph.add_node("QualificationCheck", qualification_check_node)
    graph.add_node("DraftOutreach", communicator_node)
    graph.add_node("HumanReview", human_review_node)
    graph.add_node("SendOutreach", send_outreach_node)
    graph.add_node("ObjectionHandling", closer_node)

    graph.add_edge(START, "LeadIngestion")
    graph.add_edge("LeadIngestion", "Research")
    graph.add_edge("Research", "QualificationCheck")

    def route_after_qualification(state: AOROState) -> str:
        if float(state.get("qualification_score") or 0.0) < 0.5:
            return END
        return "DraftOutreach"

    graph.add_conditional_edges("QualificationCheck", route_after_qualification)
    graph.add_edge("DraftOutreach", "HumanReview")

    def route_after_review(state: AOROState) -> str:
        if state.get("human_approved") is True:
            return "SendOutreach"
        return END

    graph.add_conditional_edges("HumanReview", route_after_review)
    graph.add_edge("SendOutreach", END)

    return graph.compile()


