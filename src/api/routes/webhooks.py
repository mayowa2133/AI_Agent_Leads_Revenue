from __future__ import annotations

import logging
import re
from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel

from src.agents.monitoring import append_workflow_event
from src.agents.nodes.book_meeting import book_meeting_node
from src.agents.nodes.handle_response import handle_response_node
from src.agents.nodes.update_crm import update_crm_node
from src.agents.storage.workflow_storage import WorkflowStorage

logger = logging.getLogger(__name__)
router = APIRouter()


class InboundMessage(BaseModel):
    tenant_id: str
    lead_id: str | None = None
    channel: str
    from_contact: str | None = None
    message: str
    metadata: dict[str, Any] = {}


class EmailResponseWebhook(BaseModel):
    """Webhook payload from email service (SendGrid, SES, etc.)."""
    lead_id: str | None = None
    email_id: str | None = None
    from_email: str
    to_email: str
    subject: str | None = None
    content: str
    received_at: str | None = None
    source: str = "email"
    metadata: dict[str, Any] = {}


@router.post("/inbound", response_model=dict[str, Any])
async def inbound(req: InboundMessage):
    """
    Generic inbound message webhook.
    
    MVP: accept the webhook and return ok.
    Later: append to lead conversation history and re-enter graph at HandleResponse.
    """
    return {"ok": True, "received": req.model_dump()}


@router.post("/email-response", response_model=dict[str, Any])
async def handle_email_response(request: Request, payload: EmailResponseWebhook | dict[str, Any]):
    """
    Webhook endpoint for email service to notify about responses.
    
    Supports:
    - SendGrid webhook format
    - AWS SES SNS format
    - Generic email response format
    
    Saves response to workflow storage and triggers workflow resumption.
    """
    # Handle both Pydantic model and raw dict (for flexible webhook formats)
    if isinstance(payload, dict):
        payload_dict = payload
    else:
        payload_dict = payload.model_dump()
    
    # Extract lead_id from email metadata or subject
    lead_id = payload_dict.get("lead_id")
    if not lead_id:
        # Try to extract from email subject or metadata
        subject = payload_dict.get("subject", "")
        metadata = payload_dict.get("metadata", {})
        lead_id = metadata.get("lead_id") or metadata.get("leadId")
        if not lead_id and subject:
            match = re.search(r"\[AORO-([A-Za-z0-9-]+)\]", subject)
            if match:
                lead_id = match.group(1)        # Could also parse from subject line if needed
        # e.g., "Re: [AORO-LEAD-123] Fire Safety Consultation"
    
    if not lead_id:
        logger.warning("No lead_id found in email response webhook")
        return {"ok": False, "error": "lead_id required"}
    
    # Extract response content
    content = payload_dict.get("content", "") or payload_dict.get("message", "") or payload_dict.get("body", "")
    from_email = payload_dict.get("from_email") or payload_dict.get("from")
    to_email = payload_dict.get("to_email") or payload_dict.get("to")
    
    # Save response to workflow storage
    storage = WorkflowStorage()
    storage.save_response(
        lead_id,
        {
            "content": content,
            "from_email": from_email,
            "to_email": to_email,
            "subject": payload_dict.get("subject"),
            "received_at": payload_dict.get("received_at"),
            "source": payload_dict.get("source", "email"),
            "email_id": payload_dict.get("email_id"),
            "metadata": payload_dict.get("metadata", {}),
        },
    )
    append_workflow_event(
        "response_received",
        {"lead_id": lead_id, "from_email": from_email, "to_email": to_email},
    )
    
    logger.info(f"Email response saved for lead {lead_id} from {from_email}")
    
    # Resume workflow from stored state (free JSON storage)
    saved_state = storage.load_workflow_state(lead_id)
    if saved_state:
        state = {
            **saved_state,
            "response_received": True,
            "response_timeout": False,
            "waiting_for_response": False,
            "response_data": {
                "content": content,
                "from_email": from_email,
                "to_email": to_email,
                "subject": payload_dict.get("subject"),
                "received_at": payload_dict.get("received_at"),
                "source": payload_dict.get("source", "email"),
                "email_id": payload_dict.get("email_id"),
                "metadata": payload_dict.get("metadata", {}),
            },
        }
        state = await handle_response_node(state)
        if state.get("response_classification") == "positive":
            state = await book_meeting_node(state)
            state = await update_crm_node(state)
        storage.save_workflow_state(lead_id, state)
    
    return {
        "ok": True,
        "lead_id": lead_id,
        "message": "Response saved",
    }
