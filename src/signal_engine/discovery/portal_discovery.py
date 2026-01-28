"""Portal discovery service using Google Custom Search API."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any

import httpx

from src.core.config import get_settings

logger = logging.getLogger(__name__)


class PortalType(str, Enum):
    """Types of permit portal systems."""

    ACCELA = "accela"
    VIEWPOINT = "viewpoint"
    ENERGOV = "energov"
    MECKLENBURG = "mecklenburg"  # Custom WebPermit system
    CUSTOM = "custom"
    UNKNOWN = "unknown"


@dataclass
class PortalInfo:
    """Information about a discovered permit portal."""

    url: str
    city: str
    system_type: PortalType
    confidence_score: float
    title: str | None = None
    snippet: str | None = None
    validated: bool = False
    config: dict[str, Any] | None = None

    def __post_init__(self):
        """Set default config based on system type."""
        if self.config is None:
            self.config = self._get_default_config()

    def _get_default_config(self) -> dict[str, Any]:
        """Get default configuration for portal system type."""
        if self.system_type == PortalType.ACCELA:
            # Extract city code from URL if possible
            # URL pattern: https://aca-prod.accela.com/{CITY_CODE}/Cap/
            city_code = self._extract_city_code()
            return {
                "city_code": city_code,
                "module": "Fire",
                "record_type": "Fire Alarm",
            }
        elif self.system_type == PortalType.VIEWPOINT:
            return {
                "base_url": self.url,
            }
        elif self.system_type == PortalType.ENERGOV:
            return {
                "base_url": self.url,
            }
        return {}

    def _extract_city_code(self) -> str | None:
        """Extract city code from Accela URL."""
        # Example: https://aca-prod.accela.com/COSA/Cap/ -> COSA
        try:
            parts = self.url.split("/")
            for i, part in enumerate(parts):
                if part == "accela.com" and i + 1 < len(parts):
                    return parts[i + 1]
        except Exception:
            pass
        return None


class PortalDiscoveryService:
    """Service for discovering municipal permit portals using Google Custom Search."""

    def __init__(self):
        """Initialize portal discovery service."""
        self.settings = get_settings()
        self.api_key = self.settings.google_custom_search_api_key
        self.engine_id = self.settings.google_custom_search_engine_id
        self.base_url = "https://www.googleapis.com/customsearch/v1"

    async def discover_portals(
        self,
        cities: list[str],
        max_results_per_city: int = 10,
    ) -> list[PortalInfo]:
        """
        Discover permit portals for given cities.

        Args:
            cities: List of city names to search for
            max_results_per_city: Maximum results to return per city

        Returns:
            List of PortalInfo with discovered portals
        """
        if not self.api_key or not self.engine_id:
            logger.warning(
                "Google Custom Search API key or Engine ID not configured. "
                "Skipping portal discovery."
            )
            return []

        all_portals: list[PortalInfo] = []

        for city in cities:
            logger.info(f"Discovering portals for {city}...")
            portals = await self._discover_city_portals(city, max_results_per_city)
            all_portals.extend(portals)
            logger.info(f"Found {len(portals)} portals for {city}")

        # Deduplicate by URL
        seen_urls = set()
        unique_portals = []
        for portal in all_portals:
            normalized_url = self._normalize_url(portal.url)
            if normalized_url not in seen_urls:
                seen_urls.add(normalized_url)
                unique_portals.append(portal)

        logger.info(f"Total unique portals discovered: {len(unique_portals)}")
        return unique_portals

    async def _discover_city_portals(
        self,
        city: str,
        max_results: int = 10,
    ) -> list[PortalInfo]:
        """Discover portals for a single city."""
        portals: list[PortalInfo] = []

        # Search queries to try
        search_queries = [
            f'building permit search "{city}"',
            f'permit database "{city}" site:.gov',
            f'building permits "{city}" site:.gov',
            f'accela "{city}"',
            f'viewpoint "{city}"',
            f'permit portal "{city}"',
            f'construction permits "{city}"',
        ]

        for query in search_queries:
            try:
                results = await self._search_google(query, max_results=5)
                for result in results:
                    portal = self._parse_search_result(result, city)
                    if portal:
                        portals.append(portal)
            except Exception as e:
                logger.warning(f"Search failed for query '{query}': {e}")
                continue

        return portals[:max_results]

    async def _search_google(
        self,
        query: str,
        max_results: int = 10,
    ) -> list[dict[str, Any]]:
        """Search Google Custom Search API."""
        async with httpx.AsyncClient() as client:
            params = {
                "key": self.api_key,
                "cx": self.engine_id,
                "q": query,
                "num": min(max_results, 10),  # Google API max is 10 per request
            }

            response = await client.get(self.base_url, params=params)
            response.raise_for_status()

            data = response.json()
            return data.get("items", [])

    def _parse_search_result(
        self,
        result: dict[str, Any],
        city: str,
    ) -> PortalInfo | None:
        """Parse Google search result into PortalInfo."""
        url = result.get("link", "")
        title = result.get("title", "")
        snippet = result.get("snippet", "")

        # Filter out non-permit-related results
        if not self._is_permit_portal(url, title, snippet):
            return None

        # Classify portal system type
        system_type = self._classify_portal(url, title, snippet)

        # Calculate confidence score
        confidence = self._calculate_confidence(url, title, snippet, system_type)

        return PortalInfo(
            url=url,
            city=city,
            system_type=system_type,
            confidence_score=confidence,
            title=title,
            snippet=snippet,
        )

    def _is_permit_portal(
        self,
        url: str,
        title: str,
        snippet: str,
    ) -> bool:
        """Check if result is likely a permit portal."""
        text = f"{url} {title} {snippet}".lower()

        # Positive indicators
        permit_keywords = [
            "permit",
            "building permit",
            "construction permit",
            "fire permit",
            "accela",
            "viewpoint",
            "energov",
            "permit search",
            "permit database",
        ]

        # Negative indicators (exclude these)
        exclude_keywords = [
            "news",
            "article",
            "blog",
            "pdf",
            "download",
            ".pdf",
        ]

        # Check for exclude keywords first
        if any(keyword in text for keyword in exclude_keywords):
            return False

        # Check for permit keywords
        if any(keyword in text for keyword in permit_keywords):
            return True

        # Check for .gov domain (more likely to be official)
        if ".gov" in url or ".us" in url:
            return True

        return False

    def _classify_portal(
        self,
        url: str,
        title: str,
        snippet: str,
    ) -> PortalType:
        """Classify portal system type based on URL and content."""
        text = f"{url} {title} {snippet}".lower()
        url_lower = url.lower()

        # Accela patterns (most common - 100+ cities)
        if "accela.com" in url_lower or "accela" in text:
            return PortalType.ACCELA

        # ViewPoint patterns
        if "viewpointcloud.com" in url_lower or "viewpoint" in text:
            return PortalType.VIEWPOINT

        # EnerGov patterns
        if "energov.com" in url_lower or "energov" in text:
            return PortalType.ENERGOV

        # Mecklenburg pattern (specific WebPermit system)
        if "mecklenburgcountync.gov" in url_lower or "webpermit" in text:
            return PortalType.MECKLENBURG

        # NYC Building Information System (BIS)
        if "nyc.gov/bis" in url_lower or "bisweb" in url_lower or "building information system" in text:
            return PortalType.CUSTOM  # NYC has custom system

        # Chicago Building Records
        if "chicago.gov" in url_lower and ("building" in text or "permit" in text):
            return PortalType.CUSTOM  # Chicago has custom system

        # Common patterns that indicate custom systems
        if any(pattern in url_lower for pattern in [
            "/permits/",
            "/permit",
            "/building",
            "/construction",
            "permit-search",
            "permit-database",
            "building-permit",
        ]):
            return PortalType.CUSTOM

        return PortalType.UNKNOWN

    def _calculate_confidence(
        self,
        url: str,
        title: str,
        snippet: str,
        system_type: PortalType,
    ) -> float:
        """Calculate confidence score for portal discovery."""
        score = 0.0

        # Base score for being a permit portal
        if self._is_permit_portal(url, title, snippet):
            score += 0.3

        # Higher score for known system types
        if system_type != PortalType.UNKNOWN:
            score += 0.3

        # Higher score for .gov domains
        if ".gov" in url or ".us" in url:
            score += 0.2

        # Higher score for specific permit keywords in title
        title_lower = title.lower()
        if any(kw in title_lower for kw in ["permit", "building", "construction"]):
            score += 0.2

        return min(score, 1.0)

    def _normalize_url(self, url: str) -> str:
        """Normalize URL for deduplication."""
        # Remove protocol, www, trailing slashes
        url = url.lower().strip()
        url = url.replace("https://", "").replace("http://", "")
        url = url.replace("www.", "")
        url = url.rstrip("/")
        return url

    async def validate_portal(self, portal_info: PortalInfo) -> bool:
        """
        Validate that portal actually has permit search functionality.

        Args:
            portal_info: Portal to validate

        Returns:
            True if portal is valid and functional
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(portal_info.url, follow_redirects=True)
                if response.status_code != 200:
                    return False

                html = response.text.lower()

                # Check for permit search indicators
                search_indicators = [
                    "permit",
                    "search",
                    "application",
                    "record",
                    "building",
                ]

                if any(indicator in html for indicator in search_indicators):
                    portal_info.validated = True
                    return True

        except Exception as e:
            logger.debug(f"Portal validation failed for {portal_info.url}: {e}")

        return False
