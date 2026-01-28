"""CKAN API client for municipal open data portals."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

import httpx

from src.signal_engine.api.base_api_client import BaseAPIPermitClient
from src.signal_engine.models import PermitData

logger = logging.getLogger(__name__)


class CKANPermitClient(BaseAPIPermitClient):
    """
    Client for fetching permit data from CKAN open data portals.
    
    CKAN is used by 50+ cities and government agencies including:
    - data.gov (federal)
    - Many state/local portals
    
    API Documentation: https://docs.ckan.org/
    """

    def __init__(
        self,
        portal_url: str,
        resource_id: str,
        field_mapping: dict[str, str] | None = None,
        api_key: str | None = None,
    ):
        """
        Initialize CKAN client.
        
        Args:
            portal_url: Base URL of the CKAN portal (e.g., "https://data.gov")
            resource_id: Resource/dataset identifier
            field_mapping: Optional mapping from PermitData fields to API field names
            api_key: Optional CKAN API key (for private datasets)
        """
        source_name = f"ckan_{portal_url.split('//')[1].split('.')[0]}"
        super().__init__(source_name)
        
        self.portal_url = portal_url.rstrip("/")
        self.resource_id = resource_id
        self.api_key = api_key
        
        # Default field mapping
        self.field_mapping = field_mapping or {
            "permit_id": "permit_number",
            "permit_type": "permit_type",
            "address": "address",
            "status": "status",
            "applicant_name": "applicant",
            "issued_date": "issue_date",
        }

    async def get_permits(
        self,
        days_back: int = 30,
        limit: int = 1000,
        **filters,
    ) -> list[PermitData]:
        """
        Fetch permits from CKAN API.
        
        Args:
            days_back: Number of days to look back
            limit: Maximum number of permits to return
            **filters: Additional CKAN query filters
        
        Returns:
            List of PermitData objects
        """
        start_date, end_date = self._calculate_date_range(days_back)
        
        # Build CKAN API request
        # Prefer datastore_search_sql for date ranges (more reliable than filters)
        date_field = self.field_mapping.get("issued_date")
        use_sql = bool(date_field)
        if use_sql:
            api_url = f"{self.portal_url}/api/3/action/datastore_search_sql"
        else:
            api_url = f"{self.portal_url}/api/3/action/datastore_search"
        
        # Build filters / SQL
        params: dict[str, Any] = {}
        if use_sql:
            # Escape field name with quotes (handles spaces)
            date_field_sql = f"\"{date_field}\""
            sql = (
                f'SELECT * FROM "{self.resource_id}" '
                f"WHERE {date_field_sql} >= '{start_date.strftime('%Y-%m-%d')}' "
                f"AND {date_field_sql} <= '{end_date.strftime('%Y-%m-%d')}' "
                f"ORDER BY {date_field_sql} DESC "
                f"LIMIT {limit}"
            )
            params["sql"] = sql
        else:
            # Fallback to datastore_search with filters
            ckan_filters: dict[str, Any] = {}
            ckan_filters.update(filters)
            params = {
                "resource_id": self.resource_id,
                "limit": limit,
            }
            if ckan_filters:
                params["filters"] = str(ckan_filters)
        
        # Add API key if provided
        headers = {}
        if self.api_key:
            headers["Authorization"] = self.api_key
        
        # Fetch data
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(api_url, params=params, headers=headers)
                response.raise_for_status()
                result = response.json()
                
                # CKAN returns data in result["result"]["records"]
                if result.get("success") and "result" in result:
                    data = result["result"].get("records", [])
                else:
                    logger.error(f"CKAN API error: {result.get('error', 'Unknown error')}")
                    return []
        except httpx.HTTPError as e:
            logger.error(f"CKAN API error for {self.portal_url}: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error fetching from CKAN: {e}")
            return []
        
        # Map API records to PermitData
        permits = []
        for record in data:
            permit = self._map_api_data_to_permit(record, self.field_mapping)
            if permit:
                permits.append(permit)
        
        logger.info(f"Fetched {len(permits)} permits from CKAN ({self.portal_url})")
        return permits
