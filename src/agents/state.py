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
    compliance_urgency_score: float  # Phase 2.1: Compliance urgency (0.0 - 1.0)

    # Communication State
    outreach_draft: str
    outreach_channel: Literal["email", "whatsapp", "voice"]
    response_history: list[dict]
    outreach_sent_at: str | None  # Phase 2.1: Timestamp when outreach was sent
    
    # Phase 2.2: Response Handling
    response_received: bool  # True if response was received
    response_timeout: bool  # True if timeout reached
    response_data: dict | None  # Response data from webhook
    response_classification: str | None  # "positive", "objection", "no_response", "unsubscribe"
    response_sentiment: str | None  # "positive", "neutral", "negative"
    interest_level: str | None  # "high", "medium", "low", "none"
    extracted_objections: list[str]  # List of objections found in response
    waiting_for_response: bool  # True if currently waiting

    # Workflow State
    qualification_score: float
    current_objection: str | None
    human_approved: bool
    
    # Phase 2.3: Follow-ups & Objection Management
    followup_count: int  # Number of follow-up attempts
    followup_scheduled_at: str | None  # ISO timestamp for next follow-up
    workflow_complete: bool  # True if workflow is complete
    workflow_status: str | None  # "no_response", "booking_ready", "objection_loop_max", etc.
    objection_handling_count: int  # Number of objection handling cycles
    
    # Phase 2.3: Meeting Booking
    booking_payload: dict | None  # Booking data for CRM
    booking_ready: bool  # True if booking is ready for CRM
    meeting_preferences: dict | None  # Extracted meeting preferences
    
    # Phase 2.3: CRM Integration
    crm_update_status: str | None  # "ready", "failed", "completed"
    crm_ready_at: str | None  # ISO timestamp when CRM update was ready

    # CRM State
    crm_booking_id: str | None
    appointment_datetime: datetime | None


