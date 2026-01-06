from __future__ import annotations

from datetime import datetime

from src.signal_engine.models import PermitData
from src.signal_engine.scrapers.base_scraper import BaseScraper


class RegulatoryUpdateScraper(BaseScraper):
    """
    Placeholder scraper for regulatory updates.

    In production, this would ingest RSS feeds, PDFs, and bulletins from
    state fire marshals / authorities having jurisdiction.
    """

    source = "regulatory_updates"

    async def scrape(self) -> list[PermitData]:
        # Not a permit source; this is scaffolded here for symmetry.
        return []

    async def check_for_updates(self, last_run: datetime) -> list[PermitData]:
        _ = last_run
        return []


