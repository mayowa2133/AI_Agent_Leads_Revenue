"""Reusable Accela scraper for permit portals.

Accela is used by 100+ cities including:
- San Antonio, TX (COSA)
- Dallas, TX (DAL)
- Tampa, FL
- San Diego, CA (SANDIEGO)
- Seattle, WA
- And many more...

This scraper can be configured for any Accela portal by providing:
- city_code: The city code in the Accela URL (e.g., "COSA" for San Antonio)
- module: The module name (e.g., "Fire", "Building", "DSD")
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
import re

from src.signal_engine.models import PermitData
from src.signal_engine.scrapers.base_scraper import ScraperError, dedupe_permits
from src.signal_engine.scrapers.status_normalizer import normalize_status


def _is_poor_quality_address(address: str) -> bool:
    """
    Check if an address is poor quality (too short, no numbers, common placeholders).
    
    Args:
        address: Address string to check
        
    Returns:
        True if address is poor quality, False otherwise
    """
    if not address:
        return True
    
    address_lower = address.lower().strip()
    
    # Too short
    if len(address_lower) < 5:
        return True
    
    # Common placeholders or invalid values
    poor_quality_indicators = [
        'n/a', 'none', 'unknown', 'tbd', 'to be determined',
        'tunnel', 'tops', 'see notes', 'see detail', 'click to view',
        'address:', 'location:', 'site:', 'property:',
        'application type:', 'license type:', 'type of work:'
    ]
    
    if any(indicator in address_lower for indicator in poor_quality_indicators):
        return True
    
    # CRITICAL: Filter out section headers like "COMPANY INFORMATION", "PERMIT INFORMATION", etc.
    section_headers = [
        'company information', 'permit information', 'project information',
        'contact information', 'property information', 'general information',
        'record information', 'application information', 'type of work',
        'cashier payments'
    ]
    
    if any(header in address_lower for header in section_headers):
        return True
    
    # Filter out all-caps text that's likely a section header (unless it's a valid address)
    if address.isupper() and len(address) > 20:
        # If it's all caps and long, it's probably a section header unless it has numbers and street words
        if not (any(char.isdigit() for char in address) and 
                any(word in address_lower for word in ['st', 'street', 'ave', 'avenue', 'rd', 'road', 'dr', 'drive', 'blvd', 'boulevard'])):
            return True
    
    # No numbers (addresses usually have street numbers)
    if not any(char.isdigit() for char in address):
        # Allow if it has common address words
        address_words = ['street', 'st', 'avenue', 'ave', 'road', 'rd', 'boulevard', 'blvd', 'drive', 'dr', 'lane', 'ln', 'way', 'court', 'ct']
        if not any(word in address_lower for word in address_words):
            return True
    
    return False


def _normalize_applicant_name(name: str) -> str:
    """
    Normalize applicant/company names by removing common prefixes and collapsing whitespace.
    """
    if not name:
        return ""

    normalized = " ".join(name.split()).strip()
    # Remove common label-style prefixes (e.g., "Organization", "Company Name:")
    normalized = re.sub(
        r"^(organization|org|company name|applicant|contractor|owner)\s*:?\s+",
        "",
        normalized,
        flags=re.IGNORECASE,
    ).strip()
    return normalized


def _is_valid_applicant_name(name: str) -> bool:
    """
    Validate applicant/company names without rejecting ALL-CAPS organizations.
    """
    normalized = _normalize_applicant_name(name)
    if not normalized or len(normalized) < 2 or len(normalized) > 100:
        return False

    lower = normalized.lower()
    invalid_values = {
        "applicant",
        "contractor",
        "owner",
        "organization",
        "company information",
        "individual",
        "person",
        "n/a",
        "none",
        "tbd",
    }
    if lower in invalid_values or lower.endswith(":"):
        return False

    return True
from src.signal_engine.scrapers.permit_scraper import PortalSelectors, PlaywrightPermitScraper


class AccelaScraper(PlaywrightPermitScraper):
    """
    Reusable scraper for Accela-based permit portals.
    
    Works for any city using Accela by configuring:
    - city_code: City code in URL (e.g., "COSA" for San Antonio, "DAL" for Dallas)
    - module: Module name (e.g., "Fire", "Building", "DSD")
    - record_type: Optional filter (e.g., "Fire Alarm", "Fire Sprinkler")
    
    URL Pattern: https://aca-prod.accela.com/{city_code}/Cap/CapHome.aspx?module={module}
    
    Example:
        # San Antonio Fire permits
        scraper = AccelaScraper(
            city_code="COSA",
            module="Fire",
            record_type="Fire Alarm"
        )
        
        # Dallas Building permits
        scraper = AccelaScraper(
            city_code="DAL",
            module="Building"
        )
    """
    
    source = "accela_portal"
    
    def __init__(
        self,
        *,
        city_code: str,  # e.g., "COSA" for San Antonio, "DAL" for Dallas
        module: str = "Fire",  # "Fire", "Building", "DSD", etc.
        record_type: str | None = None,  # Optional filter: "Fire Alarm", "Fire Sprinkler", etc.
        days_back: int = 30,  # Number of days to look back
        max_retries: int = 3,
        base_delay_s: float = 1.0,
        extract_applicant: bool = True,
        max_pages: int = 10,  # Maximum pages to scrape (for pagination)
    ):
        # Build Accela URL
        base_url = f"https://aca-prod.accela.com/{city_code}/Cap/CapHome.aspx"
        fire_module_url = f"{base_url}?module={module}&TabName=Home"
        
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
            permit_id="td:nth-child(2)",  # Record Number column (cell index 1)
            permit_type="td:nth-child(3)",  # Record Type column (cell index 2)
            address="td:nth-child(5)",  # Short Notes column (cell index 4) - may be empty, will try detail page
            status="td:nth-child(7)",  # Status column (cell index 6) - FIXED: was 6, should be 7
            detail_url="td:nth-child(2) a",  # Link in Record Number column
            applicant_selector='[id*="Applicant"], [id*="Contractor"], label:has-text("Applicant") + *',
        )
        super().__init__(
            start_url=fire_module_url,
            selectors=selectors,
            max_pages=1,
            max_retries=max_retries,
            base_delay_s=base_delay_s,
            extract_applicant=extract_applicant,
        )
        self.city_code = city_code
        self.module = module
        self.record_type = record_type
        self.days_back = days_back
        self.base_url = base_url
        self.max_pages = max_pages
    
    async def _scrape_full(self) -> list[PermitData]:
        """Scrape permits with pagination support."""
        from playwright.async_api import async_playwright
        
        permits: list[PermitData] = []
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            # Run the search once (page 1)
            await self._run_search(page)
            
            # Extract permits from all pages
            for page_num in range(1, self.max_pages + 1):
                if page_num > 1:
                    print(f"\n--- Processing page {page_num} ---")
                    # Click Next button to navigate to next page
                    if not await self._click_next_page(page):
                        print("No more pages available, stopping pagination")
                        break
                
                # Extract permits from current page
                page_permits = await self._extract_page_permits(page, page_num)
                if not page_permits:
                    print(f"No permits found on page {page_num}, stopping pagination")
                    break
                
                permits.extend(page_permits)
                print(f"Total permits so far: {len(permits)}")
                
                # If we got fewer permits than expected, might be last page
                if len(page_permits) < 10:  # Less than 10 suggests last page
                    print("Few permits on this page, likely last page")
                    break
            
            await browser.close()
        
        return dedupe_permits(permits)
    
    async def _run_search(self, page) -> None:
        """Run the initial search (only called once)."""
        # Step 1: Navigate to search page
        search_url = f"{self.base_url}?module={self.module}&TabName=Search"
        await page.goto(search_url, wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(2000)
        
        # Step 2: Select "General Search" from search type dropdown
        search_type_select = await page.query_selector('#ctl00_PlaceHolderMain_ddlSearchType')
        if search_type_select:
            await search_type_select.select_option(label="General Search")
            await page.wait_for_timeout(2000)
        
        # Step 3: Fill in date range
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
        
        # Step 4: Optionally filter by Record Type
        if self.record_type:
            permit_type_select = await page.query_selector('#ctl00_PlaceHolderMain_generalSearchForm_ddlGSPermitType')
            if permit_type_select:
                try:
                    await permit_type_select.select_option(label=self.record_type)
                    await page.wait_for_timeout(1000)
                except Exception:
                    # Try partial match
                    options = await permit_type_select.query_selector_all("option")
                    for option in options:
                        text = await option.inner_text()
                        if self.record_type.lower() in text.lower():
                            value = await option.get_attribute("value")
                            await permit_type_select.select_option(value=value)
                            await page.wait_for_timeout(1000)
                            break
        
        # Step 5: Submit search using GlobalSearch function
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
        
        # Step 6: Wait for navigation to results page
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
        
        # Search is complete - results page should be loaded
        # Extraction will happen in _extract_page_permits
    
    async def _click_next_page(self, page) -> bool:
        """Click the Next button to navigate to the next page. Returns True if successful."""
        try:
            # Wait for page to be ready
            await page.wait_for_load_state("networkidle", timeout=10000)
            await page.wait_for_timeout(1000)
            
            # Look for pagination controls
            # Accela typically uses: "Next", ">", or page numbers
            next_button = None
            
            # Try multiple selectors for "Next" button
            next_selectors = [
                'a:has-text("Next")',
                'a:has-text(">")',
                'input[value*="Next"]',
                'button:has-text("Next")',
                'a[id*="Next"]',
                'a[title*="Next"]',
                '.aca_grid_pager a:has-text("Next")',
                '.aca_grid_pager a:has-text(">")',
                'a[onclick*="Next"]',
                'a[href*="Next"]',
            ]
            
            for selector in next_selectors:
                try:
                    next_button = await page.query_selector(selector)
                    if next_button:
                        # Check if button is enabled (not disabled)
                        is_disabled = await next_button.evaluate("""
                            (el) => {
                                return el.disabled || 
                                       el.classList.contains('disabled') || 
                                       el.style.display === 'none' ||
                                       el.getAttribute('disabled') !== null ||
                                       window.getComputedStyle(el).display === 'none';
                            }
                        """)
                        if not is_disabled:
                            print(f"Found Next button with selector: {selector}")
                            break
                        else:
                            next_button = None
                except:
                    continue
            
            # If no "Next" button, try to find page numbers and click the next one
            if not next_button:
                try:
                    # Look for current page number
                    current_page_elem = await page.query_selector('.aca_grid_pager span, .aca_grid_pager .current, .pager .current, [class*="current"]')
                    if current_page_elem:
                        current_page_text = await current_page_elem.inner_text()
                        try:
                            current_page = int(current_page_text.strip())
                            # Look for next page number link
                            next_page = current_page + 1
                            next_page_link = await page.query_selector(f'a:has-text("{next_page}")')
                            if next_page_link:
                                next_button = next_page_link
                                print(f"Found next page link: {next_page}")
                        except:
                            pass
                except:
                    pass
            
            # If we found a next button, click it
            if next_button:
                try:
                    print("Clicking Next button...")
                    await next_button.click()
                    await page.wait_for_load_state("networkidle", timeout=30000)
                    await page.wait_for_timeout(3000)  # Wait for results to load
                    print("Successfully navigated to next page")
                    return True
                except Exception as e:
                    print(f"Error clicking Next button: {e}")
                    return False
            else:
                print("No Next button found")
                return False
                
        except Exception as e:
            print(f"Error in _click_next_page: {e}")
            return False
    
    async def _extract_page_permits(self, page, page_num: int = 1) -> list[PermitData]:
        """Extract permits from the current page."""
        permits: list[PermitData] = []
        
        # Check if we're on results page (after search or after clicking Next)
        page_url = page.url
        page_title = await page.title()
        
        if "Error" in page_title:
            await page.screenshot(path=f"debug_accela_error_{self.city_code}.png")
            raise ScraperError(f"Accela portal returned error page: {page_title}")
        
        # Wait for page to be ready
        await page.wait_for_load_state("networkidle", timeout=30000)
        await page.wait_for_timeout(2000)
        
        # Look for results table
        rows = []
        results_from_global_search = False
        
        if "GlobalSearchResults" in page_url:
            print("On GlobalSearchResults page - extracting results directly from page")
            rows = await page.query_selector_all('table.aca_grid_table tbody tr:not(.aca_grid_header), table[id*="grid"] tbody tr:not(:first-child), table[id*="gvPermitList"] tbody tr:not(:first-child)')
            if not rows:
                rows = await page.query_selector_all('table.aca_grid_table tr:not(.aca_grid_header), table[id*="grid"] tr:not(:first-child)')
            if not rows:
                rows = await page.query_selector_all('table tbody tr:not(:first-child), table tr:not(:first-child)')
            
            # Check for "no results" message
            page_text = await page.evaluate("() => document.body.innerText")
            if page_text and any(term in page_text.lower() for term in ["no record", "no result", "0 record", "no data"]):
                print("No results message found on results page")
                return permits
            
            if rows:
                print(f"Found {len(rows)} rows on GlobalSearchResults page")
                # Filter out header row
                if rows:
                    first_row = rows[0]
                    first_row_text = await first_row.evaluate("el => el.innerText")
                    if any(term in first_row_text for term in ["Record Number", "Record Type", "Date"]):
                        print(f"  Skipping header row, {len(rows)-1} data rows remaining")
                        rows = rows[1:]
                    else:
                        first_row_tag = await first_row.evaluate("el => el.tagName")
                        if first_row_tag.upper() == "TH" or await first_row.query_selector("th"):
                            print(f"  Skipping header row (th), {len(rows)-1} data rows remaining")
                            rows = rows[1:]
                
                if rows:
                    results_from_global_search = True
                    print(f"  Ready to extract {len(rows)} data rows")
        
        # If no rows found, return empty list
        if not rows:
            print("No rows found on results page")
            return permits
        
        # Extract permit data from rows and extract detail page data
        print(f"Extracting data from {len(rows)} rows...")
        permits: list[PermitData] = []
        
        for idx, row in enumerate(rows):
            try:
                row_text = await row.evaluate("el => el.innerText")
                
                # Skip header rows
                if any(term in row_text for term in ["Record Number", "Record Type", "Date"]):
                    continue
                
                # Extract using query_selector (address is optional - we can get it from detail page)
                permit_id_elem = await row.query_selector(self.selectors.permit_id)
                permit_type_elem = await row.query_selector(self.selectors.permit_type)
                address_elem = await row.query_selector(self.selectors.address)
                status_elem = await row.query_selector(self.selectors.status)
                
                # Require permit_id and permit_type, but address and status are optional
                if permit_id_elem and permit_type_elem:
                    permit_id = (await permit_id_elem.inner_text()).strip()
                    permit_type = (await permit_type_elem.inner_text()).strip()
                    address = (await address_elem.inner_text()).strip() if address_elem else ""
                    status = (await status_elem.inner_text()).strip() if status_elem else ""
                    
                    # Skip if empty or looks like header
                    if not permit_id or not permit_type or permit_id == "Record Number" or permit_id == "Date":
                        if idx < 3:  # Only log for first few rows to avoid spam
                            print(f"  ⚠ Skipping row {idx}: permit_id='{permit_id}', permit_type='{permit_type}'")
                        continue
                    
                    # Successfully extracted basic data
                    if idx < 3:  # Only log for first few rows
                        print(f"  ✓ Extracted row {idx}: {permit_id} - {permit_type} - Status: {status}")
                    
                    # Get detail link element (we'll need it for clicking)
                    detail_link = None
                    detail_url = None
                    if self.selectors.detail_url:
                        detail_link = await row.query_selector(self.selectors.detail_url)
                        if detail_link:
                            href = await detail_link.get_attribute("href")
                            if href:
                                if href.startswith("/"):
                                    detail_url = f"https://aca-prod.accela.com{href}"
                                elif href.startswith("http"):
                                    detail_url = href
                                elif not href.startswith("javascript:"):
                                    detail_url = f"https://aca-prod.accela.com/{self.city_code}/{href}"
                    
                    # Extract applicant and address from detail page if enabled
                    applicant_name = None
                    
                    # Extract applicant and address from detail page if enabled
                    # NOTE: For now, we skip detail page extraction during initial loop to avoid breaking navigation
                    # Detail page extraction can be done in a second pass if needed
                    # This prevents issues with JavaScript postbacks breaking the row iteration
                    
                    # Normalize status
                    normalized_status = normalize_status(status)
                    
                    # Extract company name from address field if it contains "Company Name:"
                    # Do this BEFORE filtering out poor quality addresses
                    extracted_company = applicant_name  # Start with what we have
                    # Debug: Check if address contains Company Name
                    if idx < 3 and address:
                        print(f"  🔍 Row {idx} address preview: {address[:100]}")
                    if not extracted_company and address and 'Company Name' in address:
                        import re
                        company_match = re.search(r'Company\s+Name\s*:\s*([^:\n]+?)(?:\s*License\s*Type|LicenseType|$)', address, re.IGNORECASE)
                        if company_match:
                            company_name = company_match.group(1).strip()
                            company_name = ' '.join(company_name.split())
                            company_name = re.sub(r'\s*License\s*Type.*$', '', company_name, flags=re.IGNORECASE)
                            company_name = re.sub(r'License.*$', '', company_name, flags=re.IGNORECASE)
                            company_name = _normalize_applicant_name(company_name)
                            if _is_valid_applicant_name(company_name):
                                extracted_company = company_name
                                if idx < 3:
                                    print(f"  ✓ Extracted company name from address field: {company_name[:50]}")
                    
                    # Build final detail_url (for storage, not navigation)
                    # Store JavaScript postbacks too - we'll handle them in second pass
                    final_detail_url = None
                    if detail_url:
                        # Store JavaScript postbacks as-is (we'll handle them in second pass)
                        if detail_url.startswith('javascript:') or '__doPostBack' in detail_url:
                            final_detail_url = detail_url  # Store it so we can find the link later
                        elif not detail_url.startswith('javascript:'):
                            final_detail_url = detail_url
                    elif detail_link:
                        # Try to get a usable URL from the link
                        try:
                            href = await detail_link.get_attribute("href")
                            if href:
                                if href.startswith('javascript:') or '__doPostBack' in href:
                                    final_detail_url = href  # Store JavaScript postback
                                elif href.startswith("/"):
                                    final_detail_url = f"https://aca-prod.accela.com{href}"
                                elif href.startswith("http"):
                                    final_detail_url = href
                        except:
                            pass
                    
                    try:
                        # Extract company name from address field if it contains "Company Name:"
                        # Do this BEFORE filtering out poor quality addresses
                        extracted_company = applicant_name  # Start with what we have
                        if not extracted_company and address and 'Company Name' in address:
                            import re
                            company_match = re.search(r'Company\s+Name\s*:\s*([^:\n]+?)(?:\s*License\s*Type|LicenseType|$)', address, re.IGNORECASE)
                            if company_match:
                                company_name = company_match.group(1).strip()
                                company_name = ' '.join(company_name.split())
                                company_name = re.sub(r'\s*License\s*Type.*$', '', company_name, flags=re.IGNORECASE)
                                company_name = re.sub(r'License.*$', '', company_name, flags=re.IGNORECASE)
                                company_name = _normalize_applicant_name(company_name)
                            if _is_valid_applicant_name(company_name):
                                    extracted_company = company_name
                        
                        permit_data = PermitData(
                            source=f"{self.source}_{self.city_code}_{self.module.lower()}",
                            permit_id=permit_id,
                            permit_type=permit_type,
                            address=address if address and not _is_poor_quality_address(address) else "",
                            building_type=None,  # TODO: Extract from detail page
                            status=normalized_status,
                            applicant_name=extracted_company,  # Use extracted company name if found
                            issued_date=None,  # TODO: Extract from detail page
                            detail_url=final_detail_url,
                        )
                        permits.append(permit_data)
                        if idx < 3:  # Only log for first few rows
                            print(f"  ✓ Added permit {permit_id} to list (total: {len(permits)})")
                    except Exception as create_error:
                        print(f"  ⚠ Failed to create PermitData for {permit_id}: {create_error}")
                        raise  # Re-raise to trigger fallback
                else:
                    # Try evaluate fallback if selectors didn't work
                    print(f"  ⚠ Selectors didn't match for row {idx}, trying evaluate fallback...")
                    raise Exception("Selectors didn't match - trigger fallback")
            except Exception as e:
                if idx < 3:  # Only log for first few rows
                    print(f"  ⚠ Exception in row {idx}: {e}")
                # DOM context error - try evaluate as fallback
                try:
                    row_data = await row.evaluate("""
                        (row) => {
                            const cells = row.querySelectorAll('td');
                            if (cells.length < 3) return null;
                            
                            // Column structure: 0=Date, 1=Record Number, 2=Record Type, 3=Module, 4=Short Notes, 5=Project Name, 6=Status
                            const permitId = cells[1] ? cells[1].innerText.trim() : '';
                            const permitType = cells[2] ? cells[2].innerText.trim() : '';
                            if (!permitId || !permitType || permitId === 'Record Number') return null;
                            
                            // Get address from column 5 (index 4) - Short Notes (may be empty)
                            let address = '';
                            if (cells[4]) {
                                address = cells[4].innerText.trim();
                            }
                            
                            // Get status from column 7 (index 6) - FIXED: was index 5, should be 6
                            let status = '';
                            if (cells[6]) {
                                status = cells[6].innerText.trim();
                            }
                            
                            // Get detail URL from link in Record Number cell (cells[1])
                            let detailUrl = null;
                            if (cells[1]) {
                                const link = cells[1].querySelector('a');
                                if (link) {
                                    detailUrl = link.href || link.getAttribute('href') || null;
                                }
                            }
                            
                            return {
                                permit_id: permitId,
                                permit_type: permitType,
                                address: address || '',
                                status: status || '',
                                detail_url: detailUrl
                            };
                        }
                    """)
                    if row_data and row_data.get('permit_id'):
                        print(f"  ✓ Evaluate fallback extracted: {row_data['permit_id']}")
                        permit_id = row_data['permit_id']
                        permit_type = row_data['permit_type']
                        address = row_data.get('address', '')
                        status = row_data.get('status', '')
                        
                        # Filter poor quality addresses
                        if _is_poor_quality_address(address):
                            address = None
                        
                        detail_url = row_data.get('detail_url')
                        if detail_url and not detail_url.startswith('javascript:'):
                            if detail_url.startswith("/"):
                                detail_url = f"https://aca-prod.accela.com{detail_url}"
                            elif not detail_url.startswith("http"):
                                detail_url = f"https://aca-prod.accela.com/{self.city_code}/{detail_url}"
                        else:
                            detail_url = None
                        
                        permits.append(
                            PermitData(
                                source=f"{self.source}_{self.city_code}_{self.module.lower()}",
                                permit_id=permit_id,
                                permit_type=permit_type,
                                address=address,
                                building_type=None,
                                status=normalize_status(status),
                                applicant_name=None,  # Can't extract from detail page in fallback mode
                                issued_date=None,
                                detail_url=detail_url,
                            )
                        )
                except Exception as fallback_error:
                    print(f"  ⚠ Evaluate fallback also failed for row {idx}: {fallback_error}")
                    continue
        
        print(f"Extracted {len(permits)} permits from {len(rows)} rows")
        
        # Second pass: Extract addresses and applicant names from detail pages
        needs_enrichment = (
            self.extract_applicant and any(not p.applicant_name for p in permits)
        ) or any(not p.address or len(p.address.strip()) < 5 or _is_poor_quality_address(p.address) for p in permits)
        
        if permits and needs_enrichment:
            print(f"\nStarting second pass: Extracting addresses and applicants from detail pages...")
            print(f"  Permits needing enrichment: {sum(1 for p in permits if (not p.address or len(p.address.strip()) < 5) or (self.extract_applicant and not p.applicant_name))}")
            await self._extract_detail_page_data(page, permits)
        
        print(f"Successfully extracted {len(permits)} permits from page {page_num}")
        return permits
    
    async def _extract_detail_page_data(self, page, permits: list[PermitData]) -> None:
        """
        Second pass: Extract addresses and applicant names from detail pages.
        
        Args:
            page: Playwright page object
            permits: List of permits to enrich with detail page data
        """
        current_url = page.url
        enriched_count = 0
        
        for i, permit in enumerate(permits, 1):
            # Skip if we already have both address and applicant
            if permit.address and len(permit.address.strip()) > 5 and permit.applicant_name:
                continue
            
            # Need detail URL or be able to find link on results page
            # For JavaScript postbacks, detail_url might be set but we still need to find the link
            has_detail_url = permit.detail_url and not permit.detail_url.startswith('javascript:')
            is_javascript_postback = permit.detail_url and (permit.detail_url.startswith('javascript:') or '__doPostBack' in str(permit.detail_url))
            
            if not permit.detail_url:
                if i <= 3:  # Only log for first few
                    print(f"  ⚠ [{i}/{len(permits)}] No detail URL for {permit.permit_id}")
                continue
            
            if i <= 3:  # Debug logging for first few
                print(f"  🔍 [{i}/{len(permits)}] Processing {permit.permit_id}, detail_url type: {'javascript' if is_javascript_postback else 'regular' if has_detail_url else 'none'}")
            
            try:
                # Check if it's a JavaScript postback
                is_javascript = permit.detail_url.startswith('javascript:') or '__doPostBack' in permit.detail_url
                
                if is_javascript:
                    # For JavaScript postbacks, we need to find the link on the results page
                    # Navigate back to results page first
                    if page.url != current_url:
                        await page.goto(current_url, wait_until="networkidle", timeout=15000)
                        await page.wait_for_timeout(2000)
                    
                    # Find the permit row by permit_id
                    # Try multiple selectors to find the table
                    rows = await page.query_selector_all('table.aca_grid_table tbody tr:not(.aca_grid_header), table[id*="grid"] tbody tr:not(:first-child), table[id*="gvPermitList"] tbody tr:not(:first-child)')
                    if not rows:
                        rows = await page.query_selector_all('table.aca_grid_table tr:not(.aca_grid_header), table[id*="grid"] tr:not(:first-child)')
                    if not rows:
                        rows = await page.query_selector_all('table tbody tr:not(:first-child), table tr:not(:first-child)')
                    
                    detail_link = None
                    
                    # Normalize permit_id for comparison (remove extra whitespace, case-insensitive)
                    target_permit_id = permit.permit_id.strip().upper()
                    
                    for row in rows:
                        try:
                            # Try column 2 first (most common location for permit_id)
                            permit_id_elem = await row.query_selector('td:nth-child(2)')
                            if not permit_id_elem:
                                # Try column 1 as fallback
                                permit_id_elem = await row.query_selector('td:nth-child(1)')
                            
                            if permit_id_elem:
                                row_permit_id = (await permit_id_elem.inner_text()).strip().upper()
                                
                                # More flexible matching - check if permit_id is contained in the cell
                                # This handles cases where there might be extra text or formatting
                                if target_permit_id == row_permit_id or target_permit_id in row_permit_id or row_permit_id in target_permit_id:
                                    # Found the row! Now find the link
                                    # Try column 2 first (most common)
                                    detail_link = await row.query_selector('td:nth-child(2) a')
                                    if not detail_link:
                                        # Try column 1
                                        detail_link = await row.query_selector('td:nth-child(1) a')
                                    if not detail_link:
                                        # Try any link in the row
                                        detail_link = await row.query_selector('a[href*="doPostBack"], a[href*="CapDetail"], a[href*="Detail"]')
                                    
                                    if detail_link:
                                        if i <= 3:  # Debug for first few
                                            print(f"  ✓ Found detail link for {permit.permit_id} (matched: {row_permit_id})")
                                        break
                        except Exception as e:
                            if i <= 3:  # Debug for first few
                                pass  # Don't spam errors
                            continue
                    
                    # If still not found, try XPath-based search (more reliable for complex structures)
                    if not detail_link:
                        try:
                            # Use XPath to find row containing permit_id, then get link
                            xpath_result = await page.evaluate(f"""
                                () => {{
                                    const permitId = '{permit.permit_id}';
                                    const rows = document.querySelectorAll('table tr');
                                    for (const row of rows) {{
                                        const cells = row.querySelectorAll('td');
                                        for (const cell of cells) {{
                                            const text = (cell.textContent || cell.innerText || '').trim().toUpperCase();
                                            if (text.includes(permitId.toUpperCase()) || permitId.toUpperCase().includes(text)) {{
                                                // Found the row, now find the link
                                                const link = row.querySelector('a[href*="doPostBack"], a[href*="CapDetail"], a[href*="Detail"]');
                                                if (link) {{
                                                    return link.href || link.getAttribute('href') || '';
                                                }}
                                            }}
                                        }}
                                    }}
                                    return null;
                                }}
                            """)
                            
                            if xpath_result:
                                # Find the link element by href
                                detail_link = await page.query_selector(f'a[href*="{xpath_result[:50]}"]')
                                if detail_link and i <= 3:
                                    print(f"  ✓ Found detail link via XPath for {permit.permit_id}")
                        except Exception:
                            pass  # XPath fallback failed, continue
                    
                    if detail_link:
                        # Click the link to open detail page
                        # Use force=True to bypass visibility checks (this was working before)
                        try:
                            # Try ElementHandle click with force=True first (most reliable)
                            # This bypasses visibility and actionability checks
                            try:
                                async with page.expect_navigation(timeout=20000, wait_until="networkidle"):
                                    await detail_link.click(force=True, timeout=10000)
                                await page.wait_for_timeout(2000)
                            except Exception as click_error:
                                # Force click failed, try JavaScript click as fallback
                                if i <= 3:
                                    print(f"  ⚠ [{i}/{len(permits)}] Force click failed for {permit.permit_id}, trying JavaScript click...")
                                
                                # Find and click using JavaScript (bypasses all checks)
                                try:
                                    clicked = await page.evaluate(f"""
                                        () => {{
                                            const permitId = '{permit.permit_id}';
                                            const rows = document.querySelectorAll('table tr');
                                            
                                            for (const row of rows) {{
                                                const cells = row.querySelectorAll('td');
                                                for (const cell of cells) {{
                                                    const text = (cell.textContent || cell.innerText || '').trim().toUpperCase();
                                                    if (text.includes(permitId.toUpperCase()) || permitId.toUpperCase().includes(text)) {{
                                                        const link = row.querySelector('a[href*="doPostBack"], a[onclick*="doPostBack"], a[href*="CapDetail"], a[href*="Detail"]');
                                                        if (link) {{
                                                            link.click();
                                                            return true;
                                                        }}
                                                    }}
                                                }}
                                            }}
                                            return false;
                                        }}
                                    """)
                                    
                                    if not clicked:
                                        raise Exception("Could not find link via JavaScript")
                                except Exception as eval_error:
                                    # "Execution context was destroyed" means navigation happened - this is success!
                                    if "Execution context was destroyed" in str(eval_error) or "navigation" in str(eval_error).lower():
                                        # Navigation happened, wait for page to load
                                        await page.wait_for_timeout(3000)
                                        await page.wait_for_load_state("networkidle", timeout=10000)
                                        await page.wait_for_timeout(2000)
                                    else:
                                        raise  # Re-raise if it's a different error
                                
                                # Wait for navigation - be more flexible with detection
                                # JavaScript clicks can trigger navigation that takes time
                                navigation_success = False
                                for attempt in range(6):  # Try up to 6 times (12 seconds total)
                                    await page.wait_for_timeout(2000)
                                    current_url = page.url
                                    if 'CapDetail' in current_url or 'Detail' in current_url:
                                        # Successfully navigated!
                                        navigation_success = True
                                        await page.wait_for_load_state("networkidle", timeout=10000)
                                        await page.wait_for_timeout(2000)
                                        break
                                
                                if not navigation_success:
                                    # Still not navigated after multiple attempts
                                    raise Exception("Navigation timeout - still on results page")
                        except Exception as click_error:
                            if i <= 3:
                                print(f"  ⚠ [{i}/{len(permits)}] Failed to click detail link for {permit.permit_id}: {click_error}")
                            continue
                        
                        # Check if we're on an error page - if so, try waiting a bit more
                        current_url = page.url
                        if "Error.aspx" in current_url:
                            # Sometimes Accela redirects through error page - wait a bit more
                            await page.wait_for_timeout(3000)
                            # Check if URL changed - sometimes it redirects to the actual detail page
                            if "Error.aspx" in page.url:
                                # Try to find and click a "Back" or "Continue" button
                                try:
                                    back_button = await page.query_selector('a[href*="CapHome"], input[value*="Back"], input[value*="Continue"]')
                                    if back_button:
                                        await back_button.click()
                                        await page.wait_for_timeout(2000)
                                except:
                                    pass
                                
                                # Check again if we're still on error page
                                if "Error.aspx" in page.url:
                                    if i <= 3:
                                        print(f"  ⚠ [{i}/{len(permits)}] Still on error page after click for {permit.permit_id}")
                                    continue
                    else:
                        if i <= 3:  # Only log for first few
                            print(f"  ⚠ Could not find detail link for {permit.permit_id} (found {len(rows)} rows on page)")
                        continue
                else:
                    # Regular URL - navigate directly
                    await page.goto(permit.detail_url, wait_until="networkidle", timeout=15000)
                    await page.wait_for_timeout(2000)
                
                # Extract data from detail page
                detail_url = page.url
                
                # Extract applicant if needed
                if self.extract_applicant and not permit.applicant_name:
                    try:
                        # First, try to extract from address field if it contains "Company Name"
                        # This is a fallback since address extraction might have already captured it
                        if permit.address and 'Company Name' in permit.address:
                            import re
                            company_match = re.search(r'Company\s+Name\s*:\s*([^:\n]+?)(?:\s*License\s*Type|LicenseType|$)', permit.address, re.IGNORECASE)
                            if company_match:
                                company_name = company_match.group(1).strip()
                                company_name = ' '.join(company_name.split())
                                company_name = re.sub(r'\s*License\s*Type.*$', '', company_name, flags=re.IGNORECASE)
                                company_name = re.sub(r'License.*$', '', company_name, flags=re.IGNORECASE)
                                company_name = _normalize_applicant_name(company_name)
                                if _is_valid_applicant_name(company_name):
                                    permit.applicant_name = company_name
                                    print(f"  ✓ [{i}/{len(permits)}] Extracted applicant from address field for {permit.permit_id}: {company_name[:50]}")
                                    # Skip detail page extraction if we got it from address
                                    continue
                        
                        # Debug: Check if we're on detail page
                        current_url = page.url
                        if i <= 3:
                            print(f"  🔍 [{i}/{len(permits)}] Extracting applicant from {permit.permit_id}, current URL: {current_url[:80]}")
                        
                        applicant_name = await self._extract_applicant_from_detail(page, detail_url)
                        if applicant_name:
                            # Validate it's not a label (AccelaScraper inherits from PlaywrightPermitScraper)
                            normalized_applicant = _normalize_applicant_name(applicant_name)
                            if _is_valid_applicant_name(normalized_applicant):
                                permit.applicant_name = normalized_applicant
                                print(f"  ✓ [{i}/{len(permits)}] Extracted applicant for {permit.permit_id}: {normalized_applicant[:50]}")
                            elif i <= 3:
                                print(f"  ⚠ [{i}/{len(permits)}] Filtered out label for {permit.permit_id}: '{applicant_name[:50]}'")
                        elif i <= 3:
                            print(f"  ⚠ [{i}/{len(permits)}] No applicant extracted for {permit.permit_id}")
                    except Exception as e:
                        if i <= 3:  # Only log errors for first few
                            print(f"  ⚠ [{i}/{len(permits)}] Failed to extract applicant for {permit.permit_id}: {e}")
                
                # Extract address if missing or poor quality
                if not permit.address or len(permit.address.strip()) < 5 or _is_poor_quality_address(permit.address):
                    try:
                        detail_address = await self._extract_address_from_detail(page, detail_url)
                        if detail_address:
                            # Clean up address: remove "Location" prefix and leading/trailing whitespace
                            cleaned_address = detail_address.strip()
                            # Remove "Location" prefix if present (case-insensitive)
                            if cleaned_address.lower().startswith('location'):
                                cleaned_address = cleaned_address[8:].strip()  # Remove "Location" (8 chars)
                                # Remove leading colon, dash, newlines, tabs, or whitespace
                                cleaned_address = cleaned_address.lstrip(':-\t\n\r ')
                            detail_address = cleaned_address
                            # CRITICAL: Extract company name from address field BEFORE filtering
                            # The address field might contain "Company Name:..." text
                            if not permit.applicant_name and 'Company Name' in detail_address:
                                import re
                                company_match = re.search(r'Company\s+Name\s*:\s*([^:\n]+?)(?:\s*License\s*Type|LicenseType|$)', detail_address, re.IGNORECASE)
                                if company_match:
                                    company_name = company_match.group(1).strip()
                                    company_name = ' '.join(company_name.split())
                                    company_name = re.sub(r'\s*License\s*Type.*$', '', company_name, flags=re.IGNORECASE)
                                    company_name = re.sub(r'License.*$', '', company_name, flags=re.IGNORECASE)
                                    company_name = _normalize_applicant_name(company_name)
                                    if _is_valid_applicant_name(company_name):
                                        permit.applicant_name = company_name
                                        print(f"  ✓ [{i}/{len(permits)}] Extracted company name from address field for {permit.permit_id}: {company_name[:50]}")
                            
                            # Validate it's not a label and is a good address
                            # Allow addresses ending with "*" (common in permit systems)
                            # Strip "*" for validation but keep original
                            address_for_validation = detail_address.rstrip(' *').strip()
                            if (not _is_poor_quality_address(address_for_validation) and 
                                not self._is_label_text(address_for_validation)):
                                permit.address = detail_address  # Keep original with "*" if present
                                print(f"  ✓ [{i}/{len(permits)}] Extracted address for {permit.permit_id}: {detail_address[:50]}")
                            elif i <= 3:
                                print(f"  ⚠ [{i}/{len(permits)}] Filtered out label/poor address for {permit.permit_id}: '{detail_address[:50]}' (validation: poor_quality={_is_poor_quality_address(address_for_validation)}, is_label={self._is_label_text(address_for_validation)})")
                    except Exception as e:
                        if i <= 3:  # Only log errors for first few
                            print(f"  ⚠ [{i}/{len(permits)}] Failed to extract address for {permit.permit_id}: {e}")
                
                enriched_count += 1
                
                # Navigate back to results page
                if page.url != current_url:
                    await page.goto(current_url, wait_until="networkidle", timeout=15000)
                    await page.wait_for_timeout(2000)
                
            except Exception as e:
                print(f"  ⚠ [{i}/{len(permits)}] Error processing detail page for {permit.permit_id}: {e}")
                # Try to navigate back to results page
                try:
                    if page.url != current_url:
                        await page.goto(current_url, wait_until="networkidle", timeout=15000)
                        await page.wait_for_timeout(2000)
                except:
                    pass
                continue
        
        print(f"\n✅ Second pass complete: Enriched {enriched_count}/{len(permits)} permits with detail page data")
        
        # Post-processing: Extract company names from address fields if applicant name is still missing
        # This handles cases where address extraction captured "Company Name:..." text
        import re
        company_extracted = 0
        for permit in permits:
            if not permit.applicant_name and permit.address and 'Company Name' in permit.address:
                company_match = re.search(r'Company\s+Name\s*:\s*([^:\n]+?)(?:\s*License\s*Type|LicenseType|$)', permit.address, re.IGNORECASE)
                if company_match:
                    company_name = company_match.group(1).strip()
                    company_name = ' '.join(company_name.split())
                    company_name = re.sub(r'\s*License\s*Type.*$', '', company_name, flags=re.IGNORECASE)
                    company_name = re.sub(r'License.*$', '', company_name, flags=re.IGNORECASE)
                    company_name = _normalize_applicant_name(company_name)
                    if _is_valid_applicant_name(company_name):
                        permit.applicant_name = company_name
                        company_extracted += 1
                        print(f"  ✓ Extracted company name from address field for {permit.permit_id}: {company_name[:50]}")
        
        if company_extracted > 0:
            print(f"✅ Post-processing: Extracted {company_extracted} company names from address fields")


def create_accela_scraper(
    city_code: str,
    module: str = "Fire",
    record_type: str | None = None,
    days_back: int = 30,
    max_pages: int = 1,
    extract_applicant: bool = True,  # Enable by default for better data quality
) -> AccelaScraper:
    """
    Factory function to create an Accela scraper.
    
    Args:
        city_code: City code in Accela URL (e.g., "COSA" for San Antonio)
        module: Module name (e.g., "Fire", "Building", "DSD")
        record_type: Optional filter (e.g., "Fire Alarm", "Fire Sprinkler")
        days_back: Number of days to look back (default 30)
    
    Returns:
        Configured AccelaScraper instance
    
    Example:
        # San Antonio Fire permits
        scraper = create_accela_scraper("COSA", "Fire", "Fire Alarm")
        
        # Dallas Building permits
        scraper = create_accela_scraper("DAL", "Building")
    """
    return AccelaScraper(
        city_code=city_code,
        module=module,
        record_type=record_type,
        days_back=days_back,
        max_pages=max_pages,
        extract_applicant=extract_applicant,
    )
