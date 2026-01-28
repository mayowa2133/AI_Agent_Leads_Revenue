"""Automated discovery scheduler for permit portals."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from src.signal_engine.config.portal_config import PortalConfig, PortalConfigManager
from src.signal_engine.discovery.portal_discovery import PortalDiscoveryService, PortalInfo
from src.signal_engine.discovery.portal_storage import PortalStorage

logger = logging.getLogger(__name__)


class DiscoveryScheduler:
    """
    Scheduled job to discover new permit portals.
    
    Runs weekly to discover new portals and automatically add them
    to the portal configuration system.
    """

    def __init__(self, config_manager: PortalConfigManager | None = None):
        """
        Initialize discovery scheduler.
        
        Args:
            config_manager: Portal configuration manager (creates new if None)
        """
        self.config_manager = config_manager or PortalConfigManager()
        self.portal_storage = PortalStorage()
        self.discovery_service = PortalDiscoveryService()
        self.scheduler = AsyncIOScheduler()

    def start(self, day_of_week: int = 0, hour: int = 2) -> None:
        """
        Start the discovery scheduler.
        
        Args:
            day_of_week: Day of week (0=Monday, 6=Sunday)
            hour: Hour of day (0-23)
        """
        # Schedule weekly discovery (default: Monday at 2 AM)
        trigger = CronTrigger(day_of_week=day_of_week, hour=hour)
        self.scheduler.add_job(
            self.discover_new_portals,
            trigger=trigger,
            id="discover_portals",
            name="Discover New Permit Portals",
            replace_existing=True,
        )
        self.scheduler.start()
        logger.info(f"Discovery scheduler started (runs weekly on day {day_of_week} at {hour}:00)")

    def stop(self) -> None:
        """Stop the discovery scheduler."""
        self.scheduler.shutdown()
        logger.info("Discovery scheduler stopped")

    async def discover_new_portals(
        self, cities: list[str] | None = None, auto_register: bool = True
    ) -> list[PortalInfo]:
        """
        Run portal discovery and add new portals to registry.
        
        Args:
            cities: List of cities to search (uses default if None)
            auto_register: Whether to automatically register new portals
        
        Returns:
            List of newly discovered portals
        """
        logger.info("Starting automated portal discovery...")
        
        if cities is None:
            cities = self.get_target_cities()
        
        logger.info(f"Discovering portals for {len(cities)} cities: {cities}")
        
        # Discover portals (use default query patterns)
        discovered_portals = await self.discovery_service.discover_portals(
            cities=cities,
        )
        
        logger.info(f"Discovered {len(discovered_portals)} portals")
        
        # Filter for new portals
        new_portals = []
        existing_source_ids = {c.source_id for c in self.config_manager.get_all_configs()}
        
        for portal in discovered_portals:
            # Generate source_id from portal
            source_id = self._generate_source_id(portal)
            
            if source_id not in existing_source_ids:
                new_portals.append(portal)
                logger.info(f"New portal discovered: {portal.city} - {portal.url}")
            else:
                logger.debug(f"Portal already exists: {portal.city} - {portal.url}")
        
        # Save to portal storage
        if new_portals:
            self.portal_storage.add_portals(new_portals)
            self.portal_storage.save()
            logger.info(f"Saved {len(new_portals)} new portals to storage")
        
        # Auto-register new portals if enabled
        if auto_register and new_portals:
            registered = await self.register_portals(new_portals)
            logger.info(f"Auto-registered {registered} new portals")
        
        return new_portals

    async def register_portals(self, portals: list[PortalInfo]) -> int:
        """
        Register portals in the configuration system.
        
        Args:
            portals: List of portals to register
        
        Returns:
            Number of portals registered
        """
        from src.signal_engine.api.unified_ingestion import PermitSourceType

        registered = 0
        
        for portal in portals:
            try:
                # Determine source type based on system type
                source_type = self._determine_source_type(portal)
                
                # Create portal config
                config = PortalConfig(
                    city=portal.city,
                    portal_url=portal.url,
                    system_type=portal.system_type,
                    source_type=source_type,
                    source_id=self._generate_source_id(portal),
                    config=portal.config or {},
                    enabled=True,  # Auto-enable new portals
                )
                
                self.config_manager.add_config(config)
                registered += 1
                
            except Exception as e:
                logger.error(f"Failed to register portal {portal.url}: {e}")
        
        return registered

    def _generate_source_id(self, portal: PortalInfo) -> str:
        """Generate unique source ID from portal."""
        # Use city and system type to create ID
        city_slug = portal.city.lower().replace(" ", "_").replace(",", "")
        system_slug = portal.system_type.value.lower()
        return f"{city_slug}_{system_slug}"

    def _determine_source_type(self, portal: PortalInfo) -> PermitSourceType:
        """Determine source type from portal."""
        from src.signal_engine.api.unified_ingestion import PermitSourceType

        # Check if it's an API portal (Socrata, CKAN, etc.)
        url_lower = portal.url.lower()
        if "data." in url_lower and ("socrata" in url_lower or ".gov" in url_lower):
            # Could be Socrata or CKAN - default to Socrata for now
            return PermitSourceType.SOCRATA_API
        elif "ckan" in url_lower:
            return PermitSourceType.CKAN_API
        
        # Default to scraper
        return PermitSourceType.SCRAPER

    def get_target_cities(self) -> list[str]:
        """
        Get list of target cities for discovery.
        
        Can be extended to read from config file or database.
        """
        # Default list of major US cities
        return [
            "San Antonio",
            "Denver",
            "Charlotte",
            "Seattle",
            "Portland",
            "Austin",
            "Dallas",
            "Houston",
            "Phoenix",
            "San Diego",
            "Los Angeles",
            "San Francisco",
            "Chicago",
            "New York",
            "Boston",
            "Miami",
            "Atlanta",
            "Nashville",
            "Minneapolis",
            "Detroit",
        ]

    async def run_discovery_now(self) -> list[PortalInfo]:
        """Run discovery immediately (for testing/manual triggers)."""
        return await self.discover_new_portals()
