from __future__ import annotations

import asyncio
import os
from datetime import datetime, timedelta, timezone

from src.core.security import tenant_scoped_session
from playwright.async_api import async_playwright


async def test_san_antonio_broad_search():
    """Try very broad San Antonio search to get ANY results"""
    print("\n" + "="*60)
    print("SAN ANTONIO - BROAD SEARCH (ANY RESULTS)")
    print("="*60)
    
    tenant_id = os.environ.get("TENANT_ID", "demo")
    
    async with tenant_scoped_session(tenant_id):
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)  # Visible for inspection
            page = await browser.new_page()
            
            # Navigate to search
            search_url = "https://aca-prod.accela.com/COSA/Cap/CapHome.aspx?module=Fire&TabName=Search"
            await page.goto(search_url, wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_timeout(3000)
            
            # Select General Search
            search_type = await page.query_selector('#ctl00_PlaceHolderMain_ddlSearchType')
            if search_type:
                await search_type.select_option(label="General Search")
                await page.wait_for_timeout(2000)
            
            # Try a very broad date range - last 2 years
            end_date = datetime.now()
            start_date = end_date - timedelta(days=730)
            
            start_input = await page.query_selector('#ctl00_PlaceHolderMain_generalSearchForm_txtGSStartDate')
            end_input = await page.query_selector('#ctl00_PlaceHolderMain_generalSearchForm_txtGSEndDate')
            
            if start_input and end_input:
                await start_input.fill(start_date.strftime("%m/%d/%Y"))
                await end_input.fill(end_date.strftime("%m/%d/%Y"))
                print(f"✓ Filled date range: {start_date.strftime('%m/%d/%Y')} to {end_date.strftime('%m/%d/%Y')}")
                await page.wait_for_timeout(1000)
            
            # DON'T select a permit type - leave it as "All"
            print("✓ Leaving permit type as 'All' (no filter)")
            
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
                print("✓ Clicked search button")
                await page.wait_for_timeout(5000)  # Wait longer
                await page.wait_for_load_state("networkidle", timeout=60000)
                await page.wait_for_timeout(5000)
            
            # Check for iframe
            iframe = await page.query_selector('iframe#aca_main_iframe, iframe[name*="aca"]')
            if iframe:
                print("✓ Found iframe, switching context")
                frame = await iframe.content_frame()
                if frame:
                    page = frame
            
            # Inspect results panel
            results_panel = await page.query_selector('#ctl00_PlaceHolderMain_RecordSearchResultInfo_updatePanel')
            if results_panel:
                panel_text = await results_panel.evaluate("el => el.innerText")
                panel_html = await results_panel.evaluate("el => el.innerHTML")
                
                print(f"\n📄 Results panel text (first 500 chars):")
                print(panel_text[:500] if panel_text else "(empty)")
                
                # Save HTML
                with open("debug_san_antonio_actual_results.html", "w", encoding="utf-8") as f:
                    f.write(panel_html)
                print("\n💾 Saved results panel HTML: debug_san_antonio_actual_results.html")
                
                # Look for tables
                tables = await results_panel.query_selector_all("table")
                print(f"\n📊 Found {len(tables)} table(s) in results panel")
                
                for i, table in enumerate(tables):
                    table_id = await table.get_attribute("id")
                    table_class = await table.get_attribute("class")
                    rows = await table.query_selector_all("tr")
                    print(f"  Table {i+1}: id={table_id}, class={table_class}, rows={len(rows)}")
                    
                    if rows:
                        # Show first few rows
                        for j, row in enumerate(rows[:5]):
                            cells = await row.query_selector_all("td, th")
                            cell_texts = []
                            for cell in cells:
                                text = await cell.inner_text()
                                cell_texts.append(text.strip()[:30])
                            print(f"    Row {j+1}: {cell_texts}")
            
            # Take screenshot
            await page.screenshot(path="debug_san_antonio_actual_results.png", full_page=True)
            print("\n📸 Screenshot saved: debug_san_antonio_actual_results.png")
            
            print("\n⏳ Keeping browser open for 60 seconds for inspection...")
            await page.wait_for_timeout(60000)
            await browser.close()


async def test_mecklenburg_project_search():
    """Try Mecklenburg project name search"""
    print("\n" + "="*60)
    print("MECKLENBURG - PROJECT NAME SEARCH")
    print("="*60)
    
    tenant_id = os.environ.get("TENANT_ID", "demo")
    
    async with tenant_scoped_session(tenant_id):
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)  # Visible
            page = await browser.new_page()
            
            # Navigate
            await page.goto("https://webpermit.mecklenburgcountync.gov/", wait_until="networkidle")
            await page.wait_for_timeout(1000)
            
            # View Permits
            view_permits = await page.query_selector('a:has-text("View Permits")')
            if view_permits:
                await view_permits.click()
                await page.wait_for_load_state("networkidle")
                await page.wait_for_timeout(1500)
            
            # By Project Name
            by_project = await page.query_selector('a:has-text("By Project Name")')
            if by_project:
                await by_project.click()
                await page.wait_for_load_state("networkidle")
                await page.wait_for_timeout(2000)
            
            # Fill with very common term
            project_input = await page.query_selector('input[name*="ProjectName"], input[id*="ProjectName"]')
            if project_input:
                await project_input.fill("Building")
                print("✓ Filled project name: 'Building'")
                await page.wait_for_timeout(500)
            
            # Submit
            submit_btn = await page.query_selector('a[id*="PerformSearch"]')
            if submit_btn:
                btn_id = await submit_btn.get_attribute("id")
                await page.evaluate(f"""
                    const btn = document.getElementById('{btn_id}');
                    if (btn && btn.onclick) {{
                        btn.onclick();
                    }} else if (btn) {{
                        btn.click();
                    }}
                """)
                print("✓ Clicked search button")
                await page.wait_for_timeout(5000)
                await page.wait_for_load_state("networkidle", timeout=60000)
                await page.wait_for_timeout(3000)
            
            # Wait for page to stabilize after navigation
            try:
                await page.wait_for_load_state("networkidle", timeout=30000)
            except:
                pass
            await page.wait_for_timeout(3000)
            
            # Check URL
            try:
                current_url = page.url
                print(f"\n📄 Current URL: {current_url}")
            except:
                print("\n⚠️  Could not get URL (page may have navigated)")
            
            # Look for results table - handle navigation errors
            try:
                results_table = await page.query_selector('#ctl00_MainContent_dgResults')
            except Exception as e:
                print(f"⚠️  Error querying page: {e}")
                # Try to get fresh page reference
                results_table = None
            if results_table:
                print("✅ FOUND RESULTS TABLE!")
                rows = await results_table.query_selector_all("tr:not(.PosseGridHeader)")
                print(f"📊 Found {len(rows)} data rows")
                
                # Show first few rows
                for i, row in enumerate(rows[:5]):
                    cells = await row.query_selector_all("td")
                    cell_texts = []
                    for cell in cells:
                        text = await cell.inner_text()
                        cell_texts.append(text.strip()[:40])
                    print(f"  Row {i+1}: {cell_texts}")
            else:
                print("❌ Results table not found")
                # Check what tables exist
                all_tables = await page.query_selector_all("table")
                print(f"📊 Found {len(all_tables)} table(s) on page")
                for i, table in enumerate(all_tables):
                    table_id = await table.get_attribute("id")
                    table_class = await table.get_attribute("class")
                    print(f"  Table {i+1}: id={table_id}, class={table_class}")
            
            # Screenshot
            await page.screenshot(path="debug_mecklenburg_actual_results.png", full_page=True)
            print("\n📸 Screenshot saved: debug_mecklenburg_actual_results.png")
            
            print("\n⏳ Keeping browser open for 60 seconds for inspection...")
            await page.wait_for_timeout(60000)
            await browser.close()


async def main():
    """Run both tests to get actual results"""
    await test_san_antonio_broad_search()
    await test_mecklenburg_project_search()


if __name__ == "__main__":
    asyncio.run(main())

