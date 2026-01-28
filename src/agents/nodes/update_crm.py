"""UpdateCRM node - placeholder for Phase 3 CRM integration."""

from __future__ import annotations

import csv
import logging
from pathlib import Path

from src.agents.state import AOROState
from src.agents.monitoring import append_workflow_event
from src.agents.infrastructure.crm_client import CRMClient
from src.core.config import get_settings
from src.core.observability import audit_event, traceable_fn

logger = logging.getLogger(__name__)


@traceable_fn("update_crm_agent")
async def update_crm_node(state: AOROState) -> AOROState:
    """
    Update CRM with booking (Phase 3 integration placeholder).
    
    For MVP, this node:
    - Logs the booking request
    - Marks booking as ready for CRM
    - Stores booking payload in state
    - Ends workflow
    
    In Phase 3, this will:
    - Call ServiceTitan MCP tool to create booking
    - Update CRM with lead information
    - Schedule appointment
    """
    booking_payload = state.get("booking_payload")
    lead_id = state.get("lead_id", "")
    company_name = state.get("company_name", "Unknown")
    
    if not booking_payload:
        logger.warning(f"No booking payload found for lead {lead_id}")
        return {
            **state,
            "crm_update_status": "failed",
            "crm_error": "No booking payload",
        }
    
    # Phase 3: Call MCP tool to create booking
    # For now: Log and mark as ready
    logger.info(f"Booking ready for CRM: {lead_id} ({company_name})")
    logger.info(f"Meeting preferences: {booking_payload.get('meeting_preferences', {})}")
    
    # Audit event
    audit_event(
        "crm_booking_ready",
        {
            "lead_id": lead_id,
            "company_name": company_name,
            "decision_maker": booking_payload.get("decision_maker", {}).get("email"),
            "meeting_type": booking_payload.get("meeting_type"),
        },
    )

    append_workflow_event(
        "booking_ready",
        {
            "lead_id": lead_id,
            "company_name": company_name,
            "decision_maker": booking_payload.get("decision_maker", {}).get("email"),
            "meeting_type": booking_payload.get("meeting_type"),
        },
    )

    settings = get_settings()
    if settings.crm_export_enabled:
        export_path = Path(settings.crm_export_csv_path)
        export_path.parent.mkdir(parents=True, exist_ok=True)
        headers = [
            "lead_id",
            "company_name",
            "decision_maker_email",
            "decision_maker_name",
            "meeting_type",
            "preferred_times",
            "preferred_dates",
            "meeting_format",
            "timezone",
            "created_at",
        ]
        row = {
            "lead_id": lead_id,
            "company_name": company_name,
            "decision_maker_email": booking_payload.get("decision_maker", {}).get("email"),
            "decision_maker_name": booking_payload.get("decision_maker", {}).get("full_name"),
            "meeting_type": booking_payload.get("meeting_type"),
            "preferred_times": ",".join(booking_payload.get("meeting_preferences", {}).get("preferred_times", [])),
            "preferred_dates": ",".join(booking_payload.get("meeting_preferences", {}).get("preferred_dates", [])),
            "meeting_format": booking_payload.get("meeting_preferences", {}).get("meeting_format"),
            "timezone": booking_payload.get("meeting_preferences", {}).get("timezone"),
            "created_at": booking_payload.get("created_at"),
        }
        if settings.crm_export_dedupe_enabled and export_path.exists():
            try:
                with export_path.open(newline="") as csvfile:
                    reader = csv.DictReader(csvfile)
                    existing = {
                        (
                            r.get("lead_id"),
                            r.get("decision_maker_email"),
                            r.get("meeting_type"),
                            r.get("preferred_times"),
                            r.get("preferred_dates"),
                        )
                        for r in reader
                    }
                key = (
                    row.get("lead_id"),
                    row.get("decision_maker_email"),
                    row.get("meeting_type"),
                    row.get("preferred_times"),
                    row.get("preferred_dates"),
                )
                if key in existing:
                    logger.info("Skipping duplicate booking export for lead %s", lead_id)
                    return {
                        **state,
                        "crm_booking_id": None,
                        "crm_update_status": "ready",
                        "crm_ready_at": None,
                        "workflow_complete": True,
                        "workflow_status": "booking_ready",
                    }
            except Exception as exc:
                logger.warning("Failed to dedupe booking export: %s", exc)
        file_exists = export_path.exists()
        with export_path.open("a", newline="") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=headers)
            if not file_exists:
                writer.writeheader()
            writer.writerow(row)

    crm_client = CRMClient(provider=settings.crm_provider)
    crm_result = await crm_client.create_booking(
        {
            "lead_id": lead_id,
            "company_name": company_name,
            "decision_maker": booking_payload.get("decision_maker", {}),
            "meeting_type": booking_payload.get("meeting_type"),
            "meeting_preferences": booking_payload.get("meeting_preferences", {}),
        }
    )
    
    crm_status = crm_result.get("status")
    crm_error = crm_result.get("error")
    crm_booking_id = crm_result.get("record_id")
    crm_update_status = "completed" if crm_status == "completed" else "ready"
    if crm_status == "error":
        crm_update_status = "failed"

    # Store booking in state for Phase 3 integration
    return {
        **state,
        "crm_booking_id": crm_booking_id,
        "crm_update_status": crm_update_status,
        "crm_error": crm_error,
        "crm_ready_at": None,
        "workflow_complete": True,
        "workflow_status": "booking_ready",
    }
