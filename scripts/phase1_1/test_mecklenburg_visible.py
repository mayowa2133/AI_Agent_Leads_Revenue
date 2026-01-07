from __future__ import annotations

import asyncio
import os
from datetime import datetime, timezone

from src.core.security import tenant_scoped_session
from src.signal_engine.scrapers.permit_scraper import mecklenburg_county_scraper


async def main():
    """
    Test script with visible browser for debugging Mecklenburg County scraper.
    
    Usage:
        TENANT_ID=demo \
        SEARCH_TYPE="project_name" \
        SEARCH_VALUE="Fire" \
        poetry run python scripts/test_mecklenburg_visible.py
    """
    tenant_id = os.environ.get("TENANT_ID", "demo")
    search_type = os.environ.get("SEARCH_TYPE", "project_name")
    search_value = os.environ.get("SEARCH_VALUE", "Fire")
    street_number = os.environ.get("STREET_NUMBER")

    # Temporarily modify the scraper to use visible browser
    from src.signal_engine.scrapers.permit_scraper import MecklenburgPermitScraper
    scraper = MecklenburgPermitScraper(
        search_type=search_type,
        search_value=search_value,
        street_number=street_number,
    )
    
    # Override to use visible browser
    original_scrape = scraper._scrape_full
    async def visible_scrape():
        from playwright.async_api import async_playwright
        permits = []
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)  # VISIBLE
            page = await browser.new_page()
            
            # Copy the navigation logic but with visible browser
            await page.goto(scraper.start_url, wait_until="networkidle", timeout=30000)
            await page.wait_for_timeout(1000)
            print("✓ Loaded home page")
            
            view_permits_link = await page.query_selector('a:has-text("View Permits")')
            if view_permits_link:
                await view_permits_link.click()
                await page.wait_for_load_state("networkidle", timeout=30000)
                await page.wait_for_timeout(1500)
                print("✓ Clicked View Permits")
            
            if search_type == "project_name":
                search_link = await page.query_selector('a:has-text("By Project Name")')
            else:
                search_link = await page.query_selector('a:has-text("By Address")')
            
            if search_link:
                await search_link.click()
                await page.wait_for_load_state("networkidle", timeout=30000)
                await page.wait_for_timeout(2000)
                print("✓ Clicked search type")
            
            # Fill form
            if search_type == "project_name":
                project_input = await page.query_selector('input[name*="ProjectName"]')
                if project_input:
                    await project_input.fill(search_value)
                    print(f"✓ Filled project name: {search_value}")
                    search_field = project_input
            else:
                if street_number:
                    street_num_input = await page.query_selector('input[name*="StreetNumber"]')
                    if street_num_input:
                        await street_num_input.fill(street_number)
                street_input = await page.query_selector('input[name*="StreetName"]')
                if street_input:
                    await street_input.fill(search_value)
                    print(f"✓ Filled street: {street_number or ''} {search_value}")
                    search_field = street_input
            
            await page.wait_for_timeout(500)
            
            # Submit - MUST use explicit button click (Enter key causes page refresh)
            # Mecklenburg uses links with onclick handlers
            submit_btn = await page.query_selector('a[id*="PerformSearch"], a[onclick*="PerformSearch"]')
            if not submit_btn:
                submit_btn = await page.query_selector('#ctl00_MainContent_btnSearch')
            if not submit_btn:
                submit_btn = await page.query_selector('input[type="submit"][value*="Search"]')
            if not submit_btn:
                submit_btn = await page.query_selector('input[type="submit"]')
            
            if submit_btn:
                btn_id = await submit_btn.get_attribute("id")
                btn_text = await submit_btn.inner_text()
                print(f"✓ Found submit button: id={btn_id}, text={btn_text}")
                await submit_btn.click()
                print("✓ Clicked submit button")
            else:
                print("⚠️  Could not find submit button - this will fail")
            
            await page.wait_for_load_state("networkidle", timeout=30000)
            await page.wait_for_timeout(3000)
            print("✓ Waiting for results...")
            
            # Capture debugging information
            page_title = await page.title()
            page_url = page.url
            print(f"\n📄 Page Title: {page_title}")
            print(f"🔗 Page URL: {page_url}")
            
            # Take screenshot
            screenshot_path = "debug_mecklenburg_results.png"
            await page.screenshot(path=screenshot_path, full_page=True)
            print(f"📸 Screenshot saved: {screenshot_path}")
            
            # Check for results table
            results_table = await page.query_selector("#ctl00_MainContent_dgResults")
            if results_table:
                print("✓ Found results table element")
                table_html = await results_table.inner_html()
                # Save HTML for inspection
                with open("debug_mecklenburg_table.html", "w", encoding="utf-8") as f:
                    f.write(table_html)
                print("💾 Table HTML saved: debug_mecklenburg_table.html")
                
                # Count all rows in table
                all_rows = await results_table.query_selector_all("tr")
                print(f"📊 Total rows in table: {len(all_rows)}")
                
                # Check header row
                header_row = await results_table.query_selector("tr.PosseGridHeader")
                if header_row:
                    header_text = await header_row.inner_text()
                    print(f"📋 Header row: {header_text}")
                
                # Check data rows (excluding header)
                data_rows = await results_table.query_selector_all("tr:not(.PosseGridHeader)")
                print(f"📊 Data rows (excluding header): {len(data_rows)}")
                
                # Inspect first few data rows
                for i, row in enumerate(data_rows[:3]):
                    cells = await row.query_selector_all("td")
                    cell_texts = []
                    for cell in cells:
                        text = await cell.inner_text()
                        cell_texts.append(text.strip())
                    print(f"  Row {i+1}: {cell_texts}")
            else:
                print("⚠️  Results table element NOT found with selector: #ctl00_MainContent_dgResults")
                
                # Try to find any table on the page
                all_tables = await page.query_selector_all("table")
                print(f"📊 Found {len(all_tables)} table(s) on page")
                for i, table in enumerate(all_tables):
                    table_id = await table.get_attribute("id")
                    table_class = await table.get_attribute("class")
                    print(f"  Table {i+1}: id={table_id}, class={table_class}")
            
            # Check for results using the configured selector
            rows = await page.query_selector_all(scraper.selectors.row)
            print(f"\n🔍 Found {len(rows)} rows with selector: {scraper.selectors.row}")
            
            # Check for "no results" message
            page_text = await page.inner_text()
            if "no results" in page_text.lower() or "no records" in page_text.lower():
                print("⚠️  Page contains 'no results' or 'no records' message")
            
            # Keep browser open for inspection
            print("\n⏳ Browser will stay open for 30 seconds for inspection...")
            print("   Check the screenshot and HTML files for details.")
            await page.wait_for_timeout(30000)
            
            await browser.close()
        
        return permits
    
    scraper._scrape_full = visible_scrape

    async with tenant_scoped_session(tenant_id):
        search_desc = f"{search_type}='{search_value}'"
        if street_number:
            search_desc += f", street_number='{street_number}'"
        print(f"Testing Mecklenburg County scraper: {search_desc}\n")
        print("Browser will open - watch the navigation sequence...\n")
        
        try:
            permits = await scraper.check_for_updates(last_run=datetime.now(tz=timezone.utc))
            print(f"\n✓ Scraper completed. Found {len(permits)} permit(s)")
        except Exception as e:
            print(f"\n✗ Scraper failed: {e}")
            print("Check the browser window to see where it got stuck.")


if __name__ == "__main__":
    asyncio.run(main())

