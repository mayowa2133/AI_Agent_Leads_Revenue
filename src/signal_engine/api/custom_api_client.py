"""Custom JSON API client for municipal permit APIs."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

import httpx

from src.signal_engine.api.base_api_client import BaseAPIPermitClient
from src.signal_engine.models import PermitData

logger = logging.getLogger(__name__)


class CustomAPIPermitClient(BaseAPIPermitClient):
    """
    Generic client for custom municipal permit APIs.
    
    Many cities have custom REST APIs for permit data:
    - data.sanantonio.gov/api
    - data.austintexas.gov/api
    - And many more...
    
    This client provides a flexible interface for various API formats.
    """

    def __init__(
        self,
        api_url: str,
        endpoint: str,
        field_mapping: dict[str, str],
        method: str = "GET",
        auth: dict[str, str] | None = None,
    ):
        """
        Initialize custom API client.
        
        Args:
            api_url: Base URL of the API (e.g., "https://data.sanantonio.gov")
            endpoint: API endpoint path (e.g., "/api/permits" or "/permits")
            field_mapping: Mapping from PermitData fields to API field names
                Required - custom APIs vary widely
            method: HTTP method ("GET" or "POST")
            auth: Optional authentication (e.g., {"type": "bearer", "token": "..."})
        """
        source_name = f"custom_api_{api_url.split('//')[1].split('.')[0]}"
        super().__init__(source_name)
        
        self.api_url = api_url.rstrip("/")
        self.endpoint = endpoint.lstrip("/")
        self.field_mapping = field_mapping
        self.method = method.upper()
        self.auth = auth

    async def get_permits(
        self,
        days_back: int = 30,
        limit: int = 1000,
        **filters,
    ) -> list[PermitData]:
        """
        Fetch permits from custom API.
        
        Args:
            days_back: Number of days to look back
            limit: Maximum number of permits to return
            **filters: Additional API-specific filters
        
        Returns:
            List of PermitData objects
        """
        start_date, end_date = self._calculate_date_range(days_back)
        
        # Build request URL
        full_url = f"{self.api_url}/{self.endpoint}"
        
        # Build request parameters/body
        params: dict[str, Any] = {}
        json_data: dict[str, Any] | None = None
        
        # Add date filters
        if "start_date" in self.field_mapping or "date" in self.field_mapping:
            params["start_date"] = start_date.strftime("%Y-%m-%d")
            params["end_date"] = end_date.strftime("%Y-%m-%d")
        
        # Add limit
        params["limit"] = limit
        
        # Add custom filters
        params.update(filters)
        
        # Build headers
        headers: dict[str, str] = {
            "Accept": "application/json",
        }
        
        # Add authentication
        if self.auth:
            auth_type = self.auth.get("type", "bearer").lower()
            if auth_type == "bearer":
                headers["Authorization"] = f"Bearer {self.auth.get('token')}"
            elif auth_type == "apikey":
                headers["X-API-Key"] = self.auth.get("token", "")
            elif auth_type == "basic":
                # Basic auth would need username/password
                pass
        
        # Make request
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                if self.method == "GET":
                    response = await client.get(full_url, params=params, headers=headers)
                elif self.method == "POST":
                    json_data = params  # Use params as JSON body for POST
                    response = await client.post(full_url, json=json_data, headers=headers)
                else:
                    logger.error(f"Unsupported HTTP method: {self.method}")
                    return []
                
                response.raise_for_status()
                result = response.json()
        except httpx.HTTPError as e:
            logger.error(f"Custom API error for {self.api_url}: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error fetching from custom API: {e}")
            return []
        
        # Handle different response formats
        # Some APIs return data directly, others wrap it
        if isinstance(result, list):
            data = result
        elif isinstance(result, dict):
            # Try common keys
            data = (
                result.get("data")
                or result.get("results")
                or result.get("permits")
                or result.get("records")
                or [result]  # Single record
            )
        else:
            logger.error(f"Unexpected API response format: {type(result)}")
            return []
        
        # Map API records to PermitData
        permits = []
        for record in data:
            if isinstance(record, dict):
                permit = self._map_api_data_to_permit(record, self.field_mapping)
                if permit:
                    permits.append(permit)
        
        logger.info(f"Fetched {len(permits)} permits from custom API ({self.api_url})")
        return permits
