from __future__ import annotations

from src.agents.state import AOROState


async def human_review_node(state: AOROState) -> AOROState:
    """
    Human-in-the-loop approval node.

    For high-confidence leads we auto-approve. Otherwise we set human_approved to False.
    
    TODO (Phase 2.2+): Implement proper interrupt mechanism with checkpointer for HITL.
    For now, we allow the workflow to continue for testing purposes.
    """
    score = float(state.get("qualification_score") or 0.0)
    
    # Auto-approve high confidence leads
    # Lowered from 0.8 to 0.6 to be more realistic given current scoring system
    if score >= 0.6:
        return {**state, "human_approved": True}

    # For lower confidence, require human approval
    # In production, this would trigger an interrupt and pause the workflow
    # For Phase 2.1 testing, we'll set to False and let the workflow continue
    # The routing logic will handle ending the workflow if not approved
    
    # Log that human review would be required
    import logging
    logger = logging.getLogger(__name__)
    logger.info(
        f"Human review required for lead {state.get('lead_id')} "
        f"(confidence: {score:.2f})"
    )
    
    # Set human_approved to False - workflow will end at routing check
    return {**state, "human_approved": False}


