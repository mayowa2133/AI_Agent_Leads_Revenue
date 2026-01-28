"""Base class for all API permit clients."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timedelta

from src.signal_engine.models import PermitData


class BaseAPIPermitClient(ABC):
    """Base class for all open data API permit clients."""

    def __init__(self, source_name: str):
        """
        Initialize API client.
        
        Args:
            source_name: Identifier for this API source (e.g., "socrata_charlotte")
        """
        self.source_name = source_name

    @abstractmethod
    async def get_permits(
        self,
        days_back: int = 30,
        limit: int = 1000,
        **filters,
    ) -> list[PermitData]:
        """
        Fetch permits from the API.
        
        Args:
            days_back: Number of days to look back
            limit: Maximum number of permits to return
            **filters: Additional filters specific to the API
        
        Returns:
            List of PermitData objects
        """
        pass

    def _normalize_date(self, date_str: str | None) -> datetime | None:
        """Normalize date string to datetime object."""
        if not date_str:
            return None
        
        # Try common date formats
        formats = [
            "%Y-%m-%dT%H:%M:%S.%f",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d",
            "%m/%d/%Y",
            "%m-%d-%Y",
            "%Y/%m/%d",
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        
        # If all fail, try parsing with dateutil (if available)
        try:
            from dateutil import parser
            return parser.parse(date_str)
        except ImportError:
            pass
        
        return None

    def _calculate_date_range(self, days_back: int) -> tuple[datetime, datetime]:
        """Calculate start and end dates for query."""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        return start_date, end_date

    def _map_api_data_to_permit(
        self,
        api_record: dict,
        field_mapping: dict[str, str],
    ) -> PermitData | None:
        """
        Map API record to PermitData model.
        
        Args:
            api_record: Raw API record (dict)
            field_mapping: Mapping from PermitData fields to API field names
                Example: {
                    "permit_id": "permit_number",
                    "permit_type": "permit_type",
                    "address": "address",
                    "status": "status",
                    "applicant_name": "applicant",
                    "issued_date": "issue_date",
                }
        
        Returns:
            PermitData object or None if mapping fails
        """
        try:
            # Extract fields using mapping
            permit_id = self._get_nested_value(api_record, field_mapping.get("permit_id", "permit_id"))
            permit_type = self._get_nested_value(api_record, field_mapping.get("permit_type", "permit_type"))
            address = self._get_nested_value(api_record, field_mapping.get("address", "address"))
            status = self._get_nested_value(api_record, field_mapping.get("status", "status"))
            
            # Required fields
            if not permit_id or not permit_type or not address or not status:
                return None
            
            # Optional fields
            applicant_name = self._get_nested_value(
                api_record, field_mapping.get("applicant_name")
            )
            applicant_name = self._normalize_applicant_name(applicant_name)
            issued_date_str = self._get_nested_value(api_record, field_mapping.get("issued_date"))
            issued_date = self._normalize_date(issued_date_str) if issued_date_str else None
            
            building_type = self._get_nested_value(api_record, field_mapping.get("building_type"))
            detail_url = self._get_nested_value(api_record, field_mapping.get("detail_url"))
            
            return PermitData(
                source=self.source_name,
                permit_id=str(permit_id),
                permit_type=str(permit_type),
                address=str(address),
                building_type=str(building_type) if building_type else None,
                status=str(status),
                applicant_name=str(applicant_name) if applicant_name else None,
                issued_date=issued_date,
                detail_url=str(detail_url) if detail_url else None,
            )
        except Exception as e:
            # Log error but continue processing
            print(f"Warning: Failed to map API record to PermitData: {e}")
            return None

    def _get_nested_value(self, data: dict, key: str | None) -> str | None:
        """Get value from dict, supporting nested keys (e.g., "address.street")."""
        if not key:
            return None
        
        keys = key.split(".")
        value = data
        
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return None
            
            if value is None:
                return None
        
        return str(value) if value is not None else None

    def _normalize_applicant_name(self, name: str | None) -> str | None:
        """
        Normalize applicant names from API data.

        If the value is "Person, Company", prefer the company part when it looks
        like a business name so domain lookup works better.
        """
        if not name:
            return None

        cleaned = " ".join(str(name).strip().split())
        if not cleaned:
            return None

        # If there are separators, try to extract the company-like segment.
        separators = [",", " - ", " / ", " | ", ";"]
        if any(sep in cleaned for sep in separators):
            # Split on common separators and keep non-empty parts.
            parts = []
            for sep in separators:
                if sep in cleaned:
                    parts = [p.strip() for p in cleaned.split(sep) if p.strip()]
                    break
            if not parts and "," in cleaned:
                parts = [p.strip() for p in cleaned.split(",") if p.strip()]

            for part in parts:
                if self._looks_like_company(part):
                    return part

            # If we split and the last segment is longer, prefer it.
            if parts:
                parts.sort(key=len, reverse=True)
                return parts[0]

        return cleaned

    @staticmethod
    def _looks_like_company(text: str) -> bool:
        """Heuristic check for organization names."""
        lower = text.lower()
        keywords = [
            "llc",
            "inc",
            "ltd",
            "llp",
            "pllc",
            "corp",
            "co",
            "company",
            "group",
            "partners",
            "associates",
            "architect",
            "architects",
            "engineering",
            "engineers",
            "construction",
            "builders",
            "plumbing",
            "electric",
            "electrical",
            "mechanical",
            "hvac",
            "roofing",
            "sprinkler",
            "alarm",
            "fire",
            "services",
            "systems",
            "design",
            "consulting",
            "development",
            "properties",
            "realty",
            "contractor",
            "contractors",
        ]
        if any(keyword in lower for keyword in keywords):
            return True

        # Suffix check (last token)
        suffixes = {"llc", "inc", "ltd", "llp", "pllc", "corp", "co", "pc"}
        last_token = lower.split()[-1] if lower.split() else ""
        return last_token in suffixes
