from __future__ import annotations

import asyncio
import os
from datetime import datetime, timedelta, timezone

from src.core.security import tenant_scoped_session
from playwright.async_api import async_playwright
from src.signal_engine.scrapers.base_scraper import dedupe_permits
from src.signal_engine.models import PermitData


async def main():
    """Try San Antonio with 'Search by Record Information' instead of General Search"""
    print("\n" + "="*60)
    print("SAN ANTONIO - SEARCH BY RECORD INFORMATION")
    print("="*60)
    
    tenant_id = os.environ.get("TENANT_ID", "demo")
    
    async with tenant_scoped_session(tenant_id):
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            page = await browser.new_page()
            
            # Navigate to search
            search_url = "https://aca-prod.accela.com/COSA/Cap/CapHome.aspx?module=Fire&TabName=Search"
            await page.goto(search_url, wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_timeout(3000)
            
            # Try "Search by Record Information" instead
            search_type = await page.query_selector('#ctl00_PlaceHolderMain_ddlSearchType')
            if search_type:
                # Get all options
                options = await search_type.query_selector_all("option")
                option_texts = [await opt.inner_text() for opt in options]
                print(f"Available search types: {option_texts}")
                
                # Try "Search by Record Information"
                for option in options:
                    text = await option.inner_text()
                    if "Record Information" in text:
                        await search_type.select_option(label=text)
                        print(f"✓ Selected: {text}")
                        await page.wait_for_timeout(3000)
                        break
            
            # Fill in a permit number search (try a common pattern)
            permit_num_input = await page.query_selector('input[name*="PermitNumber"], input[id*="PermitNumber"], input[name*="RecordNumber"], input[id*="RecordNumber"]')
            if permit_num_input:
                # Try searching for any permit - use a wildcard or common pattern
                await permit_num_input.fill("FIRE")
                print("✓ Filled permit number search: 'FIRE'")
                await page.wait_for_timeout(1000)
            
            # Submit search
            search_btn = await page.query_selector('#btnSearch')
            if search_btn:
                await page.evaluate("""
                    const btn = document.getElementById('btnSearch');
                    if (btn) {
                        btn.removeAttribute('disabled');
                        btn.classList.remove('ButtonDisabled');
                        btn.classList.add('gs_go');
                        btn.href = btn.getAttribute('href_disabled') || '#';
                    }
                """)
                await page.wait_for_timeout(500)
                await page.evaluate("document.getElementById('btnSearch').click()")
                print("✓ Clicked search")
                await page.wait_for_timeout(5000)
                await page.wait_for_load_state("networkidle", timeout=60000)
                await page.wait_for_timeout(3000)
            
            # Check for iframe
            iframe = await page.query_selector('iframe#aca_main_iframe, iframe[name*="aca"]')
            if iframe:
                print("✓ Found iframe, switching context")
                frame = await iframe.content_frame()
                if frame:
                    page = frame
            
            # Check results
            results_panel = await page.query_selector('#ctl00_PlaceHolderMain_RecordSearchResultInfo_updatePanel')
            if results_panel:
                panel_text = await results_panel.evaluate("el => el.innerText")
                print(f"\n📄 Results panel text: {panel_text[:200] if panel_text else '(empty)'}")
                
                # Look for tables
                tables = await results_panel.query_selector_all("table")
                print(f"📊 Found {len(tables)} table(s)")
                
                for i, table in enumerate(tables):
                    rows = await table.query_selector_all("tr")
                    print(f"  Table {i+1}: {len(rows)} rows")
                    
                    if rows and len(rows) > 1:
                        print(f"\n✅ FOUND RESULTS TABLE!")
                        # Extract first few rows
                        for j, row in enumerate(rows[:5], 1):
                            cells = await row.query_selector_all("td, th")
                            cell_texts = []
                            for cell in cells:
                                text = await cell.inner_text()
                                cell_texts.append(text.strip()[:40])
                            print(f"  Row {j}: {cell_texts}")
            
            # Screenshot
            await page.screenshot(path="debug_san_antonio_record_search.png", full_page=True)
            print("\n📸 Screenshot: debug_san_antonio_record_search.png")
            
            print("\n⏳ Keeping browser open for 60 seconds...")
            await page.wait_for_timeout(60000)
            await browser.close()


if __name__ == "__main__":
    asyncio.run(main())

