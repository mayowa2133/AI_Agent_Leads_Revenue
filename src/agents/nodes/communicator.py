from __future__ import annotations

from src.agents.state import AOROState
from src.core.observability import get_openai_client, traceable_fn


async def generate_email_outreach(state: AOROState) -> str:
    """Generate email outreach draft."""
    permit = state.get("permit_data") or {}
    dm = state.get("decision_maker") or {}
    company = state.get("company_name") or "your facility"
    codes = state.get("applicable_codes") or []
    gaps = state.get("compliance_gaps") or []

    client = get_openai_client()
    system = (
        "You are a technical sales outreach assistant for commercial fire safety services. "
        "Be concise, credible, and specific. Avoid hype. Use code citations only if relevant."
    )
    user = f"""
Draft a first-touch email to a facility decision maker.

Context:
- Company: {company}
- Decision maker: {dm.get('full_name')} ({dm.get('title')})
- Permit type: {permit.get('permit_type')}
- Permit status: {permit.get('status')}
- Address: {permit.get('address')}
- Applicable codes: {codes}
- Potential compliance gaps: {gaps}

Constraints:
- 120-160 words
- Subject line included
- Offer a 15-minute call and propose 2 time windows
- Lead with technical value (inspection readiness, code alignment, risk reduction)
"""

    resp = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.4,
    )
    return resp.choices[0].message.content or ""


async def generate_whatsapp_outreach(state: AOROState) -> str:
    """Generate WhatsApp outreach draft (shorter, more casual)."""
    permit = state.get("permit_data") or {}
    dm = state.get("decision_maker") or {}
    company = state.get("company_name") or "your facility"
    codes = state.get("applicable_codes") or []

    client = get_openai_client()
    system = (
        "You are a technical sales outreach assistant for commercial fire safety services. "
        "Write in a professional but friendly tone suitable for WhatsApp."
    )
    user = f"""
Draft a WhatsApp message to a facility decision maker.

Context:
- Company: {company}
- Decision maker: {dm.get('full_name')} ({dm.get('title')})
- Permit type: {permit.get('permit_type')}
- Permit status: {permit.get('status')}
- Applicable codes: {codes}

Constraints:
- 60-80 words (WhatsApp is shorter)
- Professional but friendly tone
- Offer a quick call
- Lead with value proposition
"""

    resp = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.4,
    )
    return resp.choices[0].message.content or ""


async def generate_voice_script(state: AOROState) -> str:
    """Generate voice call script (conversational, structured)."""
    permit = state.get("permit_data") or {}
    dm = state.get("decision_maker") or {}
    company = state.get("company_name") or "your facility"
    codes = state.get("applicable_codes") or []

    client = get_openai_client()
    system = (
        "You are a technical sales outreach assistant for commercial fire safety services. "
        "Write a conversational phone script that sounds natural when spoken."
    )
    user = f"""
Draft a phone call script for reaching out to a facility decision maker.

Context:
- Company: {company}
- Decision maker: {dm.get('full_name')} ({dm.get('title')})
- Permit type: {permit.get('permit_type')}
- Permit status: {permit.get('status')}
- Applicable codes: {codes}

Constraints:
- 150-200 words
- Conversational tone (sounds natural when spoken)
- Include opening, value proposition, and call-to-action
- Leave room for conversation
"""

    resp = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.4,
    )
    return resp.choices[0].message.content or ""


@traceable_fn("communication_agent")
async def communicator_node(state: AOROState) -> AOROState:
    """
    Communication agent node that generates outreach for the specified channel.
    
    Supports multiple channels:
    - email: Full email with subject line
    - whatsapp: Shorter, more casual message
    - voice: Conversational phone script
    """
    channel = state.get("outreach_channel", "email")
    
    if channel == "email":
        draft = await generate_email_outreach(state)
    elif channel == "whatsapp":
        draft = await generate_whatsapp_outreach(state)
    elif channel == "voice":
        draft = await generate_voice_script(state)
    else:
        # Default to email if unknown channel
        draft = await generate_email_outreach(state)
        channel = "email"

    return {**state, "outreach_draft": draft, "outreach_channel": channel}


