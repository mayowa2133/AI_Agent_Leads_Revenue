"""HandleResponse node - classifies responses and routes appropriately."""

from __future__ import annotations

import logging

from src.agents.state import AOROState
from src.core.observability import get_openai_client, traceable_fn

logger = logging.getLogger(__name__)


@traceable_fn("handle_response_agent")
async def handle_response_node(state: AOROState) -> AOROState:
    """
    Classify response and route to appropriate handler.
    
    Classifies responses as:
    - positive: Interest expressed, scheduling requests, questions about services
    - objection: Price concerns, timing issues, not interested, already have vendor
    - no_response: Empty or acknowledgment-only responses
    - unsubscribe: Explicit opt-out requests
    """
    response_data = state.get("response_data") or {}
    response_text = response_data.get("content", "").strip()
    
    if not response_text:
        logger.warning("Empty response text, classifying as no_response")
        return {
            **state,
            "response_classification": "no_response",
            "response_sentiment": "neutral",
        }
    
    # Classify using LLM
    client = get_openai_client()
    system = (
        "You are a response classifier for sales outreach. "
        "Classify email responses into one of these categories: "
        "positive, objection, no_response, unsubscribe. "
        "Be accurate and concise."
    )
    user = f"""
Classify this email response:

"{response_text}"

Respond with ONLY a JSON object in this format:
{{
    "type": "positive" | "objection" | "no_response" | "unsubscribe",
    "sentiment": "positive" | "neutral" | "negative",
    "primary_objection": "string or null",
    "interest_level": "high" | "medium" | "low" | "none",
    "extracted_objections": ["list", "of", "objections"] or []
}}
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
        classification = json.loads(resp.choices[0].message.content or "{}")
        
        logger.info(
            f"Response classified as: {classification.get('type')} "
            f"(sentiment: {classification.get('sentiment')})"
        )
        
        return {
            **state,
            "response_classification": classification.get("type", "no_response"),
            "response_sentiment": classification.get("sentiment", "neutral"),
            "interest_level": classification.get("interest_level", "none"),
            "extracted_objections": classification.get("extracted_objections", []),
            "current_objection": classification.get("primary_objection"),
        }
    except Exception as e:
        logger.error(f"Error classifying response: {e}", exc_info=True)
        # Fallback: classify as no_response if classification fails
        return {
            **state,
            "response_classification": "no_response",
            "response_sentiment": "neutral",
        }
