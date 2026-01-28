"""Scrapers for permits/regulatory portals."""

from src.signal_engine.scrapers.accela_scraper import AccelaScraper, create_accela_scraper
from src.signal_engine.scrapers.base_scraper import BaseScraper, ScraperError, dedupe_permits
from src.signal_engine.scrapers.energov_scraper import EnerGovScraper, create_energov_scraper
from src.signal_engine.scrapers.permit_scraper import (
    MecklenburgPermitScraper,
    PlaywrightPermitScraper,
    PortalSelectors,
)
from src.signal_engine.scrapers.registry import ScraperRegistry
from src.signal_engine.scrapers.viewpoint_scraper import ViewPointScraper, create_viewpoint_scraper

__all__ = [
    "BaseScraper",
    "ScraperError",
    "dedupe_permits",
    "PlaywrightPermitScraper",
    "PortalSelectors",
    "MecklenburgPermitScraper",
    "AccelaScraper",
    "create_accela_scraper",
    "ViewPointScraper",
    "create_viewpoint_scraper",
    "EnerGovScraper",
    "create_energov_scraper",
    "ScraperRegistry",
]

