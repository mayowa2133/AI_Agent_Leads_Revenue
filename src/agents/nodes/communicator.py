from __future__ import annotations

from src.agents.state import AOROState
from src.core.observability import get_openai_client, traceable_fn


@traceable_fn("communication_agent")
async def communicator_node(state: AOROState) -> AOROState:
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
    draft = resp.choices[0].message.content or ""

    return {**state, "outreach_draft": draft, "outreach_channel": state.get("outreach_channel", "email")}


