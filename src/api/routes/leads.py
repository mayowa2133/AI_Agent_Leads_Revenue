from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from src.signal_engine.enrichment.company_enricher import EnrichmentInputs, enrich_permit_to_lead
from src.signal_engine.models import EnrichedLead, PermitData

router = APIRouter()

# MVP in-memory store (swap for DB in next iteration)
LEADS: dict[str, EnrichedLead] = {}


class IngestPermitRequest(BaseModel):
    tenant_id: str
    permit: PermitData


@router.post("/ingest", response_model=dict[str, Any])
async def ingest(req: IngestPermitRequest):
    lead = await enrich_permit_to_lead(EnrichmentInputs(tenant_id=req.tenant_id, permit=req.permit))
    LEADS[lead.lead_id] = lead
    return {"ok": True, "lead": lead.model_dump()}


@router.get("/{lead_id}", response_model=dict[str, Any])
async def get_lead(lead_id: str):
    lead = LEADS.get(lead_id)
    if not lead:
        return {"ok": False, "error": "not_found"}
    return {"ok": True, "lead": lead.model_dump()}


