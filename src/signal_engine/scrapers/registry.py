"""Scraper registry for routing portals to appropriate scrapers."""

from __future__ import annotations

from src.signal_engine.discovery.portal_discovery import PortalInfo, PortalType
from src.signal_engine.scrapers.accela_scraper import AccelaScraper, create_accela_scraper
from src.signal_engine.scrapers.base_scraper import BaseScraper
from src.signal_engine.scrapers.energov_scraper import EnerGovScraper, create_energov_scraper
from src.signal_engine.scrapers.permit_scraper import (
    MecklenburgPermitScraper,
    PlaywrightPermitScraper,
    PortalSelectors,
)
from src.signal_engine.scrapers.viewpoint_scraper import ViewPointScraper, create_viewpoint_scraper


class ScraperRegistry:
    """
    Registry of available scrapers by portal type.
    
    This registry routes discovered portals to the appropriate scraper
    based on the portal's system type.
    """
    
    REGISTRY: dict[PortalType, type[BaseScraper]] = {
        PortalType.ACCELA: AccelaScraper,
        PortalType.VIEWPOINT: ViewPointScraper,
        PortalType.ENERGOV: EnerGovScraper,
        PortalType.MECKLENBURG: MecklenburgPermitScraper,
        # PortalType.CUSTOM: PlaywrightPermitScraper,  # Generic fallback - requires manual config
        # PortalType.UNKNOWN: PlaywrightPermitScraper,  # Generic fallback - requires manual config
    }
    
    @classmethod
    def create_scraper(
        cls,
        portal_info: PortalInfo,
        **kwargs,
    ) -> BaseScraper:
        """
        Factory method to create appropriate scraper for a portal.
        
        Args:
            portal_info: Portal information from discovery
            **kwargs: Additional scraper configuration
        
        Returns:
            Configured scraper instance
        
        Raises:
            ValueError: If portal type is not supported or config is missing
        
        Example:
            # Get portal from discovery
            storage = PortalStorage()
            portal = storage.get_portals(city="San Diego", system_type=PortalType.ACCELA)[0]
            
            # Create scraper
            scraper = ScraperRegistry.create_scraper(portal)
            permits = await scraper.scrape()
        """
        scraper_class = cls.REGISTRY.get(portal_info.system_type)
        
        if not scraper_class:
            raise ValueError(
                f"No scraper available for portal type: {portal_info.system_type}. "
                f"Supported types: {list(cls.REGISTRY.keys())}"
            )
        
        # Extract configuration from portal info
        config = portal_info.config or {}
        
        # Merge with kwargs (kwargs take precedence)
        config = {**config, **kwargs}
        
        # Route to appropriate scraper factory based on type
        if portal_info.system_type == PortalType.ACCELA:
            return cls._create_accela_scraper(portal_info, config)
        elif portal_info.system_type == PortalType.VIEWPOINT:
            return cls._create_viewpoint_scraper(portal_info, config)
        elif portal_info.system_type == PortalType.ENERGOV:
            return cls._create_energov_scraper(portal_info, config)
        elif portal_info.system_type == PortalType.MECKLENBURG:
            return cls._create_mecklenburg_scraper(portal_info, config)
        else:
            # Fallback to generic Playwright scraper
            return cls._create_generic_scraper(portal_info, config)
    
    @classmethod
    def _create_accela_scraper(cls, portal_info: PortalInfo, config: dict) -> AccelaScraper:
        """Create Accela scraper from portal info."""
        # Extract city code from URL
        # URL pattern: https://aca-prod.accela.com/{CITY_CODE}/Cap/
        url = portal_info.url
        city_code = None
        
        # Try to extract from URL
        if "aca-prod.accela.com" in url:
            parts = url.split("/")
            for i, part in enumerate(parts):
                if "accela.com" in part and i + 1 < len(parts):
                    city_code = parts[i + 1].upper()
                    break
        
        # Fallback: try to get from config
        if not city_code:
            city_code = config.get("city_code")
        
        # Fallback: try to infer from city name (basic mapping)
        if not city_code:
            city_code = cls._infer_city_code(portal_info.city)
        
        if not city_code:
            raise ValueError(
                f"Could not determine city_code for Accela portal: {portal_info.url}. "
                f"Please provide 'city_code' in portal config."
            )
        
        # Get module from config (default to "Fire")
        module = config.get("module", "Fire")
        
        # Get other options
        record_type = config.get("record_type")
        days_back = config.get("days_back", 30)
        
        return create_accela_scraper(
            city_code=city_code,
            module=module,
            record_type=record_type,
            days_back=days_back,
        )
    
    @classmethod
    def _create_viewpoint_scraper(cls, portal_info: PortalInfo, config: dict) -> ViewPointScraper:
        """Create ViewPoint scraper from portal info."""
        # Extract city subdomain from URL
        # URL pattern: https://{city}.viewpointcloud.com
        url = portal_info.url
        city_subdomain = None
        
        if "viewpointcloud.com" in url:
            # Extract subdomain
            if url.startswith("https://"):
                parts = url.replace("https://", "").split(".")
                if parts:
                    city_subdomain = parts[0]
        
        # Fallback: try config
        if not city_subdomain:
            city_subdomain = config.get("city_subdomain")
        
        if not city_subdomain:
            raise ValueError(
                f"Could not determine city_subdomain for ViewPoint portal: {portal_info.url}. "
                f"Please provide 'city_subdomain' in portal config."
            )
        
        permit_type = config.get("permit_type")
        days_back = config.get("days_back", 30)
        
        return create_viewpoint_scraper(
            city_subdomain=city_subdomain,
            permit_type=permit_type,
            days_back=days_back,
        )
    
    @classmethod
    def _create_energov_scraper(cls, portal_info: PortalInfo, config: dict) -> EnerGovScraper:
        """Create EnerGov scraper from portal info."""
        # Extract city subdomain from URL
        # URL pattern: https://{city}.energov.com
        url = portal_info.url
        city_subdomain = None
        
        if "energov.com" in url:
            # Extract subdomain
            if url.startswith("https://"):
                parts = url.replace("https://", "").split(".")
                if parts:
                    city_subdomain = parts[0]
        
        # Fallback: try config
        if not city_subdomain:
            city_subdomain = config.get("city_subdomain")
        
        if not city_subdomain:
            raise ValueError(
                f"Could not determine city_subdomain for EnerGov portal: {portal_info.url}. "
                f"Please provide 'city_subdomain' in portal config."
            )
        
        permit_type = config.get("permit_type")
        days_back = config.get("days_back", 30)
        
        return create_energov_scraper(
            city_subdomain=city_subdomain,
            permit_type=permit_type,
            days_back=days_back,
        )
    
    @classmethod
    def _create_mecklenburg_scraper(cls, portal_info: PortalInfo, config: dict) -> MecklenburgPermitScraper:
        """Create Mecklenburg scraper from portal info."""
        search_type = config.get("search_type", "project_name")
        search_value = config.get("search_value", "Fire")
        street_number = config.get("street_number")
        
        return MecklenburgPermitScraper(
            search_type=search_type,
            search_value=search_value,
            street_number=street_number,
        )
    
    @classmethod
    def _create_generic_scraper(cls, portal_info: PortalInfo, config: dict) -> PlaywrightPermitScraper:
        """Create generic Playwright scraper (requires manual selector config)."""
        start_url = portal_info.url
        
        # Try to get selectors from config
        selectors = config.get("selectors")
        if selectors:
            portal_selectors = PortalSelectors(**selectors)
        else:
            # Default generic selectors (may not work for all portals)
            portal_selectors = PortalSelectors(
                row="table tbody tr",
                permit_id="td:nth-child(1)",
                permit_type="td:nth-child(2)",
                address="td:nth-child(3)",
                status="td:nth-child(4)",
                detail_url="a",
            )
        
        return PlaywrightPermitScraper(
            start_url=start_url,
            selectors=portal_selectors,
            max_pages=config.get("max_pages", 1),
        )
    
    @classmethod
    def _infer_city_code(cls, city_name: str) -> str | None:
        """
        Infer Accela city code from city name.
        
        This is a basic mapping - may need expansion.
        """
        # Common city code mappings
        mappings = {
            "San Antonio": "COSA",
            "Dallas": "DAL",
            "San Diego": "SANDIEGO",
            "Seattle": "SEATTLE",
            "Tampa": "TAMPA",
        }
        
        return mappings.get(city_name)
    
    @classmethod
    def is_supported(cls, portal_type: PortalType) -> bool:
        """Check if a portal type is supported."""
        return portal_type in cls.REGISTRY
    
    @classmethod
    def get_supported_types(cls) -> list[PortalType]:
        """Get list of supported portal types."""
        return list(cls.REGISTRY.keys())
