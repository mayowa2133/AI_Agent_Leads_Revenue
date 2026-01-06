from __future__ import annotations

from src.agents.state import AOROState


async def human_review_node(state: AOROState) -> AOROState:
    """
    Human-in-the-loop approval node.

    For high-confidence leads we auto-approve. Otherwise we interrupt and expect
    an external reviewer to approve/reject and resume the graph.
    """
    score = float(state.get("qualification_score") or 0.0)
    if score >= 0.8:
        return {**state, "human_approved": True}

    # Interrupt for human review (LangGraph will pause here).
    from langgraph.prebuilt import interrupt

    interrupt(
        {
            "type": "approval_required",
            "lead_id": state.get("lead_id"),
            "draft": state.get("outreach_draft"),
            "confidence": score,
        }
    )

    # If the workflow is resumed without setting human_approved, default to False.
    return {**state, "human_approved": bool(state.get("human_approved", False))}


