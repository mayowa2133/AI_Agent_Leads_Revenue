from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from src.agents.orchestrator import build_graph
from src.core.security import tenant_scoped_session

router = APIRouter()


class RunAgentRequest(BaseModel):
    tenant_id: str
    lead_id: str | None = None
    company_name: str | None = None
    decision_maker: dict | None = None
    permit_data: dict
    outreach_channel: str | None = "email"


@router.post("/run", response_model=dict[str, Any])
async def run_agents(req: RunAgentRequest):
    graph = build_graph()
    async with tenant_scoped_session(req.tenant_id):
        state_in: dict[str, Any] = {
            "tenant_id": req.tenant_id,
            "lead_id": req.lead_id,
            "company_name": req.company_name,
            "decision_maker": req.decision_maker or {},
            "permit_data": req.permit_data,
            "outreach_channel": req.outreach_channel or "email",
        }
        state_out = await graph.ainvoke(state_in)
    return {"ok": True, "state": state_out}


