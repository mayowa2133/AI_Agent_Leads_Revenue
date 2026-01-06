from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from src.signal_engine.models import PermitData
from src.signal_engine.scrapers.base_scraper import BaseScraper, dedupe_permits


@dataclass(frozen=True)
class PortalSelectors:
    """
    CSS selectors used by the Playwright scraper. This makes it easy to
    customize per municipality without rewriting the engine.
    """

    row: str
    permit_id: str
    permit_type: str
    address: str
    status: str
    detail_url: str | None = None


class PlaywrightPermitScraper(BaseScraper):
    """
    Generic Playwright-based scraper.

    You configure:
    - start_url
    - selectors for the permit rows/fields
    """

    source = "playwright_portal"

    def __init__(
        self,
        *,
        start_url: str,
        selectors: PortalSelectors,
        max_pages: int = 1,
        max_retries: int = 3,
        base_delay_s: float = 1.0,
    ):
        super().__init__(max_retries=max_retries, base_delay_s=base_delay_s)
        self.start_url = start_url
        self.selectors = selectors
        self.max_pages = max_pages

    async def scrape(self) -> list[PermitData]:
        return await self._with_retries(self._scrape_full)

    async def check_for_updates(self, last_run: datetime) -> list[PermitData]:
        # Many portals don't support clean "since" filters; MVP uses full scrape.
        # In production, extend with portal-specific query params and date filters.
        _ = last_run
        return await self.scrape()

    async def _scrape_full(self) -> list[PermitData]:
        from playwright.async_api import async_playwright

        permits: list[PermitData] = []
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(self.start_url, wait_until="networkidle")

            # MVP: scrape first page only unless max_pages > 1 (pagination can vary widely).
            for _page_idx in range(self.max_pages):
                rows = await page.query_selector_all(self.selectors.row)
                for row in rows:
                    permit_id = (await (await row.query_selector(self.selectors.permit_id)).inner_text()).strip()
                    permit_type = (
                        await (await row.query_selector(self.selectors.permit_type)).inner_text()
                    ).strip()
                    address = (await (await row.query_selector(self.selectors.address)).inner_text()).strip()
                    status = (await (await row.query_selector(self.selectors.status)).inner_text()).strip()

                    detail_url = None
                    if self.selectors.detail_url:
                        a = await row.query_selector(self.selectors.detail_url)
                        if a:
                            href = await a.get_attribute("href")
                            detail_url = href

                    permits.append(
                        PermitData(
                            source=self.source,
                            permit_id=permit_id,
                            permit_type=permit_type,
                            address=address,
                            building_type=None,
                            status=status,
                            applicant_name=None,
                            issued_date=None,
                            detail_url=detail_url,
                        )
                    )

                # Try naive next-page click if present (best-effort).
                next_btn = await page.query_selector("text=Next")
                if not next_btn:
                    break
                await next_btn.click()
                await page.wait_for_load_state("networkidle")

            await browser.close()

        return dedupe_permits(permits)


def example_fire_permit_scraper(start_url: str) -> PlaywrightPermitScraper:
    """
    Factory for a common 'table of permits' UI pattern.
    This is a starting point; adjust selectors per target portal.
    """
    selectors = PortalSelectors(
        row="table tbody tr",
        permit_id="td:nth-child(1)",
        permit_type="td:nth-child(2)",
        address="td:nth-child(3)",
        status="td:nth-child(4)",
        detail_url="a",
    )
    return PlaywrightPermitScraper(start_url=start_url, selectors=selectors, max_pages=1)


