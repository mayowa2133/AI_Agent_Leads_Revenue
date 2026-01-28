"""Socrata API client for municipal open data portals."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

import httpx

from src.signal_engine.api.base_api_client import BaseAPIPermitClient
from src.signal_engine.models import PermitData

logger = logging.getLogger(__name__)


class SocrataPermitClient(BaseAPIPermitClient):
    """
    Client for fetching permit data from Socrata open data portals.
    
    Socrata is used by 100+ cities including:
    - Charlotte, NC (data.cityofcharlotte.org)
    - Seattle, WA (data.seattle.gov)
    - New York, NY (data.cityofnewyork.us)
    - And many more...
    
    API Documentation: https://dev.socrata.com/
    """

    def __init__(
        self,
        portal_url: str,
        dataset_id: str,
        field_mapping: dict[str, str] | None = None,
        app_token: str | None = None,
    ):
        """
        Initialize Socrata client.
        
        Args:
            portal_url: Base URL of the Socrata portal (e.g., "https://data.cityofcharlotte.org")
            dataset_id: Dataset identifier (e.g., "abcd-1234")
            field_mapping: Optional mapping from PermitData fields to API field names
                If None, uses default mapping
            app_token: Optional Socrata app token (for higher rate limits)
        """
        source_name = f"socrata_{portal_url.split('//')[1].split('.')[0]}"
        super().__init__(source_name)
        
        self.portal_url = portal_url.rstrip("/")
        self.dataset_id = dataset_id
        self.app_token = app_token
        
        # Default field mapping (can be overridden)
        self.field_mapping = field_mapping or {
            "permit_id": "permit_number",
            "permit_type": "permit_type",
            "address": "address",
            "status": "status",
            "applicant_name": "applicant",
            "issued_date": "issue_date",
        }
        
        # Common field name variations to try
        self.field_variations = {
            "permit_id": ["permit_number", "permit_id", "permit_num", "id", "record_id"],
            "permit_type": ["permit_type", "type", "permit_category", "category"],
            "address": ["address", "location", "site_address", "property_address"],
            "status": ["status", "permit_status", "current_status"],
            "applicant_name": ["applicant", "applicant_name", "contractor", "owner"],
            "issued_date": ["issue_date", "issued_date", "date_issued", "permit_date"],
        }

    async def get_permits(
        self,
        days_back: int = 30,
        limit: int = 1000,
        **filters,
    ) -> list[PermitData]:
        """
        Fetch permits from Socrata API.
        
        Args:
            days_back: Number of days to look back
            limit: Maximum number of permits to return
            **filters: Additional Socrata query filters
        
        Returns:
            List of PermitData objects
        """
        start_date, end_date = self._calculate_date_range(days_back)
        
        # Build Socrata query
        # Socrata uses SoQL (Socrata Query Language)
        where_clauses = []
        
        # Date filter (if issued_date field exists and is not None)
        date_field = self.field_mapping.get("issued_date")
        if date_field:
            where_clauses.append(
                f"{date_field} >= '{start_date.strftime('%Y-%m-%d')}'"
            )
            where_clauses.append(
                f"{date_field} <= '{end_date.strftime('%Y-%m-%d')}'"
            )
        
        # Add custom filters
        for key, value in filters.items():
            if isinstance(value, str):
                where_clauses.append(f"{key} = '{value}'")
            else:
                where_clauses.append(f"{key} = {value}")
        
        where_clause = " AND ".join(where_clauses) if where_clauses else None
        
        # Build API URL
        api_url = f"{self.portal_url}/resource/{self.dataset_id}.json"
        
        params: dict[str, Any] = {
            "$limit": limit,
        }
        
        # Add order by date if available
        date_field = self.field_mapping.get("issued_date")
        if date_field:
            params["$order"] = f"{date_field} DESC"
        
        if where_clause:
            params["$where"] = where_clause
        
        # Add app token if provided
        headers = {}
        if self.app_token:
            headers["X-App-Token"] = self.app_token
        
        # Fetch data
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(api_url, params=params, headers=headers)
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPError as e:
            logger.error(f"Socrata API error for {self.portal_url}: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error fetching from Socrata: {e}")
            return []
        
        # Map API records to PermitData
        permits = []
        for record in data:
            permit = self._map_api_data_to_permit(record, self.field_mapping)
            if permit:
                permits.append(permit)
        
        logger.info(f"Fetched {len(permits)} permits from Socrata ({self.portal_url})")
        return permits

    def discover_field_mapping(self, sample_record: dict) -> dict[str, str]:
        """
        Auto-discover field mapping from a sample API record.
        
        This helps when field names vary between cities.
        
        Args:
            sample_record: Sample record from the API
        
        Returns:
            Field mapping dictionary
        """
        mapping = {}
        record_keys = [k.lower() for k in sample_record.keys()]
        
        for permit_field, variations in self.field_variations.items():
            for variation in variations:
                # Try exact match (case-insensitive)
                for key in record_keys:
                    if key == variation.lower():
                        mapping[permit_field] = key
                        break
                
                if permit_field in mapping:
                    break
        
        return mapping
