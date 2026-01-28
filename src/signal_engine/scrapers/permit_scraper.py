from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from src.signal_engine.models import PermitData
from src.signal_engine.scrapers.base_scraper import BaseScraper, ScraperError, dedupe_permits


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
    applicant_selector: str | None = None  # Selector for applicant name on detail page


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
        extract_applicant: bool = False,  # Whether to extract applicant from detail pages
    ):
        super().__init__(max_retries=max_retries, base_delay_s=base_delay_s)
        self.start_url = start_url
        self.selectors = selectors
        self.max_pages = max_pages
        self.extract_applicant = extract_applicant

    async def _extract_applicant_from_detail(
        self,
        page,
        detail_url: str,
    ) -> str | None:
        """
        Extract applicant/contractor name from permit detail page.
        
        Args:
            page: Playwright page object
            detail_url: URL to the permit detail page
            
        Returns:
            Applicant name if found, None otherwise
        """
        if not detail_url:
            return None

        try:
            # If we're already on a detail page or the URL is a JavaScript postback,
            # don't navigate again.
            current_url = page.url
            is_detail_page = "CapDetail.aspx" in current_url or "Detail" in current_url
            if not is_detail_page and not detail_url.startswith("javascript:"):
                await page.goto(detail_url, wait_until="networkidle", timeout=10000)
                await page.wait_for_timeout(1000)  # Wait for page to render
            else:
                await page.wait_for_timeout(1000)

            # Try the configured selector first
            if self.selectors and self.selectors.applicant_selector:
                applicant_elem = await page.query_selector(self.selectors.applicant_selector)
                if applicant_elem:
                    applicant_text = (await applicant_elem.inner_text()).strip()
                    if applicant_text and not self._is_label_text(applicant_text):
                        return applicant_text

            # Strategy 0: XPath following-sibling axis for label/value pairs
            try:
                xpath_result = await page.evaluate(
                    """
                    () => {
                        const result = document.evaluate(
                            "//label[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'applicant') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'contractor') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'owner') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'company name')]/following-sibling::*[1][self::span or self::div or self::input or self::textarea]",
                            document,
                            null,
                            XPathResult.FIRST_ORDERED_NODE_TYPE,
                            null
                        );
                        const element = result.singleNodeValue;
                        if (element) {
                            if (element.tagName === 'INPUT' || element.tagName === 'TEXTAREA') {
                                const value = element.value;
                                if (value && value.trim().length > 2 && value.trim().length < 200) {
                                    return { type: 'value', text: value.trim() };
                                }
                            }
                            const text = element.textContent || element.innerText;
                            if (text && text.trim().length > 2 && text.trim().length < 200) {
                                return { type: 'text', text: text.trim() };
                            }
                        }
                        const tdResult = document.evaluate(
                            "//td[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'applicant') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'contractor') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'owner') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'company name')]/following-sibling::td[1]",
                            document,
                            null,
                            XPathResult.FIRST_ORDERED_NODE_TYPE,
                            null
                        );
                        const tdElement = tdResult.singleNodeValue;
                        if (tdElement) {
                            const text = tdElement.textContent || tdElement.innerText;
                            if (text && text.trim().length > 2 && text.trim().length < 200) {
                                return { type: 'text', text: text.trim() };
                            }
                        }
                        return null;
                    }
                    """
                )
                if xpath_result and xpath_result.get("text"):
                    candidate = xpath_result["text"].strip()
                    if candidate and len(candidate) > 2 and len(candidate) < 200:
                        if candidate.lower() not in [
                            "applicant",
                            "contractor",
                            "owner",
                            "applicant:",
                            "contractor:",
                            "owner:",
                            "n/a",
                            "none",
                        ]:
                            return candidate
            except Exception:
                pass

            # Strategy 1: Table row label/value pairs
            try:
                table_result = await page.evaluate(
                    """
                    () => {
                        const rows = document.querySelectorAll('tr');
                        for (const row of rows) {
                            const cells = row.querySelectorAll('th, td');
                            if (cells.length >= 2) {
                                const labelText = (cells[0].textContent || '').trim().toLowerCase();
                                if (labelText.includes('applicant') || labelText.includes('contractor') || labelText.includes('owner')) {
                                    const valueText = (cells[1].textContent || '').trim();
                                    if (valueText && valueText.length > 2 && valueText.length < 200) {
                                        return { type: 'text', text: valueText };
                                    }
                                }
                            }
                        }
                        return null;
                    }
                    """
                )
                if table_result and table_result.get("text"):
                    candidate = table_result["text"].strip()
                    if candidate and not self._is_label_text(candidate):
                        return candidate
            except Exception:
                pass
            
            # Fallback: Try common patterns for applicant/contractor fields
            # First try ID/name-based selectors
            id_selectors = [
                '[id*="applicant" i]',
                '[id*="contractor" i]',
                '[id*="owner" i]',
                '[name*="applicant" i]',
                '[name*="contractor" i]',
                '[name*="owner" i]',
            ]
            
            for selector in id_selectors:
                try:
                    elem = await page.query_selector(selector)
                    if elem:
                        text = (await elem.inner_text()).strip()
                        if text and len(text) < 200 and len(text) > 2:  # Reasonable name length
                            return text
                except Exception:
                    continue
            
            # Try label-based selectors
            try:
                # Look for labels containing "Applicant", "Contractor", or "Owner"
                labels = await page.query_selector_all('label')
                for label in labels:
                    label_text = (await label.inner_text()).strip().lower()
                    if any(term in label_text for term in ['applicant', 'contractor', 'owner']):
                        # Try to find associated input/span/div
                        label_for = await label.get_attribute('for')
                        if label_for:
                            associated = await page.query_selector(f'#{label_for}')
                            if associated:
                                text = (await associated.inner_text()).strip()
                                if text and len(text) < 200 and len(text) > 2:
                                    return text
                        # Try next sibling
                        parent = await label.evaluate_handle('el => el.parentElement')
                        if parent:
                            siblings = await parent.query_selector_all('*')
                            for sibling in siblings:
                                if sibling != label:
                                    text = (await sibling.inner_text()).strip()
                                    if text and len(text) < 200 and len(text) > 2:
                                        return text
            except Exception:
                pass
                    
        except Exception as e:
            # Log but don't fail - applicant extraction is optional
            print(f"Warning: Could not extract applicant from {detail_url}: {e}")
        
        return None

    async def _extract_address_from_detail(
        self,
        page,
        detail_url: str,
    ) -> str | None:
        """
        Extract address/location from permit detail page.
        """
        if not detail_url:
            return None

        try:
            current_url = page.url
            is_detail_page = "CapDetail.aspx" in current_url or "Detail" in current_url
            if not is_detail_page and not detail_url.startswith("javascript:"):
                await page.goto(detail_url, wait_until="networkidle", timeout=10000)
                await page.wait_for_timeout(1000)
            else:
                await page.wait_for_timeout(1000)

            # Strategy 0: XPath following-sibling axis for label/value pairs
            try:
                xpath_result = await page.evaluate(
                    """
                    () => {
                        const result = document.evaluate(
                            "//label[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'address') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'location')]/following-sibling::*[1][self::span or self::div or self::input or self::textarea]",
                            document,
                            null,
                            XPathResult.FIRST_ORDERED_NODE_TYPE,
                            null
                        );
                        const element = result.singleNodeValue;
                        if (element) {
                            if (element.tagName === 'INPUT' || element.tagName === 'TEXTAREA') {
                                const value = element.value;
                                if (value && value.trim().length > 5 && value.trim().length < 500) {
                                    return { type: 'value', text: value.trim() };
                                }
                            }
                            const text = element.textContent || element.innerText;
                            if (text && text.trim().length > 5 && text.trim().length < 500) {
                                return { type: 'text', text: text.trim() };
                            }
                        }
                        const tdResult = document.evaluate(
                            "//td[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'address') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'location')]/following-sibling::td[1]",
                            document,
                            null,
                            XPathResult.FIRST_ORDERED_NODE_TYPE,
                            null
                        );
                        const tdElement = tdResult.singleNodeValue;
                        if (tdElement) {
                            const text = tdElement.textContent || tdElement.innerText;
                            if (text && text.trim().length > 5 && text.trim().length < 500) {
                                return { type: 'text', text: text.trim() };
                            }
                        }
                        return null;
                    }
                    """
                )
                if xpath_result and xpath_result.get("text"):
                    candidate = xpath_result["text"].strip()
                    if candidate and not self._is_label_text(candidate):
                        return candidate
            except Exception:
                pass

            # Strategy 1: ID/name-based selectors
            id_selectors = [
                '[id*="address" i]',
                '[id*="location" i]',
                '[name*="address" i]',
                '[name*="location" i]',
            ]
            for selector in id_selectors:
                try:
                    elem = await page.query_selector(selector)
                    if elem:
                        text = (await elem.inner_text()).strip()
                        if text and len(text) > 5 and len(text) < 500 and not self._is_label_text(text):
                            return text
                except Exception:
                    continue

            # Strategy 2: Label-based extraction
            try:
                labels = await page.query_selector_all("label")
                for label in labels:
                    label_text = (await label.inner_text()).strip().lower()
                    if "address" in label_text or "location" in label_text:
                        label_for = await label.get_attribute("for")
                        if label_for:
                            associated = await page.query_selector(f"#{label_for}")
                            if associated:
                                text = (await associated.inner_text()).strip()
                                if text and len(text) > 5 and len(text) < 500 and not self._is_label_text(text):
                                    return text
                        parent = await label.evaluate_handle("el => el.parentElement")
                        if parent:
                            siblings = await parent.query_selector_all("*")
                            for sibling in siblings:
                                if sibling != label:
                                    text = (await sibling.inner_text()).strip()
                                    if text and len(text) > 5 and len(text) < 500 and not self._is_label_text(text):
                                        return text
            except Exception:
                pass
        except Exception as e:
            print(f"Warning: Could not extract address from {detail_url}: {e}")

        return None

    def _is_label_text(self, text: str) -> bool:
        """
        Heuristic to detect label/header text instead of real values.
        """
        if not text:
            return True

        text = text.strip()
        text_lower = text.lower()

        # Common label keywords
        label_keywords = [
            "applicant",
            "contractor",
            "owner",
            "address",
            "location",
            "status",
            "type",
            "information",
            "details",
        ]
        if text_lower.endswith(":") and any(keyword in text_lower for keyword in label_keywords):
            return True

        # All-caps headers are often labels, but allow valid all-caps addresses
        if text.isupper() and len(text) > 20:
            if not (
                any(char.isdigit() for char in text)
                and any(
                    word in text_lower
                    for word in [
                        "st",
                        "street",
                        "ave",
                        "avenue",
                        "rd",
                        "road",
                        "dr",
                        "drive",
                        "blvd",
                        "boulevard",
                        "ln",
                        "lane",
                        "way",
                        "court",
                        "ct",
                    ]
                )
            ):
                return True

        if len(text) < 50 and "information" in text_lower:
            return True

        return False

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


