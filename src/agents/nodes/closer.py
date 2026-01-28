from __future__ import annotations

from src.agents.state import AOROState
from src.core.observability import get_openai_client, traceable_fn


@traceable_fn("closer_agent")
async def closer_node(state: AOROState) -> AOROState:
    """
    Handle objections and prepare revised outreach message.
    
    Tracks objection handling cycles to prevent infinite loops.
    """
    import logging
    
    logger = logging.getLogger(__name__)
    
    # Get objection from extracted objections or current_objection
    extracted_objections = state.get("extracted_objections", [])
    current_objection = state.get("current_objection")
    
    # Use first extracted objection if current_objection not set
    objection = current_objection or (extracted_objections[0] if extracted_objections else None)
    
    if not objection:
        logger.warning("No objection found in state")
        return state

    # Increment objection handling count
    objection_count = state.get("objection_handling_count", 0) + 1

    client = get_openai_client()
    system = (
        "You are a commercial fire safety closer. Address objections with calm technical authority. "
        "Cite relevant codes only when it helps. Offer a next step."
    )
    user = f"""
Objection: {objection}

Context:
- Applicable codes: {state.get('applicable_codes') or []}
- Compliance gaps: {state.get('compliance_gaps') or []}
- Company: {state.get('company_name', 'Unknown')}

Write a short reply (4-8 sentences) that answers the objection and proposes scheduling.
"""
    resp = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        temperature=0.3,
    )
    reply = resp.choices[0].message.content or ""
    
    # Store objection reply in outreach_draft for revised message
    # Format as email draft
    outreach_draft = f"Subject: Re: Fire Safety Compliance Consultation\n\n{reply}"
    
    history = list(state.get("response_history") or [])
    history.append({"type": "objection_reply", "objection": objection, "reply": reply})
    
    logger.info(f"Objection handled (cycle {objection_count}): {objection[:50]}...")
    
    return {
        **state,
        "response_history": history,
        "outreach_draft": outreach_draft,
        "objection_handling_count": objection_count,
        "current_objection": objection,
    }


