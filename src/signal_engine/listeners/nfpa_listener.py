"""NFPA code amendment announcement listener."""

from __future__ import annotations

import logging
import re
from datetime import datetime

from playwright.async_api import async_playwright

from src.signal_engine.listeners.base_listener import BaseRegulatoryListener
from src.signal_engine.models import RegulatoryUpdate

logger = logging.getLogger(__name__)


class NFPAListener(BaseRegulatoryListener):
    """
    Listener for NFPA code amendment announcements.
    
    Scrapes NFPA.org for code update announcements.
    """

    source = "nfpa"

    def __init__(
        self,
        *,
        base_url: str = "https://www.nfpa.org",
        max_retries: int = 3,
        base_delay_s: float = 1.0,
    ):
        """
        Initialize NFPA listener.
        
        Args:
            base_url: Base URL for NFPA website
            max_retries: Maximum retry attempts
            base_delay_s: Base delay between retries
        """
        super().__init__(max_retries=max_retries, base_delay_s=base_delay_s)
        self.base_url = base_url
        # NFPA code update page (may need to be discovered/updated)
        self.updates_url = f"{base_url}/Codes-and-Standards/Resources/Code-updates"

    async def check_for_updates(self, last_run: datetime | None) -> list[RegulatoryUpdate]:
        """
        Check for new NFPA code amendments since last run.
        
        Args:
            last_run: Last run timestamp (None for first run)
            
        Returns:
            List of new RegulatoryUpdate objects
        """
        return await self._with_retries(self._fetch_updates, last_run)

    async def _fetch_updates(self, last_run: datetime | None) -> list[RegulatoryUpdate]:
        """Internal method to fetch updates from NFPA website."""
        updates: list[RegulatoryUpdate] = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            try:
                await page.goto(self.updates_url, wait_until="networkidle", timeout=30000)
                await page.wait_for_timeout(2000)  # Wait for page to render

                # Look for code update announcements
                # NFPA website structure may vary - this is a flexible approach
                # Look for common patterns: code numbers, dates, links

                # Try to find update items (adjust selectors based on actual NFPA site structure)
                update_items = await page.query_selector_all(
                    "article, .update-item, .code-update, [class*='update'], [class*='announcement']"
                )

                for item in update_items:
                    try:
                        update = await self._parse_update_item(item, page)
                        if update:
                            # Filter by date if last_run is provided
                            if last_run and update.published_date <= last_run:
                                continue
                            updates.append(update)
                    except Exception as e:
                        logger.warning(f"Error parsing NFPA update item: {e}")
                        continue

            except Exception as e:
                logger.error(f"Error fetching NFPA updates: {e}", exc_info=True)
            finally:
                await browser.close()

        logger.info(f"Found {len(updates)} new NFPA code updates")
        return updates

    async def _parse_update_item(self, item, page) -> RegulatoryUpdate | None:
        """
        Parse a single NFPA update item from the page.
        
        Args:
            item: Playwright element handle
            page: Playwright page object
            
        Returns:
            RegulatoryUpdate or None if parsing fails
        """
        import hashlib

        # Extract title
        title_elem = await item.query_selector("h1, h2, h3, .title, [class*='title']")
        title = (await title_elem.inner_text()).strip() if title_elem else ""

        if not title:
            return None

        # Extract content/description
        content_elem = await item.query_selector("p, .description, [class*='description'], .summary")
        content = (await content_elem.inner_text()).strip() if content_elem else ""

        # Extract URL
        link_elem = await item.query_selector("a")
        url = ""
        if link_elem:
            href = await link_elem.get_attribute("href")
            if href:
                url = href if href.startswith("http") else f"{self.base_url}{href}"

        if not url:
            # Try to get URL from page context
            url = page.url

        # Extract date (look for date patterns)
        date_elem = await item.query_selector(
            ".date, [class*='date'], time, [datetime]"
        )
        published_date = datetime.now(tz=datetime.now().astimezone().tzinfo)
        if date_elem:
            date_text = (await date_elem.inner_text()).strip()
            date_attr = await date_elem.get_attribute("datetime")
            if date_attr:
                try:
                    from dateutil import parser

                    published_date = parser.parse(date_attr)
                except Exception:
                    pass

        # Extract NFPA code numbers from title/content
        code_pattern = r"NFPA\s+(\d+)"
        codes = re.findall(code_pattern, title + " " + content, re.IGNORECASE)
        applicable_codes = [f"NFPA {code}" for code in codes]

        # Generate update ID
        update_id = hashlib.sha256(f"{self.source}:{title}:{url}".encode()).hexdigest()[:32]

        return RegulatoryUpdate(
            update_id=update_id,
            source=self.source,
            source_name="National Fire Protection Association",
            title=title,
            content=content,
            published_date=published_date,
            effective_date=None,  # May need additional parsing
            url=url,
            jurisdiction="Federal",
            applicable_codes=applicable_codes,
            compliance_triggers=[],  # Will be populated by content processor
            building_types_affected=[],  # Will be populated by content processor
        )

