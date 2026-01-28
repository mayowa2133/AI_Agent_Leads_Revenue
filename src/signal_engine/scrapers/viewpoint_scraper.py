"""Reusable ViewPoint Cloud scraper for permit portals.

ViewPoint Cloud is used by 50+ cities. This scraper handles the modern
React-based ViewPoint Cloud interface.

URL Pattern: https://{city}.viewpointcloud.com
"""

from __future__ import annotations

from src.signal_engine.models import PermitData
from src.signal_engine.scrapers.base_scraper import ScraperError, dedupe_permits
from src.signal_engine.scrapers.permit_scraper import PortalSelectors, PlaywrightPermitScraper


class ViewPointScraper(PlaywrightPermitScraper):
    """
    Reusable scraper for ViewPoint Cloud permit portals.
    
    ViewPoint Cloud uses a modern React-based interface. This scraper
    handles the standard ViewPoint search and results patterns.
    
    Works for any city using ViewPoint Cloud by configuring:
    - city_subdomain: City subdomain (e.g., "seattle" for seattle.viewpointcloud.com)
    - permit_type: Optional filter for permit type
    
    URL Pattern: https://{city_subdomain}.viewpointcloud.com
    
    Example:
        # Seattle permits
        scraper = ViewPointScraper(city_subdomain="seattle")
    """
    
    source = "viewpoint_cloud"
    
    def __init__(
        self,
        *,
        city_subdomain: str,  # e.g., "seattle" for seattle.viewpointcloud.com
        permit_type: str | None = None,  # Optional filter
        days_back: int = 30,
        max_retries: int = 3,
        base_delay_s: float = 1.0,
        extract_applicant: bool = True,
    ):
        # Build ViewPoint URL
        base_url = f"https://{city_subdomain}.viewpointcloud.com"
        search_url = f"{base_url}/permits"  # Common ViewPoint permits page
        
        # ViewPoint uses React, so selectors may vary
        # Common patterns:
        # - Results in table or card format
        # - Permit number, type, address, status
        selectors = PortalSelectors(
            row="table tbody tr, .permit-card, [data-testid*='permit']",
            permit_id="td:nth-child(1), .permit-number, [data-testid='permit-number']",
            permit_type="td:nth-child(2), .permit-type, [data-testid='permit-type']",
            address="td:nth-child(3), .permit-address, [data-testid='permit-address']",
            status="td:nth-child(4), .permit-status, [data-testid='permit-status']",
            detail_url="a, .permit-link, [data-testid='permit-link']",
            applicant_selector='[id*="applicant"], [id*="contractor"], [data-testid*="applicant"]',
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
        """Override to handle ViewPoint Cloud navigation and search."""
        from playwright.async_api import async_playwright
        
        permits: list[PermitData] = []
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            # Step 1: Navigate to permits page
            await page.goto(self.start_url, wait_until="networkidle", timeout=30000)
            await page.wait_for_timeout(3000)  # Wait for React to render
            
            # Step 2: Look for search form or filter options
            # ViewPoint may have:
            # - Search input field
            # - Date range filters
            # - Permit type dropdown
            
            # Try to find and interact with search elements
            # This is a generic implementation - may need customization per city
            
            # Step 3: Wait for results to load
            await page.wait_for_timeout(2000)
            
            # Step 4: Extract results
            # ViewPoint results may be in table or card format
            rows = await page.query_selector_all(self.selectors.row)
            
            # If no rows with primary selector, try alternatives
            if not rows:
                # Try common ViewPoint patterns
                alt_selectors = [
                    "table.permit-table tbody tr",
                    ".permit-list .permit-item",
                    "[class*='permit'] [class*='row']",
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
            
            # Step 5: Extract permit data
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


def create_viewpoint_scraper(
    city_subdomain: str,
    permit_type: str | None = None,
    days_back: int = 30,
) -> ViewPointScraper:
    """
    Factory function to create a ViewPoint scraper.
    
    Args:
        city_subdomain: City subdomain (e.g., "seattle" for seattle.viewpointcloud.com)
        permit_type: Optional filter for permit type
        days_back: Number of days to look back (default 30)
    
    Returns:
        Configured ViewPointScraper instance
    
    Example:
        scraper = create_viewpoint_scraper("seattle")
    """
    return ViewPointScraper(
        city_subdomain=city_subdomain,
        permit_type=permit_type,
        days_back=days_back,
    )
