"""Unified permit ingestion layer for scrapers and APIs."""

from __future__ import annotations

from enum import Enum
from typing import Any

from src.signal_engine.api.base_api_client import BaseAPIPermitClient
from src.signal_engine.api.ckan_client import CKANPermitClient
from src.signal_engine.api.custom_api_client import CustomAPIPermitClient
from src.signal_engine.api.socrata_client import SocrataPermitClient
from src.signal_engine.models import PermitData
from src.signal_engine.scrapers.base_scraper import BaseScraper


class PermitSourceType(str, Enum):
    """Type of permit source."""

    SCRAPER = "scraper"
    SOCRATA_API = "socrata_api"
    CKAN_API = "ckan_api"
    CUSTOM_API = "custom_api"


class PermitSource:
    """Configuration for a permit source (scraper or API)."""

    def __init__(
        self,
        source_type: PermitSourceType,
        city: str,
        source_id: str,
        config: dict[str, Any],
    ):
        """
        Initialize permit source.
        
        Args:
            source_type: Type of source (scraper, API, etc.)
            city: City name
            source_id: Unique identifier for this source
            config: Source-specific configuration
        """
        self.source_type = source_type
        self.city = city
        self.source_id = source_id
        self.config = config


class UnifiedPermitIngestion:
    """
    Unified interface for ingesting permits from any source.
    
    Supports:
    - Scrapers (Playwright-based)
    - Socrata APIs
    - CKAN APIs
    - Custom APIs
    """

    def __init__(self):
        """Initialize unified ingestion layer."""
        pass

    async def ingest_permits(
        self,
        source: PermitSource,
        days_back: int = 30,
        limit: int = 1000,
    ) -> list[PermitData]:
        """
        Ingest permits from any source.
        
        Args:
            source: PermitSource configuration
            days_back: Number of days to look back
            limit: Maximum number of permits to return
        
        Returns:
            List of PermitData objects
        """
        if source.source_type == PermitSourceType.SCRAPER:
            return await self._ingest_from_scraper(source, days_back, limit)
        elif source.source_type == PermitSourceType.SOCRATA_API:
            return await self._ingest_from_socrata(source, days_back, limit)
        elif source.source_type == PermitSourceType.CKAN_API:
            return await self._ingest_from_ckan(source, days_back, limit)
        elif source.source_type == PermitSourceType.CUSTOM_API:
            return await self._ingest_from_custom_api(source, days_back, limit)
        else:
            raise ValueError(f"Unknown source type: {source.source_type}")

    async def _ingest_from_scraper(
        self,
        source: PermitSource,
        days_back: int,
        limit: int,
    ) -> list[PermitData]:
        """Ingest permits from a scraper."""
        from src.signal_engine.discovery.portal_discovery import PortalInfo, PortalType
        from src.signal_engine.scrapers.registry import ScraperRegistry

        # Create PortalInfo from config
        portal_type_str = source.config.get("portal_type", "accela")
        try:
            portal_type = PortalType(portal_type_str.upper())
        except ValueError:
            portal_type = PortalType.ACCELA  # Default
        
        portal_info = PortalInfo(
            url=source.config.get("url", ""),
            city=source.city,
            system_type=portal_type,
            confidence_score=1.0,
            config=source.config,
        )
        
        # Create scraper using registry
        scraper = ScraperRegistry.create_scraper(
            portal_info,
            days_back=days_back,
            **{k: v for k, v in source.config.items() if k not in ["portal_type", "url"]},
        )
        
        # Scrape permits
        permits = await scraper.scrape()
        
        # Apply limit
        return permits[:limit]

    async def _ingest_from_socrata(
        self,
        source: PermitSource,
        days_back: int,
        limit: int,
    ) -> list[PermitData]:
        """Ingest permits from Socrata API."""
        client = SocrataPermitClient(
            portal_url=source.config["portal_url"],
            dataset_id=source.config["dataset_id"],
            field_mapping=source.config.get("field_mapping"),
            app_token=source.config.get("app_token"),
        )
        
        return await client.get_permits(days_back=days_back, limit=limit)

    async def _ingest_from_ckan(
        self,
        source: PermitSource,
        days_back: int,
        limit: int,
    ) -> list[PermitData]:
        """Ingest permits from CKAN API."""
        client = CKANPermitClient(
            portal_url=source.config["portal_url"],
            resource_id=source.config["resource_id"],
            field_mapping=source.config.get("field_mapping"),
            api_key=source.config.get("api_key"),
        )
        
        return await client.get_permits(days_back=days_back, limit=limit)

    async def _ingest_from_custom_api(
        self,
        source: PermitSource,
        days_back: int,
        limit: int,
    ) -> list[PermitData]:
        """Ingest permits from custom API."""
        client = CustomAPIPermitClient(
            api_url=source.config["api_url"],
            endpoint=source.config["endpoint"],
            field_mapping=source.config["field_mapping"],
            method=source.config.get("method", "GET"),
            auth=source.config.get("auth"),
        )
        
        return await client.get_permits(days_back=days_back, limit=limit)
