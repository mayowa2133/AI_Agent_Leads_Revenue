from __future__ import annotations

from datetime import datetime
from typing import Literal, TypedDict


class AOROState(TypedDict, total=False):
    # Lead Information
    lead_id: str
    tenant_id: str
    company_name: str
    decision_maker: dict
    permit_data: dict

    # Research Results
    compliance_gaps: list[str]
    applicable_codes: list[str]
    case_studies: list[dict]

    # Communication State
    outreach_draft: str
    outreach_channel: Literal["email", "whatsapp", "voice"]
    response_history: list[dict]

    # Workflow State
    qualification_score: float
    current_objection: str | None
    human_approved: bool

    # CRM State
    crm_booking_id: str | None
    appointment_datetime: datetime | None


