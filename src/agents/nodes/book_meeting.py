"""BookMeeting node - prepares meeting booking data for CRM integration."""

from __future__ import annotations

import logging
import re

from src.agents.state import AOROState
from src.core.observability import get_openai_client, traceable_fn

logger = logging.getLogger(__name__)


async def extract_meeting_preferences(response_text: str) -> dict:
    """
    Extract meeting preferences from response text.
    
    Args:
        response_text: Response content from customer
    
    Returns:
        Dictionary with meeting preferences (times, dates, format, etc.)
    """
    client = get_openai_client()
    
    system = (
        "You are a meeting scheduler assistant. Extract meeting preferences "
        "from customer responses. Return structured data about preferred times, "
        "dates, meeting format (phone, video, in-person), and any constraints."
    )
    
    user = f"""
Extract meeting preferences from this customer response:

"{response_text}"

Return a JSON object with:
- preferred_times: list of preferred times mentioned (e.g., ["morning", "afternoon", "2pm"])
- preferred_dates: list of preferred dates mentioned (e.g., ["next week", "Monday", "Jan 15"])
- meeting_format: "phone", "video", "in-person", or "any"
- timezone: inferred timezone or null
- constraints: list of constraints mentioned (e.g., ["not before 9am", "weekdays only"])
- urgency: "high", "medium", "low" based on language used
"""
    
    try:
        resp = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.1,
            response_format={"type": "json_object"},
        )
        
        import json
        preferences = json.loads(resp.choices[0].message.content or "{}")
        return preferences
    except Exception as e:
        logger.warning(f"Error extracting meeting preferences: {e}", exc_info=True)
        # Return default preferences
        return {
            "preferred_times": [],
            "preferred_dates": [],
            "meeting_format": "any",
            "timezone": None,
            "constraints": [],
            "urgency": "medium",
        }


@traceable_fn("book_meeting_agent")
async def book_meeting_node(state: AOROState) -> AOROState:
    """
    Prepare meeting booking data for CRM integration.
    
    Extracts meeting preferences from response and prepares booking payload.
    Actual CRM booking happens in Phase 3 (UpdateCRM node).
    """
    response_data = state.get("response_data") or {}
    decision_maker = state.get("decision_maker") or {}
    permit_data = state.get("permit_data") or {}
    company_name = state.get("company_name", "Unknown Company")
    lead_id = state.get("lead_id", "")
    
    # Extract meeting preferences from response
    response_text = response_data.get("content", "")
    meeting_preferences = await extract_meeting_preferences(response_text)
    
    # Prepare booking payload for CRM
    booking_payload = {
        "lead_id": lead_id,
        "company_name": company_name,
        "decision_maker": {
            "full_name": decision_maker.get("full_name") or decision_maker.get("name"),
            "email": decision_maker.get("email") or decision_maker.get("email_address"),
            "title": decision_maker.get("title"),
            "phone": decision_maker.get("phone"),
        },
        "permit_data": {
            "permit_id": permit_data.get("permit_id"),
            "permit_type": permit_data.get("permit_type"),
            "address": permit_data.get("address"),
            "status": permit_data.get("status"),
        },
        "meeting_preferences": meeting_preferences,
        "meeting_type": "consultation",
        "source": "agentic_workflow",
        "notes": f"Generated from permit: {permit_data.get('permit_id', 'N/A')}. "
                 f"Response classification: {state.get('response_classification', 'positive')}",
        "compliance_gaps": state.get("compliance_gaps", []),
        "applicable_codes": state.get("applicable_codes", []),
    }
    
    logger.info(f"Booking payload prepared for lead {lead_id}")
    logger.debug(f"Meeting preferences: {meeting_preferences}")
    
    return {
        **state,
        "booking_payload": booking_payload,
        "booking_ready": True,
        "meeting_preferences": meeting_preferences,
    }
