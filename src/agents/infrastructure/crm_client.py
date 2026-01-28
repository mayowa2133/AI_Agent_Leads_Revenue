"""CRM client integrations (free-first)."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from src.core.config import get_settings

logger = logging.getLogger(__name__)


class CRMClient:
    def __init__(self, *, provider: str | None = None):
        settings = get_settings()
        self.provider = (provider or settings.crm_provider or "csv").lower()
        self.settings = settings

    async def create_booking(self, payload: dict[str, Any]) -> dict[str, Any]:
        if self.provider == "airtable":
            return await self._create_airtable_record(payload)
        # CSV provider is handled separately in UpdateCRM
        return {"status": "skipped", "provider": self.provider}

    async def _create_airtable_record(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not self.settings.airtable_api_key:
            return {"status": "error", "provider": "airtable", "error": "AIRTABLE_API_KEY not set"}
        if not self.settings.airtable_base_id:
            return {"status": "error", "provider": "airtable", "error": "AIRTABLE_BASE_ID not set"}

        table = self.settings.airtable_table_name or "Bookings"
        url = f"https://api.airtable.com/v0/{self.settings.airtable_base_id}/{table}"
        headers = {
            "Authorization": f"Bearer {self.settings.airtable_api_key}",
            "Content-Type": "application/json",
        }

        decision_maker = payload.get("decision_maker") or {}
        meeting_prefs = payload.get("meeting_preferences") or {}
        fields = {
            "Lead ID": payload.get("lead_id"),
            "Company": payload.get("company_name"),
            "Decision Maker Email": decision_maker.get("email"),
            "Decision Maker Name": decision_maker.get("full_name"),
            "Meeting Type": payload.get("meeting_type"),
            "Preferred Times": ", ".join(meeting_prefs.get("preferred_times") or []),
            "Preferred Dates": ", ".join(meeting_prefs.get("preferred_dates") or []),
            "Meeting Format": meeting_prefs.get("meeting_format"),
            "Timezone": meeting_prefs.get("timezone"),
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(url, headers=headers, json={"fields": fields})
            if resp.status_code >= 400:
                return {
                    "status": "error",
                    "provider": "airtable",
                    "error": f"{resp.status_code}: {resp.text}",
                }
            record_id = (resp.json() or {}).get("id")
            logger.info("Airtable record created: %s", record_id)
            return {"status": "completed", "provider": "airtable", "record_id": record_id}
        except Exception as exc:
            logger.error("Airtable create failed: %s", exc, exc_info=True)
            return {"status": "error", "provider": "airtable", "error": str(exc)}
