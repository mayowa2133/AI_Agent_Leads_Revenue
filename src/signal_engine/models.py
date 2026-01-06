from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class PermitData(BaseModel):
    source: str = Field(..., description="Portal/source identifier, e.g. 'accela', 'city_x_portal'.")
    permit_id: str
    permit_type: str
    address: str
    building_type: str | None = None
    status: str
    applicant_name: str | None = None
    issued_date: datetime | None = None
    last_seen_at: datetime = Field(default_factory=datetime.utcnow)
    detail_url: str | None = None


class DecisionMaker(BaseModel):
    full_name: str | None = None
    title: str | None = None
    email: str | None = None
    phone: str | None = None
    linkedin_url: str | None = None


class Company(BaseModel):
    name: str
    website: str | None = None
    employee_count: int | None = None
    revenue_estimate: str | None = None
    industry: str | None = None


class ComplianceContext(BaseModel):
    jurisdiction: str | None = None
    applicable_codes: list[str] = []
    inspection_history: list[dict] = []
    triggers: list[str] = []


class EnrichedLead(BaseModel):
    lead_id: str
    tenant_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

    company: Company
    decision_maker: DecisionMaker | None = None
    permit: PermitData
    compliance: ComplianceContext = Field(default_factory=ComplianceContext)

    outreach_channel_hint: Literal["email", "whatsapp", "voice"] = "email"


