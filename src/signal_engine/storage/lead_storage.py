"""Storage layer for enriched leads using JSON file storage."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING

from src.signal_engine.models import EnrichedLead

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class LeadStorage:
    """
    Storage for enriched leads using JSON file storage.

    Matches Phase 1.1 and 1.2 approach for consistency. Can be upgraded to
    database later if needed.
    """

    def __init__(self, *, storage_file: Path | str | None = None):
        """
        Initialize lead storage.

        Args:
            storage_file: Path to JSON storage file (default: data/enriched_leads.json)
        """
        if storage_file is None:
            storage_file = Path("data/enriched_leads.json")
        elif isinstance(storage_file, str):
            storage_file = Path(storage_file)

        self.storage_file = storage_file
        self.storage_file.parent.mkdir(parents=True, exist_ok=True)

    def save_lead(self, lead: EnrichedLead) -> None:
        """
        Save an enriched lead to storage.

        Args:
            lead: Enriched lead to save
        """
        leads = self.load_all()

        # Deduplicate by lead_id (last write wins)
        leads_dict = {l["lead_id"]: l for l in leads}
        leads_dict[lead.lead_id] = lead.model_dump(mode="json")

        # Convert datetime to ISO format for JSON
        for lead_data in leads_dict.values():
            for key, value in lead_data.items():
                if isinstance(value, datetime):
                    lead_data[key] = value.isoformat()
                elif isinstance(value, dict):
                    # Handle nested datetime fields (e.g., in permit, company)
                    for nested_key, nested_value in value.items():
                        if isinstance(nested_value, datetime):
                            value[nested_key] = nested_value.isoformat()

        # Save to file
        self.storage_file.write_text(json.dumps(list(leads_dict.values()), indent=2))
        logger.debug(f"Saved enriched lead: {lead.lead_id}")

    def save_leads(self, leads: list[EnrichedLead]) -> None:
        """
        Save multiple enriched leads.

        Args:
            leads: List of enriched leads to save
        """
        for lead in leads:
            self.save_lead(lead)

    def load_all(self) -> list[dict]:
        """
        Load all enriched leads from storage.

        Returns:
            List of lead dictionaries
        """
        if not self.storage_file.exists():
            return []

        try:
            content = self.storage_file.read_text()
            if not content.strip():
                return []

            leads = json.loads(content)
            return leads if isinstance(leads, list) else []
        except Exception as e:
            logger.error(f"Error loading enriched leads: {e}", exc_info=True)
            return []

    def get_lead(self, lead_id: str) -> EnrichedLead | None:
        """
        Get a specific enriched lead by ID.

        Args:
            lead_id: Lead ID to retrieve

        Returns:
            EnrichedLead or None if not found
        """
        leads = self.load_all()
        for lead_data in leads:
            if lead_data.get("lead_id") == lead_id:
                return self._dict_to_lead(lead_data)
        return None

    def get_by_tenant(self, tenant_id: str) -> list[EnrichedLead]:
        """
        Get all leads for a specific tenant.

        Args:
            tenant_id: Tenant ID to filter by

        Returns:
            List of EnrichedLead objects for the tenant
        """
        leads = self.load_all()
        results = []

        for lead_data in leads:
            if lead_data.get("tenant_id") == tenant_id:
                results.append(self._dict_to_lead(lead_data))

        return results

    def get_by_permit_id(self, source: str, permit_id: str) -> EnrichedLead | None:
        """
        Get lead by permit source and ID.

        Args:
            source: Permit source (e.g., "mecklenburg", "san_antonio")
            permit_id: Permit ID

        Returns:
            EnrichedLead or None if not found
        """
        leads = self.load_all()

        for lead_data in leads:
            permit_data = lead_data.get("permit", {})
            if permit_data.get("source") == source and permit_data.get("permit_id") == permit_id:
                return self._dict_to_lead(lead_data)

        return None

    def get_recent(self, days: int = 30) -> list[EnrichedLead]:
        """
        Get leads created within the last N days.

        Args:
            days: Number of days to look back

        Returns:
            List of recent EnrichedLead objects
        """
        leads = self.load_all()
        results = []
        cutoff_date = datetime.now() - timedelta(days=days)

        for lead_data in leads:
            created_str = lead_data.get("created_at")
            if created_str:
                try:
                    created_date = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
                    if created_date >= cutoff_date:
                        results.append(self._dict_to_lead(lead_data))
                except Exception:
                    pass

        return results

    def _dict_to_lead(self, data: dict) -> EnrichedLead:
        """
        Convert dictionary to EnrichedLead object.

        Args:
            data: Dictionary with lead data

        Returns:
            EnrichedLead object
        """
        # Convert ISO date strings back to datetime
        for date_field in ["created_at"]:
            if date_field in data and data[date_field]:
                try:
                    data[date_field] = datetime.fromisoformat(
                        data[date_field].replace("Z", "+00:00")
                    )
                except Exception:
                    pass

        # Handle nested datetime fields in permit
        if "permit" in data and isinstance(data["permit"], dict):
            for date_field in ["issued_date", "last_seen_at"]:
                if date_field in data["permit"] and data["permit"][date_field]:
                    try:
                        data["permit"][date_field] = datetime.fromisoformat(
                            data["permit"][date_field].replace("Z", "+00:00")
                        )
                    except Exception:
                        pass

        return EnrichedLead(**data)

