from __future__ import annotations

from datetime import datetime

from src.signal_engine.models import PermitData
from src.signal_engine.scrapers.base_scraper import BaseScraper


class RegulatoryUpdateScraper(BaseScraper):
    """
    Legacy scraper interface for regulatory updates.
    
    Note: Regulatory updates are now handled by listeners in
    src/signal_engine/listeners/. This class is kept for backward
    compatibility but returns empty results. Use the listeners directly
    for regulatory monitoring.
    """

    source = "regulatory_updates"

    async def scrape(self) -> list[PermitData]:
        """
        Scrape regulatory updates.
        
        Note: This returns empty list. Use regulatory listeners instead:
        - FireMarshalListener for state fire marshal bulletins
        - NFPAListener for NFPA code amendments
        - EPARegulatoryListener for EPA regulations
        """
        return []

    async def check_for_updates(self, last_run: datetime) -> list[PermitData]:
        """
        Check for regulatory updates since last run.
        
        Note: This returns empty list. Use regulatory listeners instead.
        """
        _ = last_run
        return []


