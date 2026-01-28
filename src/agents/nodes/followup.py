"""FollowUp node - automated follow-up sequences with max attempts."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from src.agents.state import AOROState
from src.core.config import get_settings
from src.core.observability import get_openai_client, traceable_fn

logger = logging.getLogger(__name__)


async def generate_followup_message(state: AOROState, attempt_number: int) -> str:
    """
    Generate follow-up message based on attempt number.
    
    Args:
        state: Current workflow state
        attempt_number: Follow-up attempt number (1, 2, 3...)
    
    Returns:
        Follow-up message draft
    """
    client = get_openai_client()
    
    company_name = state.get("company_name", "there")
    permit_data = state.get("permit_data") or {}
    compliance_gaps = state.get("compliance_gaps", [])
    case_studies = state.get("case_studies", [])
    
    # Build context for follow-up
    context = f"""
Company: {company_name}
Permit: {permit_data.get('permit_id', 'N/A')} - {permit_data.get('permit_type', 'N/A')}
Compliance Gaps: {', '.join(compliance_gaps[:3]) if compliance_gaps else 'None identified'}
"""
    
    if attempt_number == 1:
        # First follow-up: Gentle reminder, add value
        system = (
            "You are a sales outreach specialist. Write a friendly follow-up email "
            "that adds value. Include a relevant case study or code update if available. "
            "Keep it concise and helpful."
        )
        user = f"""
Write a follow-up email for {company_name} regarding their fire safety permit.

Context:
{context}

This is the first follow-up (3 days after initial outreach).
Add value by:
- Referencing a relevant case study if available
- Mentioning any recent code updates that might affect them
- Being helpful and non-pushy

Subject line should be: "Re: Fire Safety Compliance Consultation - [Value Add]"
"""
    elif attempt_number == 2:
        # Second follow-up: Final attempt, soft close
        system = (
            "You are a sales outreach specialist. Write a final follow-up email "
            "that gently closes the conversation. Offer one last opportunity to connect, "
            "but respect their decision if they're not interested."
        )
        user = f"""
Write a final follow-up email for {company_name} regarding their fire safety permit.

Context:
{context}

This is the second follow-up (7 days after initial outreach).
This is our final attempt. Be respectful and offer one last opportunity to connect.
If they're not interested, that's okay - we'll respect their decision.

Subject line should be: "Final Follow-up: Fire Safety Compliance Consultation"
"""
    else:
        # Additional follow-ups: Very soft, value-focused
        system = (
            "You are a sales outreach specialist. Write a very soft follow-up email "
            "that focuses on providing value without being pushy."
        )
        user = f"""
Write a follow-up email for {company_name} regarding their fire safety permit.

Context:
{context}

This is follow-up attempt #{attempt_number}. Keep it very soft and value-focused.
"""
    
    try:
        resp = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.7,
        )
        
        return resp.choices[0].message.content or "Follow-up message not generated."
    except Exception as e:
        logger.error(f"Error generating follow-up message: {e}", exc_info=True)
        return f"Subject: Re: Fire Safety Compliance Consultation\n\nHi {company_name},\n\nJust following up on my previous message about fire safety compliance. I'd love to help you ensure your facility meets all requirements.\n\nBest regards"
    finally:
        pass


@traceable_fn("followup_agent")
async def followup_node(state: AOROState) -> AOROState:
    """
    Schedule and send follow-up outreach.
    
    Tracks follow-up attempts and generates appropriate follow-up messages.
    After max attempts, marks workflow as complete with "no_response" status.
    """
    settings = get_settings()
    followup_count = state.get("followup_count", 0)
    max_followups = getattr(settings, "max_followup_attempts", 2)
    
    logger.info(f"Follow-up attempt {followup_count + 1} of {max_followups}")
    
    # Check if max attempts reached
    if followup_count >= max_followups:
        logger.info(f"Max follow-up attempts ({max_followups}) reached. Ending workflow.")
        return {
            **state,
            "workflow_complete": True,
            "workflow_status": "no_response",
            "followup_count": followup_count,
        }
    
    # Generate follow-up message
    attempt_number = followup_count + 1
    followup_draft = await generate_followup_message(state, attempt_number)
    
    # Calculate next follow-up schedule
    # First follow-up: 3 days, Second: 7 days, etc.
    days_until_next = 3 * attempt_number if attempt_number <= 2 else 7
    followup_scheduled_at = datetime.now() + timedelta(days=days_until_next)
    
    logger.info(f"Follow-up scheduled for {followup_scheduled_at.isoformat()}")
    
    return {
        **state,
        "followup_count": followup_count + 1,
        "outreach_draft": followup_draft,
        "followup_scheduled_at": followup_scheduled_at.isoformat(),
        "outreach_channel": state.get("outreach_channel", "email"),
    }