class MecklenburgPermitScraper(PlaywrightPermitScraper):
    """
    Specialized scraper for Mecklenburg County (Charlotte, NC) WebPermit portal.
    
    This portal uses ASP.NET postbacks and requires proper session initialization.
    Navigation sequence:
    1. Start at home page (warm up session)
    2. Click "View Permits"
    3. Click search type (By Project Name or By Address)
    4. Fill form and submit
    5. Scrape results table
    """
    
    source = "mecklenburg_county_webpermit"
    
    def __init__(
        self,
        *,
        search_type: str = "project_name",  # "project_name" or "address"
        search_value: str = "Fire",  # Project name or street name
        street_number: str | None = None,  # Required for address search
        max_retries: int = 3,
        base_delay_s: float = 1.0,
        extract_applicant: bool = True,  # Extract applicant from detail pages
    ):
        # Start URL is the home page - we'll navigate from there
        home_url = "https://webpermit.mecklenburgcountync.gov/"
        # Results table selector - Mecklenburg uses possegrid class
        # Column order: [Go button], Project Number, Project Name, Project Status, Web Project Address
        selectors = PortalSelectors(
            row="table.possegrid tbody tr.possegrid, #ctl00_MainContent_dgResults tr:not(.PosseGridHeader), table.possegrid tbody tr",
            permit_id="td:nth-child(2)",  # Project Number is 2nd column (after Go button)
            permit_type="td:nth-child(3)",  # Project Name is 3rd column  
            address="td:nth-child(5)",  # Web Project Address is 5th column
            status="td:nth-child(4)",  # Project Status is 4th column
            detail_url="td:nth-child(1) a",  # Go link is in 1st column
            applicant_selector='[id*="Applicant"], [id*="Contractor"], label:has-text("Applicant") + *',  # Common patterns
        )
        super().__init__(
            start_url=home_url,
            selectors=selectors,
            max_pages=1,
            max_retries=max_retries,
            base_delay_s=base_delay_s,
            extract_applicant=extract_applicant,
        )
        self.search_type = search_type
        self.search_value = search_value
        self.street_number = street_number
    
    async def _scrape_full(self) -> list[PermitData]:
        """Override to handle proper navigation sequence and form submission."""
        from playwright.async_api import async_playwright
        
        permits: list[PermitData] = []
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            # Step 1: Start at home page to initialize session
            await page.goto(self.start_url, wait_until="networkidle")
            await page.wait_for_timeout(1000)
            
            # Step 2: Click "View Permits" link
            view_permits_link = await page.query_selector('a:has-text("View Permits")') or \
                               await page.query_selector('a[href*="ViewPermits"]')
            if not view_permits_link:
                raise ScraperError("Could not find 'View Permits' link on Mecklenburg portal")
            
            await view_permits_link.click()
            await page.wait_for_load_state("networkidle")
            await page.wait_for_timeout(1500)
            
            # Step 3: Click the appropriate search type
            if self.search_type == "project_name":
                search_link = await page.query_selector('a:has-text("By Project Name")') or \
                            await page.query_selector('a[href*="SearchByProjectName"]')
                if not search_link:
                    raise ScraperError("Could not find 'By Project Name' link on Mecklenburg portal")
            else:  # address
                search_link = await page.query_selector('a:has-text("By Address")') or \
                            await page.query_selector('a[href*="SearchByAddress"]')
                if not search_link:
                    raise ScraperError("Could not find 'By Address' link on Mecklenburg portal")
            
            await search_link.click()
            await page.wait_for_load_state("networkidle")
            await page.wait_for_timeout(2000)  # Wait for form to render
            
            # Step 4: Fill the search form
            if self.search_type == "project_name":
                # Find project name input
                project_input = await page.query_selector('input[name*="ProjectName"]') or \
                              await page.query_selector('input[id*="ProjectName"]')
                if not project_input:
                    raise ScraperError("Could not find project name input field on Mecklenburg portal")
                await project_input.fill(self.search_value)
                search_field = project_input
            else:  # address
                # Fill street number if provided
                if self.street_number:
                    street_num_input = await page.query_selector('input[name*="StreetNumber"]') or \
                                     await page.query_selector('input[id*="StreetNumber"]')
                    if street_num_input:
                        await street_num_input.fill(self.street_number)
                        await page.wait_for_timeout(300)
                
                # Fill street name
                street_input = await page.query_selector('input[name*="StreetName"]') or \
                             await page.query_selector('input[id*="StreetName"]')
                if not street_input:
                    raise ScraperError("Could not find street name input field on Mecklenburg portal")
                await street_input.fill(self.search_value)
                search_field = street_input
            
            await page.wait_for_timeout(500)
            
            # Step 5: Submit form - MUST use explicit button click (Enter key causes page refresh)
            # Mecklenburg uses links with onclick handlers, not submit buttons
            # Look for PerformSearch links (top or bottom function band)
            submit_btn = await page.query_selector('a[id*="PerformSearch"], a[onclick*="PerformSearch"]')
            if not submit_btn:
                # Fallback to other search button patterns
                submit_btn = await page.query_selector('#ctl00_MainContent_btnSearch')
            if not submit_btn:
                submit_btn = await page.query_selector('input[type="submit"][value*="Search"]')
            if not submit_btn:
                submit_btn = await page.query_selector('input[type="submit"]')
            if not submit_btn:
                submit_btn = await page.query_selector('button[type="submit"]')
            
            if submit_btn:
                # Try clicking via JavaScript to ensure onclick handler fires
                btn_id = await submit_btn.get_attribute("id")
                if btn_id:
                    # Execute the onclick function directly
                    await page.evaluate(f"""
                        const btn = document.getElementById('{btn_id}');
                        if (btn && btn.onclick) {{
                            btn.onclick();
                        }} else if (btn) {{
                            btn.click();
                        }}
                    """)
                else:
                    await submit_btn.click()
                
                # Wait for navigation or results
                await page.wait_for_timeout(2000)
                await page.wait_for_load_state("networkidle", timeout=30000)
                await page.wait_for_timeout(3000)  # Wait for results table to render
            else:
                raise ScraperError("Could not find search submit button on Mecklenburg portal")
            
            # Step 6: Scrape the results table
            # Check if we got an error page or "no results" message
            try:
                page_title = await page.title()
                if "Error" in page_title:
                    # Take screenshot for debugging
                    await page.screenshot(path="debug_mecklenburg_error.png")
                    raise ScraperError(f"Mecklenburg portal returned error page: {page_title}")
            except Exception:
                # Page title might not be available due to navigation - continue anyway
                pass
            
            # Try multiple selectors to find results table
            rows = await page.query_selector_all(self.selectors.row)
            
            # If no rows with primary selector, try alternatives
            if not rows:
                # Try possegrid table directly - rows are in tbody with posseband classes
                posse_table = await page.query_selector("table.possegrid")
                if posse_table:
                    # Rows are in tbody elements with classes like posseband_1, posseband_2
                    rows = await posse_table.query_selector_all("tbody tr.possegrid, tbody tr[class*='posse']")
            
            if not rows:
                # Try all tbody rows in possegrid table
                posse_table = await page.query_selector("table.possegrid")
                if posse_table:
                    rows = await posse_table.query_selector_all("tbody tr")
                    # Filter out header row if present
                    rows = [r for r in rows if await r.get_attribute("class") != "possegrid" or "header" not in (await r.get_attribute("class") or "").lower()]
            
            if not rows:
                # Try the original ID selector
                results_table = await page.query_selector('#ctl00_MainContent_dgResults')
                if results_table:
                    rows = await results_table.query_selector_all("tr:not(.PosseGridHeader)")
            
            if rows:
                print(f"Found {len(rows)} rows to process")
            else:
                print("No rows found - checking page structure...")
                # Debug: check what tables exist
                all_tables = await page.query_selector_all("table")
                print(f"Found {len(all_tables)} table(s) on page")
                for i, table in enumerate(all_tables[:5]):
                    table_class = await table.get_attribute("class")
                    if "posse" in (table_class or "").lower():
                        tbody_rows = await table.query_selector_all("tbody tr")
                        print(f"  Table {i+1} (class={table_class}): {len(tbody_rows)} tbody rows")
            
            for row in rows:
                try:
                    permit_id_elem = await row.query_selector(self.selectors.permit_id)
                    permit_type_elem = await row.query_selector(self.selectors.permit_type)
                    address_elem = await row.query_selector(self.selectors.address)
                    status_elem = await row.query_selector(self.selectors.status)
                    
                    if not all([permit_id_elem, permit_type_elem, address_elem, status_elem]):
                        continue  # Skip incomplete rows
                    
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
                                # Make absolute URL if relative
                                if href.startswith("/"):
                                    detail_url = f"https://webpermit.mecklenburgcountync.gov{href}"
                                elif href.startswith("http"):
                                    detail_url = href
                                else:
                                    # Relative URL - make absolute
                                    detail_url = f"https://webpermit.mecklenburgcountync.gov/{href}"
                    
                    # Extract applicant from detail page if enabled
                    applicant_name = None
                    if self.extract_applicant and detail_url:
                        applicant_name = await self._extract_applicant_from_detail(page, detail_url)
                    
                    permits.append(
                        PermitData(
                            source=self.source,
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
                    # Log but continue - don't fail entire scrape on one bad row
                    print(f"Warning: Failed to parse row: {e}")
                    continue
            
            await browser.close()
        
        return dedupe_permits(permits)


def mecklenburg_county_scraper(
    search_type: str = "project_name",
    search_value: str = "Fire",
    street_number: str | None = None,
) -> MecklenburgPermitScraper:
    """
    Factory for Mecklenburg County (Charlotte, NC) WebPermit portal.
    
    Portal: https://webpermit.mecklenburgcountync.gov/
    Uses ASP.NET postbacks - requires proper navigation sequence from home page.
    
    ⚠️ Note: This portal has database overload issues with broad searches.
    Use specific address searches (e.g., STREET_NUMBER="600" SEARCH_VALUE="Tryon")
    to avoid timeouts.
    
    Args:
        search_type: "project_name" (may timeout) or "address" (recommended)
        search_value: Project name (e.g., "Fire") or street name (e.g., "Tryon")
        street_number: Required for address search (e.g., "600")
    
    Example:
        # Search by address (RECOMMENDED - avoids database overload)
        scraper = mecklenburg_county_scraper(
            search_type="address",
            search_value="Tryon",
            street_number="600"
        )
        
        # Search by project name (may timeout on broad terms)
        scraper = mecklenburg_county_scraper(search_type="project_name", search_value="Fire")
    """
    return MecklenburgPermitScraper(
        search_type=search_type,
        search_value=search_value,
        street_number=street_number,
    )


class SanAntonioFireScraper(PlaywrightPermitScraper):
    """
    Scraper for San Antonio (TX) Accela Fire Module.
    
    Portal: https://aca-prod.accela.com/COSA/Cap/CapHome.aspx?module=Fire&TabName=Home
    Technology: Accela (industry standard, reusable across 100+ cities)
    
    Advantages over Mecklenburg:
    - Dedicated Fire module (better for fire permit discovery)
    - Less prone to database overload
    - Cleaner search interface with Record Type filters
    - Accela pattern is reusable for Dallas, Tampa, San Diego, etc.
    
    Navigation:
    1. Navigate to Fire module home
    2. Click "Search" or navigate to search page
    3. Optionally filter by Record Type (e.g., "Fire Alarm")
    4. Submit search (can leave fields blank for recent permits)
    5. Scrape results table
    """
    
    source = "san_antonio_accela_fire"
    
    def __init__(
        self,
        *,
        record_type: str | None = "Fire Alarm",  # Optional filter: "Fire Alarm", "Fire Sprinkler", etc.
        days_back: int = 30,  # Default to last 30 days if no filters
        max_retries: int = 3,
        base_delay_s: float = 1.0,
        extract_applicant: bool = True,  # Extract applicant from detail pages
    ):
        # Accela Fire module URL
        fire_module_url = "https://aca-prod.accela.com/COSA/Cap/CapHome.aspx?module=Fire&TabName=Home"
        
        # Accela GlobalSearchResults table structure:
        # Column 1: Date
        # Column 2: Record Number (permit_id)
        # Column 3: Record Type (permit_type)
        # Column 4: Module (status)
        # Column 5: Short Notes (address)
        # Column 6: Status (actual status)
        # Column 7: Actions
        selectors = PortalSelectors(
            row="table.aca_grid_table tbody tr:not(.aca_grid_header), table[id*='grid'] tbody tr:not(:first-child)",
            permit_id="td:nth-child(2)",  # Record Number column
            permit_type="td:nth-child(3)",  # Record Type column
            address="td:nth-child(5)",  # Short Notes column (or use Record Type if Short Notes empty)
            status="td:nth-child(6)",  # Status column (or Module if Status empty)
            detail_url="td:nth-child(2) a",  # Link in Record Number column
            applicant_selector='[id*="Applicant"], [id*="Contractor"], label:has-text("Applicant") + *',  # Common patterns
        )
        super().__init__(
            start_url=fire_module_url,
            selectors=selectors,
            max_pages=1,
            max_retries=max_retries,
            base_delay_s=base_delay_s,
            extract_applicant=extract_applicant,
        )
        self.record_type = record_type
        self.days_back = days_back
    
    async def _scrape_full(self) -> list[PermitData]:
        """Override to handle Accela Fire module navigation and search."""
        from playwright.async_api import async_playwright
        
        permits: list[PermitData] = []
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            # Step 1: Navigate directly to search page (Accela pattern)
            search_url = "https://aca-prod.accela.com/COSA/Cap/CapHome.aspx?module=Fire&TabName=Search"
            await page.goto(search_url, wait_until="networkidle", timeout=30000)
            await page.wait_for_timeout(2000)
            
            # Step 2: Select "General Search" from search type dropdown
            search_type_select = await page.query_selector('#ctl00_PlaceHolderMain_ddlSearchType')
            if search_type_select:
                await search_type_select.select_option(label="General Search")
                await page.wait_for_timeout(2000)  # Wait for form to update
            
            # Step 2.5: Fill in date range
            # For golden search (days_back >= 120), use Sept 1 - Oct 31, 2025
            from datetime import datetime, timedelta, date
            if self.days_back >= 120:
                # Golden search: Sept 1 - Oct 31, 2025
                start_date = date(2025, 9, 1)
                end_date = date(2025, 10, 31)
            else:
                end_date = datetime.now()
                start_date = end_date - timedelta(days=self.days_back)
            
            start_date_input = await page.query_selector('#ctl00_PlaceHolderMain_generalSearchForm_txtGSStartDate')
            end_date_input = await page.query_selector('#ctl00_PlaceHolderMain_generalSearchForm_txtGSEndDate')
            
            if start_date_input and end_date_input:
                start_date_str = start_date.strftime("%m/%d/%Y") if isinstance(start_date, date) else start_date.strftime("%m/%d/%Y")
                end_date_str = end_date.strftime("%m/%d/%Y") if isinstance(end_date, date) else end_date.strftime("%m/%d/%Y")
                await start_date_input.fill(start_date_str)
                await end_date_input.fill(end_date_str)
                await page.wait_for_timeout(1000)
            
            # Step 3: Optionally filter by Permit Type (Accela calls it "Permit Type", not "Record Type")
            if self.record_type:
                permit_type_select = await page.query_selector('#ctl00_PlaceHolderMain_generalSearchForm_ddlGSPermitType')
                if permit_type_select:
                    # Try to select by label
                    try:
                        await permit_type_select.select_option(label=self.record_type)
                        await page.wait_for_timeout(1000)
                    except Exception:
                        # If exact match fails, try partial match
                        options = await permit_type_select.query_selector_all("option")
                        for option in options:
                            text = await option.inner_text()
                            if self.record_type.lower() in text.lower():
                                value = await option.get_attribute("value")
                                await permit_type_select.select_option(value=value)
                                await page.wait_for_timeout(1000)
                                break
            
            # Step 4: Submit search
            # Accela uses GlobalSearch JavaScript function - button click triggers this
            # The button has href_disabled and disabled attribute, but GlobalSearch handles the search
            search_btn = await page.query_selector('#btnSearch')
            
            if search_btn:
                # Enable the button first
                await page.evaluate("""
                    const btn = document.getElementById('btnSearch');
                    if (btn) {
                        btn.removeAttribute('disabled');
                        btn.classList.remove('ButtonDisabled');
                        btn.classList.add('gs_go');
                        if (btn.getAttribute('href_disabled')) {
                            btn.href = btn.getAttribute('href_disabled');
                        }
                    }
                """)
                await page.wait_for_timeout(1000)
            
            # Primary method: Call GlobalSearch function directly (most reliable)
            # This is what the button actually triggers
            try:
                search_triggered = await page.evaluate("""
                    (() => {
                        if (typeof GlobalSearch !== 'undefined') {
                            try {
                                // Find search input (may be in date fields for General Search)
                                const startDate = document.getElementById('ctl00_PlaceHolderMain_generalSearchForm_txtGSStartDate')?.value || '';
                                const endDate = document.getElementById('ctl00_PlaceHolderMain_generalSearchForm_txtGSEndDate')?.value || '';
                                const permitType = document.getElementById('ctl00_PlaceHolderMain_generalSearchForm_ddlGSPermitType')?.value || '';
                                
                                // Call GlobalSearch - it handles the form submission
                                new GlobalSearch("txtSearchCondition", "btnSearch", '', '');
                                return 'GlobalSearch called';
                            } catch(e) {
                                return 'Error: ' + e.message;
                            }
                        }
                        return 'GlobalSearch not available';
                    })();
                """)
                print(f"Search trigger result: {search_triggered}")
                await page.wait_for_timeout(2000)
            except Exception as e:
                print(f"GlobalSearch call failed: {e}")
            
            # Fallback: Try button click if GlobalSearch didn't work
            if search_btn:
                try:
                    # Try clicking the button directly
                    await search_btn.click(timeout=5000)
                    await page.wait_for_timeout(2000)
                except:
                    # Try JavaScript click
                    try:
                        await page.evaluate("""
                            const btn = document.getElementById('btnSearch');
                            if (btn) {
                                btn.click();
                            }
                        """)
                        await page.wait_for_timeout(2000)
                    except:
                        pass
            
            # Wait for navigation to results page
            # Accela navigates to GlobalSearchResults.aspx after search
            # Wait for either navigation or update panel content
            try:
                # Wait for navigation to results page (most common case)
                await page.wait_for_url("**/GlobalSearchResults.aspx**", timeout=30000)
                print("Navigated to GlobalSearchResults page")
                await page.wait_for_load_state("networkidle", timeout=30000)
                await page.wait_for_timeout(3000)
            except:
                # Fallback: Check if we're still on search page but update panel has content
                try:
                    await page.wait_for_function(
                        """
                        () => {
                            const panel = document.getElementById('ctl00_PlaceHolderMain_RecordSearchResultInfo_updatePanel');
                            if (!panel) return false;
                            const text = panel.innerText.trim();
                            const hasTable = panel.querySelector('table');
                            if (hasTable) {
                                const rows = hasTable.querySelectorAll('tr');
                                return rows.length > 1;
                            }
                            return text.length > 50;
                        }
                        """,
                        timeout=20000
                    )
                    print("Update panel has content")
                except:
                    # Wait a bit more
                    await page.wait_for_timeout(5000)
            
            # Check if URL changed (Accela might navigate to results page)
            current_url = page.url
            
            # Step 5: Scrape results
            # Check for error or no results
            page_title = await page.title()
            page_url = page.url
            if "Error" in page_title:
                await page.screenshot(path="debug_san_antonio_error.png")
                raise ScraperError(f"San Antonio portal returned error page: {page_title}")
            
            # Debug: Save page HTML for inspection
            page_html = await page.content()
            with open("debug_san_antonio_results_page.html", "w", encoding="utf-8") as f:
                f.write(page_html)
            
            # Check if we're on GlobalSearchResults page - results are directly on this page
            rows = []
            results_from_global_search = False
            
            if "GlobalSearchResults" in page_url:
                print("On GlobalSearchResults page - extracting results directly from page")
                # Wait for page to fully load
                await page.wait_for_load_state("networkidle", timeout=30000)
                await page.wait_for_timeout(3000)
                
                # Look for results table on the results page
                # Try multiple selectors for Accela results tables
                rows = await page.query_selector_all('table.aca_grid_table tbody tr:not(.aca_grid_header), table[id*="grid"] tbody tr:not(:first-child), table[id*="gvPermitList"] tbody tr:not(:first-child)')
                if not rows:
                    rows = await page.query_selector_all('table.aca_grid_table tr:not(.aca_grid_header), table[id*="grid"] tr:not(:first-child)')
                if not rows:
                    rows = await page.query_selector_all('table tbody tr:not(:first-child), table tr:not(:first-child)')
                
                # Check for "no results" message
                page_text = await page.evaluate("() => document.body.innerText")
                if page_text and ("no record" in page_text.lower() or "no result" in page_text.lower() or "0 record" in page_text.lower() or "no data" in page_text.lower()):
                    print("No results message found on results page")
                    await browser.close()
                    return dedupe_permits(permits)
                
                if rows:
                    print(f"Found {len(rows)} rows on GlobalSearchResults page")
                    # Filter out header row - check if first row is a header
                    if rows:
                        first_row = rows[0]
                        first_row_text = await first_row.evaluate("el => el.innerText")
                        # If first row contains header text, skip it
                        if "Record Number" in first_row_text or "Record Type" in first_row_text or "Date" in first_row_text:
                            print(f"  Skipping header row, {len(rows)-1} data rows remaining")
                            rows = rows[1:]
                        else:
                            # Check if it's a th row
                            first_row_tag = await first_row.evaluate("el => el.tagName")
                            if first_row_tag.upper() == "TH" or await first_row.query_selector("th"):
                                print(f"  Skipping header row (th), {len(rows)-1} data rows remaining")
                                rows = rows[1:]
                    
                    if rows:
                        results_from_global_search = True
                        print(f"  Ready to extract {len(rows)} data rows")
                else:
                    print("No rows found on GlobalSearchResults page, checking update panel...")
            
            # If not on results page or no rows found, check update panel (for AJAX results)
            # Only check if we didn't get rows from GlobalSearchResults page
            iframe = None
            frame_locator = None
            if not rows or not results_from_global_search:
                await page.wait_for_timeout(3000)  # Give AJAX time to start
                
                # Accela results are loaded in an iframe - use frame_locator for proper access
                # Check if iframe exists
                iframe_selector = 'iframe#aca_main_iframe, iframe[name*="aca"], iframe[src*="Cap"]'
                iframe = await page.query_selector(iframe_selector)
                
                # Use frame_locator for reliable iframe access
                if iframe:
                    frame_locator = page.frame_locator(iframe_selector)
            
            # Wait for results table to be visible in iframe (if it exists and we don't have results yet)
            results_table_visible = False
            if frame_locator and not results_from_global_search:
                print("Found iframe - waiting for results table in iframe...")
                try:
                    # Wait for table to be visible in iframe
                    # Try multiple table selectors that Accela might use
                    table_selectors = [
                        'table[id*="gvPermitList"]',
                        'table.aca_grid_table',
                        'table[id*="grid"]',
                        'table',
                    ]
                    
                    for table_sel in table_selectors:
                        try:
                            await frame_locator.locator(table_sel).first.wait_for(state="visible", timeout=10000)
                            results_table_visible = True
                            print(f"Results table visible with selector: {table_sel}")
                            break
                        except:
                            continue
                    
                    if results_table_visible:
                        # Extract rows from iframe
                        # Try to get the frame content directly
                        frame = await iframe.content_frame()
                        if frame:
                            # Look for results table in the update panel within iframe
                            results_update_panel = await frame.query_selector('#ctl00_PlaceHolderMain_RecordSearchResultInfo_updatePanel')
                            if results_update_panel:
                                panel_text = await results_update_panel.evaluate("el => el.innerText")
                                if panel_text and ("no record" in panel_text.lower() or "no result" in panel_text.lower() or "0 record" in panel_text.lower()):
                                    print("No results found in search (checked iframe)")
                                    await browser.close()
                                    return dedupe_permits(permits)
                                
                                # Look for table within the update panel in iframe
                                rows = await results_update_panel.query_selector_all('table.aca_grid_table tbody tr:not(.aca_grid_header), table[id*="grid"] tbody tr:not(:first-child), table[id*="gvPermitList"] tbody tr:not(:first-child)')
                                if not rows:
                                    rows = await results_update_panel.query_selector_all('table.aca_grid_table tr:not(.aca_grid_header), table[id*="grid"] tr:not(:first-child), table[id*="gvPermitList"] tr:not(:first-child)')
                                if not rows:
                                    rows = await results_update_panel.query_selector_all('table tbody tr:not(:first-child), table tr:not(:first-child)')
                            
                            # If no rows in update panel, try direct table access in iframe
                            if not rows:
                                rows = await frame.query_selector_all('table.aca_grid_table tbody tr:not(.aca_grid_header), table[id*="grid"] tbody tr:not(:first-child), table[id*="gvPermitList"] tbody tr:not(:first-child)')
                except Exception as e:
                    print(f"Error accessing iframe: {e}")
                    # Fall through to try main page
            
            # Fallback: Try main page (in case results aren't in iframe)
            # Only if we don't already have rows from GlobalSearchResults
            if not rows or not results_from_global_search:
                results_update_panel = await page.query_selector('#ctl00_PlaceHolderMain_RecordSearchResultInfo_updatePanel')
                rows = []
                
                # Check for "no results" message first
                if results_update_panel:
                    panel_text = await results_update_panel.evaluate("el => el.innerText")
                    if panel_text and ("no record" in panel_text.lower() or "no result" in panel_text.lower() or "0 record" in panel_text.lower()):
                        print("No results found in search (checked main page)")
                        await browser.close()
                        return dedupe_permits(permits)
                    
                    # Check if panel is essentially empty
                    panel_html = await results_update_panel.evaluate("el => el.innerHTML")
                    has_table = await results_update_panel.query_selector("table")
                    if not panel_text or (len(panel_text.strip()) < 10 and not has_table):
                        print("Update panel is empty - no results found")
                        await browser.close()
                        return dedupe_permits(permits)
                    
                    # Look for table within the update panel
                    rows = await results_update_panel.query_selector_all('table.aca_grid_table tbody tr:not(.aca_grid_header), table[id*="grid"] tbody tr:not(:first-child), table[id*="gvPermitList"] tbody tr:not(:first-child)')
                    if not rows:
                        rows = await results_update_panel.query_selector_all('table.aca_grid_table tr:not(.aca_grid_header), table[id*="grid"] tr:not(:first-child), table[id*="gvPermitList"] tr:not(:first-child)')
                    if not rows:
                        rows = await results_update_panel.query_selector_all('table tbody tr:not(:first-child), table tr:not(:first-child)')
                
                # If no rows in update panel, try the configured selector
                if not rows:
                    rows = await page.query_selector_all(self.selectors.row)
                
                # If still no rows, try alternative selectors
                if not rows:
                    alt_selectors = [
                        "#ctl00_PlaceHolderMain_RecordSearchResultInfo_updatePanel table.aca_grid_table tbody tr:not(.aca_grid_header)",
                        "#ctl00_PlaceHolderMain_RecordSearchResultInfo_updatePanel table[id*='gvPermitList'] tbody tr:not(:first-child)",
                        "#ctl00_PlaceHolderMain_RecordSearchResultInfo_updatePanel table tbody tr:not(:first-child)",
                        "table.aca_grid_table tbody tr:not(.aca_grid_header)",
                        "table[id*='gvPermitList'] tbody tr:not(:first-child)",
                        "table[id*='grid'] tbody tr:not(:first-child)",
                    ]
                    for alt_selector in alt_selectors:
                        rows = await page.query_selector_all(alt_selector)
                        if rows and len(rows) > 1:  # More than just header
                            print(f"Found {len(rows)} rows with alternative selector: {alt_selector}")
                            break
            
            # If still no rows, the search may have returned no results
            if not rows:
                print("No results table found - search may have returned no results")
                # Debug: check iframe content
                if iframe:
                    try:
                        frame = await iframe.content_frame()
                        if frame:
                            frame_html = await frame.content()
                            has_fire_alarm = "FIRE ALARM" in frame_html.upper() or "FIRE-ALM" in frame_html.upper()
                            print(f"Debug: Iframe contains 'FIRE ALARM': {has_fire_alarm}")
                            if not has_fire_alarm:
                                print("Warning: Iframe does not contain expected fire permit data")
                    except:
                        pass
                await browser.close()
                return dedupe_permits(permits)
            
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
                                    detail_url = f"https://aca-prod.accela.com{href}"
                                elif href.startswith("http"):
                                    detail_url = href
                                else:
                                    detail_url = f"https://aca-prod.accela.com/COSA/{href}"
                    
                    # Extract applicant from detail page if enabled
                    applicant_name = None
                    if self.extract_applicant and detail_url:
                        applicant_name = await self._extract_applicant_from_detail(page, detail_url)
                    
                    permits.append(
                        PermitData(
                            source=self.source,
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


def san_antonio_fire_scraper(
    record_type: str | None = "Fire Alarm",
    days_back: int = 30,
) -> SanAntonioFireScraper:
    """
    Factory for San Antonio (TX) Accela Fire Module scraper.
    
    Portal: https://aca-prod.accela.com/COSA/Cap/CapHome.aspx?module=Fire&TabName=Home
    
    This is the recommended scraper for fire permit discovery because:
    - Dedicated Fire module (better targeting)
    - Accela-based (reusable pattern for 100+ cities)
    - Less prone to database overload than legacy ASP.NET portals
    - Cleaner search interface
    
    Args:
        record_type: Optional filter (e.g., "Fire Alarm", "Fire Sprinkler")
                     If None, searches all fire records
        days_back: Number of days to look back (default 30)
    
    Example:
        # Search for Fire Alarm permits
        scraper = san_antonio_fire_scraper(record_type="Fire Alarm")
        
        # Search all fire records (last 30 days)
        scraper = san_antonio_fire_scraper(record_type=None)
    """
    return SanAntonioFireScraper(
        record_type=record_type,
        days_back=days_back,
    )


