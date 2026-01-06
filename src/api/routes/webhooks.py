from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class InboundMessage(BaseModel):
    tenant_id: str
    lead_id: str | None = None
    channel: str
    from_contact: str | None = None
    message: str
    metadata: dict[str, Any] = {}


@router.post("/inbound", response_model=dict[str, Any])
async def inbound(req: InboundMessage):
    # MVP: accept the webhook and return ok.
    # Later: append to lead conversation history and re-enter graph at HandleResponse.
    return {"ok": True, "received": req.model_dump()}


