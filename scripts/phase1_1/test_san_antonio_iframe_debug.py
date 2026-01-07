from __future__ import annotations

import asyncio
import os
from datetime import date

from src.core.security import tenant_scoped_session
from playwright.async_api import async_playwright


async def main():
    """Debug San Antonio iframe and results extraction with visible browser"""
    print("\n" + "="*70)
    print("SAN ANTONIO - IFRAME DEBUG (GOLDEN SEARCH)")
    print("="*70)
    
    tenant_id = os.environ.get("TENANT_ID", "demo")
    
    async with tenant_scoped_session(tenant_id):
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)  # Visible
            page = await browser.new_page()
            
            # Navigate to search
            search_url = "https://aca-prod.accela.com/COSA/Cap/CapHome.aspx?module=Fire&TabName=Search"
            await page.goto(search_url, wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_timeout(3000)
            print("✓ Loaded search page")
            
            # Select General Search
            search_type = await page.query_selector('#ctl00_PlaceHolderMain_ddlSearchType')
            if search_type:
                await search_type.select_option(label="General Search")
                await page.wait_for_timeout(2000)
                print("✓ Selected General Search")
            
            # Fill golden search dates: Sept 1 - Oct 31, 2025
            start_date = date(2025, 9, 1)
            end_date = date(2025, 10, 31)
            
            start_input = await page.query_selector('#ctl00_PlaceHolderMain_generalSearchForm_txtGSStartDate')
            end_input = await page.query_selector('#ctl00_PlaceHolderMain_generalSearchForm_txtGSEndDate')
            
            if start_input and end_input:
                await start_input.fill(start_date.strftime("%m/%d/%Y"))
                await end_input.fill(end_date.strftime("%m/%d/%Y"))
                print(f"✓ Filled dates: {start_date.strftime('%m/%d/%Y')} to {end_date.strftime('%m/%d/%Y')}")
                await page.wait_for_timeout(1000)
            
            # Select Fire Alarm Permit
            permit_type = await page.query_selector('#ctl00_PlaceHolderMain_generalSearchForm_ddlGSPermitType')
            if permit_type:
                try:
                    await permit_type.select_option(label="Fire Alarm Permit")
                    print("✓ Selected Fire Alarm Permit")
                    await page.wait_for_timeout(1000)
                except:
                    # Try partial match
                    options = await permit_type.query_selector_all("option")
                    for opt in options:
                        text = await opt.inner_text()
                        if "Fire Alarm" in text:
                            await permit_type.select_option(value=await opt.get_attribute("value"))
                            print(f"✓ Selected: {text}")
                            await page.wait_for_timeout(1000)
                            break
            
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
                await page.wait_for_timeout(5000)  # Wait for AJAX
                await page.wait_for_load_state("networkidle", timeout=60000)
                await page.wait_for_timeout(5000)
            
            # Check for iframe
            iframe_selector = 'iframe#aca_main_iframe, iframe[name*="aca"], iframe[src*="Cap"]'
            iframe = await page.query_selector(iframe_selector)
            
            print(f"\n📊 IFRAME DETECTION:")
            print(f"  Iframe found: {iframe is not None}")
            
            if iframe:
                print("✓ Found iframe")
                iframe_src = await iframe.get_attribute("src")
                iframe_id = await iframe.get_attribute("id")
                iframe_name = await iframe.get_attribute("name")
                print(f"  Iframe src: {iframe_src}")
                print(f"  Iframe id: {iframe_id}")
                print(f"  Iframe name: {iframe_name}")
                
                # Try to get frame content
                try:
                    frame = await iframe.content_frame()
                    if frame:
                        print("✓ Successfully accessed iframe content")
                        
                        # Check update panel in iframe
                        results_panel = await frame.query_selector('#ctl00_PlaceHolderMain_RecordSearchResultInfo_updatePanel')
                        if results_panel:
                            panel_text = await results_panel.evaluate("el => el.innerText")
                            panel_html = await results_panel.evaluate("el => el.innerHTML")
                            
                            print(f"\n📄 IFRAME UPDATE PANEL:")
                            print(f"  Text length: {len(panel_text) if panel_text else 0}")
                            print(f"  HTML length: {len(panel_html) if panel_html else 0}")
                            print(f"  Text preview: {panel_text[:200] if panel_text else '(empty)'}")
                            
                            # Check for tables
                            tables = await results_panel.query_selector_all("table")
                            print(f"  Tables found: {len(tables)}")
                            
                            for i, table in enumerate(tables):
                                table_id = await table.get_attribute("id")
                                table_class = await table.get_attribute("class")
                                rows = await table.query_selector_all("tr")
                                print(f"    Table {i+1}: id={table_id}, class={table_class}, rows={len(rows)}")
                                
                                if rows:
                                    # Show first row
                                    first_row = rows[0]
                                    cells = await first_row.query_selector_all("td, th")
                                    cell_texts = [await cell.inner_text() for cell in cells[:5]]
                                    print(f"      First row: {cell_texts}")
                            
                            # Check for fire alarm text
                            has_fire_alarm = "FIRE ALARM" in panel_html.upper() or "FIRE-ALM" in panel_html.upper()
                            print(f"  Contains 'FIRE ALARM': {has_fire_alarm}")
                            
                            # Save iframe HTML
                            frame_html = await frame.content()
                            with open("debug_san_antonio_iframe_content.html", "w", encoding="utf-8") as f:
                                f.write(frame_html)
                            print("  💾 Saved iframe HTML: debug_san_antonio_iframe_content.html")
                        else:
                            print("  ❌ Update panel not found in iframe")
                            
                        # Try frame_locator approach
                        print("\n🔍 Testing frame_locator approach:")
                        frame_locator = page.frame_locator(iframe_selector)
                        
                        table_selectors = [
                            'table[id*="gvPermitList"]',
                            'table.aca_grid_table',
                            'table[id*="grid"]',
                            'table',
                        ]
                        
                        for table_sel in table_selectors:
                            try:
                                locator = frame_locator.locator(table_sel).first
                                count = await locator.count()
                                if count > 0:
                                    print(f"  ✓ Found table with selector: {table_sel} (count: {count})")
                                    is_visible = await locator.is_visible()
                                    print(f"    Visible: {is_visible}")
                                else:
                                    print(f"  ✗ No table found with: {table_sel}")
                            except Exception as e:
                                print(f"  ✗ Error with {table_sel}: {e}")
                    else:
                        print("  ❌ Could not get iframe content frame")
                except Exception as e:
                    print(f"  ❌ Error accessing iframe: {e}")
                    import traceback
                    traceback.print_exc()
            else:
                print("  ❌ No iframe found")
            
            # Also check main page
            print("\n📄 MAIN PAGE UPDATE PANEL:")
            main_panel = await page.query_selector('#ctl00_PlaceHolderMain_RecordSearchResultInfo_updatePanel')
            if main_panel:
                panel_text = await main_panel.evaluate("el => el.innerText")
                print(f"  Text: {panel_text[:200] if panel_text else '(empty)'}")
            else:
                print("  ❌ Update panel not found on main page")
            
            # Screenshot
            await page.screenshot(path="debug_san_antonio_iframe_debug.png", full_page=True)
            print("\n📸 Screenshot: debug_san_antonio_iframe_debug.png")
            
            print("\n⏳ Keeping browser open for 60 seconds for inspection...")
            await page.wait_for_timeout(60000)
            await browser.close()


if __name__ == "__main__":
    asyncio.run(main())

