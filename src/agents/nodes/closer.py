from __future__ import annotations

from src.agents.state import AOROState
from src.core.observability import get_openai_client, traceable_fn


@traceable_fn("closer_agent")
async def closer_node(state: AOROState) -> AOROState:
    objection = state.get("current_objection")
    if not objection:
        return state

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

Write a short reply (4-8 sentences) that answers the objection and proposes scheduling.
"""
    resp = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        temperature=0.3,
    )
    reply = resp.choices[0].message.content or ""
    history = list(state.get("response_history") or [])
    history.append({"type": "objection_reply", "objection": objection, "reply": reply})
    return {**state, "response_history": history}


