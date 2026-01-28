"""Reusable EnerGov scraper for permit portals.

EnerGov is used by 30+ cities. This scraper handles the standard
EnerGov permit search interface.

URL Pattern: https://{city}.energov.com
"""

from __future__ import annotations

from src.signal_engine.models import PermitData
from src.signal_engine.scrapers.base_scraper import ScraperError, dedupe_permits
from src.signal_engine.scrapers.permit_scraper import PortalSelectors, PlaywrightPermitScraper


class EnerGovScraper(PlaywrightPermitScraper):
    """
    Reusable scraper for EnerGov permit portals.
    
    EnerGov uses a standard permit search interface. This scraper
    handles the common EnerGov search and results patterns.
    
    Works for any city using EnerGov by configuring:
    - city_subdomain: City subdomain (e.g., "austin" for austin.energov.com)
    - permit_type: Optional filter for permit type
    
    URL Pattern: https://{city_subdomain}.energov.com
    
    Example:
        # Austin permits
        scraper = EnerGovScraper(city_subdomain="austin")
    """
    
    source = "energov"
    
    def __init__(
        self,
        *,
        city_subdomain: str,  # e.g., "austin" for austin.energov.com
        permit_type: str | None = None,  # Optional filter
        days_back: int = 30,
        max_retries: int = 3,
        base_delay_s: float = 1.0,
        extract_applicant: bool = True,
    ):
        # Build EnerGov URL
        base_url = f"https://{city_subdomain}.energov.com"
        search_url = f"{base_url}/EnerGov_Prod/SelfService#/search"  # Common EnerGov search page
        
        # EnerGov common selectors:
        # - Results in table format
        # - Permit number, type, address, status
        selectors = PortalSelectors(
            row="table tbody tr, .search-result-row, [class*='permit-row']",
            permit_id="td:nth-child(1), .permit-number, [data-field='permitNumber']",
            permit_type="td:nth-child(2), .permit-type, [data-field='permitType']",
            address="td:nth-child(3), .permit-address, [data-field='address']",
            status="td:nth-child(4), .permit-status, [data-field='status']",
            detail_url="a, .permit-link, [data-action='view-permit']",
            applicant_selector='[id*="applicant"], [id*="contractor"], [data-field*="applicant"]',
        )
        super().__init__(
            start_url=search_url,
            selectors=selectors,
            max_pages=1,
            max_retries=max_retries,
            base_delay_s=base_delay_s,
            extract_applicant=extract_applicant,
        )
        self.city_subdomain = city_subdomain
        self.permit_type = permit_type
        self.days_back = days_back
        self.base_url = base_url
    
    async def _scrape_full(self) -> list[PermitData]:
        """Override to handle EnerGov navigation and search."""
        from playwright.async_api import async_playwright
        
        permits: list[PermitData] = []
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            # Step 1: Navigate to search page
            await page.goto(self.start_url, wait_until="networkidle", timeout=30000)
            await page.wait_for_timeout(2000)
            
            # Step 2: Look for search form
            # EnerGov typically has:
            # - Search input field
            # - Date range filters
            # - Permit type dropdown
            
            # Try to find and interact with search elements
            # This is a generic implementation - may need customization per city
            
            # Step 3: Submit search
            # EnerGov may use form submission or AJAX
            
            # Step 4: Wait for results
            await page.wait_for_timeout(2000)
            
            # Step 5: Extract results
            rows = await page.query_selector_all(self.selectors.row)
            
            # If no rows with primary selector, try alternatives
            if not rows:
                alt_selectors = [
                    "table.permit-table tbody tr",
                    ".search-results tbody tr",
                    "[class*='permit'] tbody tr",
                ]
                for alt_selector in alt_selectors:
                    rows = await page.query_selector_all(alt_selector)
                    if rows:
                        break
            
            # Check for no results
            if not rows:
                page_text = await page.evaluate("() => document.body.innerText")
                if page_text and any(term in page_text.lower() for term in ["no results", "no permits", "0 results"]):
                    await browser.close()
                    return dedupe_permits(permits)
            
            # Step 6: Extract permit data
            for row in rows:
                try:
                    permit_id_elem = await row.query_selector(self.selectors.permit_id)
                    permit_type_elem = await row.query_selector(self.selectors.permit_type)
                    address_elem = await row.query_selector(self.selectors.address)
                    status_elem = await row.query_selector(self.selectors.status)
                    
                    if not all([permit_id_elem, permit_type_elem, address_elem, status_elem]):
                        continue
                    
                    permit_id = (await permit_id_elem.inner_text()).strip()
                    permit_type = (await permit_type_elem.inner_text()).strip()
                    address = (await address_elem.inner_text()).strip()
                    status = (await status_elem.inner_text()).strip()
                    
                    detail_url = None
                    if self.selectors.detail_url:
                        a = await row.query_selector(self.selectors.detail_url)
                        if a:
                            href = await a.get_attribute("href")
                            if href:
                                if href.startswith("/"):
                                    detail_url = f"{self.base_url}{href}"
                                elif href.startswith("http"):
                                    detail_url = href
                                else:
                                    detail_url = f"{self.base_url}/{href}"
                    
                    # Extract applicant from detail page if enabled
                    applicant_name = None
                    if self.extract_applicant and detail_url:
                        applicant_name = await self._extract_applicant_from_detail(page, detail_url)
                    
                    permits.append(
                        PermitData(
                            source=f"{self.source}_{self.city_subdomain}",
                            permit_id=permit_id,
                            permit_type=permit_type,
                            address=address,
                            building_type=None,
                            status=status,
                            applicant_name=applicant_name,
                            issued_date=None,
                            detail_url=detail_url,
                        )
                    )
                except Exception as e:
                    print(f"Warning: Failed to parse row: {e}")
                    continue
            
            await browser.close()
        
        return dedupe_permits(permits)


def create_energov_scraper(
    city_subdomain: str,
    permit_type: str | None = None,
    days_back: int = 30,
) -> EnerGovScraper:
    """
    Factory function to create an EnerGov scraper.
    
    Args:
        city_subdomain: City subdomain (e.g., "austin" for austin.energov.com)
        permit_type: Optional filter for permit type
        days_back: Number of days to look back (default 30)
    
    Returns:
        Configured EnerGovScraper instance
    
    Example:
        scraper = create_energov_scraper("austin")
    """
    return EnerGovScraper(
        city_subdomain=city_subdomain,
        permit_type=permit_type,
        days_back=days_back,
    )
