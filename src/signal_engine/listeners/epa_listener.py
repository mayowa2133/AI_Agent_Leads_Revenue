"""EPA/Federal Register regulatory listener."""

from __future__ import annotations

import hashlib
import logging
import re
from datetime import datetime

import httpx

from src.signal_engine.listeners.base_listener import BaseRegulatoryListener
from src.signal_engine.models import RegulatoryUpdate

logger = logging.getLogger(__name__)


class EPARegulatoryListener(BaseRegulatoryListener):
    """
    Listener for EPA regulations from Federal Register.
    
    Monitors Federal Register for EPA-related regulations, focusing on
    HVAC/refrigerant phase-out schedules.
    """

    source = "epa"

    def __init__(
        self,
        *,
        federal_register_api_url: str = "https://www.federalregister.gov/api/v1/documents.json",
        max_retries: int = 3,
        base_delay_s: float = 1.0,
    ):
        """
        Initialize EPA listener.
        
        Args:
            federal_register_api_url: Federal Register API endpoint
            max_retries: Maximum retry attempts
            base_delay_s: Base delay between retries
        """
        super().__init__(max_retries=max_retries, base_delay_s=base_delay_s)
        self.api_url = federal_register_api_url

    async def check_for_updates(self, last_run: datetime | None) -> list[RegulatoryUpdate]:
        """
        Check for new EPA regulations since last run.
        
        Args:
            last_run: Last run timestamp (None for first run)
            
        Returns:
            List of new RegulatoryUpdate objects
        """
        return await self._with_retries(self._fetch_updates, last_run)

    async def _fetch_updates(self, last_run: datetime | None) -> list[RegulatoryUpdate]:
        """Internal method to fetch updates from Federal Register API."""
        updates: list[RegulatoryUpdate] = []

        # Build API query parameters
        params = {
            "agencies[]": "environmental-protection-agency",
            "per_page": 100,
            "order": "newest",
        }

        # Add date filter if last_run is provided
        if last_run:
            params["publication_date[gte]"] = last_run.strftime("%Y-%m-%d")

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(self.api_url, params=params)
                response.raise_for_status()
                data = response.json()

                # Process results
                for result in data.get("results", []):
                    try:
                        update = self._parse_federal_register_entry(result)
                        if update:
                            updates.append(update)
                    except Exception as e:
                        logger.warning(f"Error parsing Federal Register entry: {e}")
                        continue

            except httpx.HTTPError as e:
                logger.error(f"Error fetching from Federal Register API: {e}")
                raise

        logger.info(f"Found {len(updates)} new EPA regulatory updates")
        return updates

    def _parse_federal_register_entry(self, entry: dict) -> RegulatoryUpdate | None:
        """
        Parse a Federal Register API entry into RegulatoryUpdate.
        
        Args:
            entry: Federal Register API entry dictionary
            
        Returns:
            RegulatoryUpdate or None if parsing fails
        """
        # Extract basic fields
        title = entry.get("title", "").strip() if entry.get("title") else ""
        if not title:
            return None

        # Filter for HVAC/refrigerant related regulations
        title_lower = title.lower() if title else ""
        abstract = entry.get("abstract") or ""
        content_lower = abstract.lower() if abstract else ""
        
        # Keywords for HVAC/refrigerant regulations
        relevant_keywords = [
            "refrigerant",
            "hvac",
            "phase-out",
            "phaseout",
            "ozone",
            "hcfc",
            "hfc",
            "r-22",
            "r-410a",
        ]

        # Skip if not relevant to HVAC/refrigerant
        if not any(keyword in title_lower or keyword in content_lower for keyword in relevant_keywords):
            return None

        # Extract content
        content = entry.get("abstract", "") or entry.get("body_html", "")
        # Clean HTML if present
        if content and "<" in content:
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(content, "html.parser")
            content = soup.get_text(separator=" ", strip=True)

        # Extract dates
        published_date_str = entry.get("publication_date")
        published_date = datetime.now(tz=datetime.now().astimezone().tzinfo)
        if published_date_str:
            try:
                from dateutil import parser

                published_date = parser.parse(published_date_str)
            except Exception:
                pass

        # Extract URL
        url = entry.get("html_url", "") or entry.get("pdf_url", "")

        # Extract regulation numbers/CFR citations
        cfr_pattern = r"(\d+)\s+CFR\s+(\d+(?:\.\d+)?)"
        cfr_citations = re.findall(cfr_pattern, title + " " + content)
        applicable_codes = [f"{part} CFR {section}" for part, section in cfr_citations]

        # Generate update ID
        update_id = hashlib.sha256(
            f"{self.source}:{title}:{url}".encode()
        ).hexdigest()[:32]

        return RegulatoryUpdate(
            update_id=update_id,
            source=self.source,
            source_name="U.S. Environmental Protection Agency",
            title=title,
            content=content[:5000],  # Limit content length
            published_date=published_date,
            effective_date=None,  # May need additional parsing
            url=url,
            jurisdiction="Federal",
            applicable_codes=applicable_codes,
            compliance_triggers=[],  # Will be populated by content processor
            building_types_affected=[],  # Will be populated by content processor
        )

