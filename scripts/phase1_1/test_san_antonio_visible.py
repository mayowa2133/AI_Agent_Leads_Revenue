from __future__ import annotations

import asyncio
import os
from datetime import datetime, timezone

from src.core.security import tenant_scoped_session
from src.signal_engine.scrapers.permit_scraper import san_antonio_fire_scraper


async def main():
    """
    Test script with visible browser for debugging San Antonio Fire Module scraper.
    
    Usage:
        TENANT_ID=demo \
        RECORD_TYPE="Fire Alarm" \
        poetry run python scripts/test_san_antonio_visible.py
    """
    tenant_id = os.environ.get("TENANT_ID", "demo")
    record_type = os.environ.get("RECORD_TYPE")  # Optional: "Fire Alarm", "Fire Sprinkler", etc.
    days_back = int(os.environ.get("DAYS_BACK", "30"))

    scraper = san_antonio_fire_scraper(
        record_type=record_type,
        days_back=days_back,
    )
    
    # Override to use visible browser
    from playwright.async_api import async_playwright
    
    async with tenant_scoped_session(tenant_id):
        search_desc = f"record_type={record_type or 'All'}, days_back={days_back}"
        print(f"Testing San Antonio Fire Module scraper: {search_desc}\n")
        print("Browser will open - watch the navigation sequence...\n")
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)  # VISIBLE
            page = await browser.new_page()
            
            # Navigate directly to search page (Accela pattern)
            search_url = "https://aca-prod.accela.com/COSA/Cap/CapHome.aspx?module=Fire&TabName=Search"
            print(f"🔍 Navigating to search URL: {search_url}")
            await page.goto(search_url, wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_timeout(3000)  # Give JavaScript time to load
            
            # Take screenshot of search page
            await page.screenshot(path="debug_san_antonio_search.png", full_page=True)
            print("📸 Screenshot saved: debug_san_antonio_search.png")
            
            # Inspect search form
            page_title = await page.title()
            page_url = page.url
            print(f"📄 Search Page Title: {page_title}")
            print(f"🔗 Search Page URL: {page_url}")
            
            # Look for form elements
            forms = await page.query_selector_all("form")
            print(f"📋 Found {len(forms)} form(s)")
            
            # Look for select dropdowns (Record Type)
            selects = await page.query_selector_all("select")
            print(f"📋 Found {len(selects)} select dropdown(s)")
            for i, select in enumerate(selects):
                select_id = await select.get_attribute("id")
                select_name = await select.get_attribute("name")
                options = await select.query_selector_all("option")
                option_texts = [await opt.inner_text() for opt in options[:5]]  # First 5 options
                print(f"  Select {i+1}: id={select_id}, name={select_name}, options={option_texts}")
            
            # Look for input fields
            inputs = await page.query_selector_all("input[type='text'], input[type='search']")
            print(f"📋 Found {len(inputs)} text input(s)")
            
            # Look for submit buttons
            submit_buttons = await page.query_selector_all('input[type="submit"], button[type="submit"]')
            print(f"📋 Found {len(submit_buttons)} submit button(s)")
            
            # Select "General Search" from search type dropdown
            search_type_select = await page.query_selector('#ctl00_PlaceHolderMain_ddlSearchType')
            if search_type_select:
                print("✓ Found search type dropdown, selecting 'General Search'")
                await search_type_select.select_option(label="General Search")
                await page.wait_for_timeout(2000)  # Wait for form to update
            
            # Fill in date range to ensure we get results (last 30 days)
            from datetime import datetime, timedelta
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)
            
            start_date_input = await page.query_selector('#ctl00_PlaceHolderMain_generalSearchForm_txtGSStartDate')
            end_date_input = await page.query_selector('#ctl00_PlaceHolderMain_generalSearchForm_txtGSEndDate')
            
            if start_date_input and end_date_input:
                start_date_str = start_date.strftime("%m/%d/%Y")
                end_date_str = end_date.strftime("%m/%d/%Y")
                await start_date_input.fill(start_date_str)
                await end_date_input.fill(end_date_str)
                print(f"✓ Filled date range: {start_date_str} to {end_date_str}")
                await page.wait_for_timeout(1000)
            
            # Try selecting a permit type to get results - let's try the first non-empty option
            permit_type_select = await page.query_selector('#ctl00_PlaceHolderMain_generalSearchForm_ddlGSPermitType')
            if permit_type_select:
                # Get all options
                options = await permit_type_select.query_selector_all("option")
                option_texts = [await opt.inner_text() for opt in options]
                print(f"📋 Available permit types ({len(option_texts)} total):")
                for i, text in enumerate(option_texts[:15]):  # Show first 15
                    print(f"  {i+1}. {text}")
                
                # If record type is specified, try to match it
                if record_type:
                    found = False
                    for option in options:
                        text = await option.inner_text()
                        if record_type.lower() in text.lower() and text.strip() != "--Select--":
                            value = await option.get_attribute("value")
                            await permit_type_select.select_option(value=value)
                            print(f"\n✓ Selected permit type: {text}")
                            await page.wait_for_timeout(1000)
                            found = True
                            break
                    if not found:
                        print(f"\n⚠️  Could not find permit type matching '{record_type}'")
                else:
                    # Try selecting the first non-empty option (skip "--Select--")
                    for option in options[1:6]:  # Try first 5 non-empty options
                        text = await option.inner_text()
                        if text.strip() and text.strip() != "--Select--":
                            value = await option.get_attribute("value")
                            await permit_type_select.select_option(value=value)
                            print(f"\n✓ Selected permit type (for testing): {text}")
                            await page.wait_for_timeout(1000)
                            break
            else:
                print("⚠️  Could not find permit type select dropdown")
            
            # Inspect the general search form specifically
            print("\n🔍 Inspecting general search form for submission method...")
            general_search_form = await page.query_selector('#ctl00_PlaceHolderMain_generalSearchForm')
            
            if general_search_form:
                print("✓ Found general search form")
                
                # Look for buttons specifically within the general search form
                form_buttons = await general_search_form.query_selector_all('input[type="button"], input[type="submit"], input[type="image"], button, a[onclick], img[onclick]')
                print(f"📋 Found {len(form_buttons)} button-like elements in general search form")
                
                search_btn = None
                for i, btn in enumerate(form_buttons):
                    btn_type = await btn.get_attribute("type")
                    btn_value = await btn.get_attribute("value")
                    btn_onclick = await btn.get_attribute("onclick")
                    btn_id = await btn.get_attribute("id")
                    btn_name = await btn.get_attribute("name")
                    btn_class = await btn.get_attribute("class")
                    btn_alt = await btn.get_attribute("alt")
                    try:
                        btn_text = await btn.inner_text()
                    except:
                        btn_text = ""
                    
                    print(f"  Form Button {i+1}: type={btn_type}, value={btn_value}, id={btn_id}, name={btn_name}, onclick={btn_onclick[:80] if btn_onclick else None}, alt={btn_alt}, text={btn_text[:30]}")
                    
                    # Check if this looks like a search button
                    if (btn_onclick and ("search" in btn_onclick.lower() or "submit" in btn_onclick.lower() or "doPostBack" in btn_onclick.lower())) or \
                       (btn_value and "search" in btn_value.lower()) or \
                       (btn_text and "search" in btn_text.lower()) or \
                       (btn_alt and "search" in btn_alt.lower()) or \
                       (btn_id and "search" in btn_id.lower()) or \
                       (btn_name and "search" in btn_name.lower()):
                        search_btn = btn
                        print(f"    → This looks like a search button!")
                        break
                
                # Also check for image buttons with alt text
                if not search_btn:
                    img_buttons = await general_search_form.query_selector_all('input[type="image"], img[onclick]')
                    for img_btn in img_buttons:
                        alt_text = await img_btn.get_attribute("alt")
                        src_text = await img_btn.get_attribute("src")
                        if (alt_text and "search" in alt_text.lower()) or (src_text and "search" in src_text.lower()):
                            search_btn = img_btn
                            print(f"✓ Found image search button: alt={alt_text}, src={src_text}")
                            break
            else:
                print("⚠️  Could not find general search form")
                search_btn = None
            
            # Try to submit search using the #btnSearch button (same method as scraper)
            btn_search = await page.query_selector('#btnSearch')
            if btn_search:
                print(f"\n✓ Found #btnSearch button")
                # Enable the button
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
                
                # Click via JavaScript
                await page.evaluate("document.getElementById('btnSearch').click()")
                print("✓ Clicked search button")
                await page.wait_for_timeout(2000)
                
                # Wait for AJAX update
                try:
                    await page.wait_for_selector('#ctl00_PlaceHolderMain_RecordSearchResultInfo_updatePanel', timeout=10000)
                    print("✓ Update panel found")
                except:
                    print("⚠️  Update panel not found, waiting for network...")
                
                await page.wait_for_load_state("networkidle", timeout=30000)
                await page.wait_for_timeout(3000)
                print("✓ Search submitted and page loaded")
            elif search_btn:
                print(f"\n✓ Found search button in form, clicking...")
                await search_btn.click()
                await page.wait_for_timeout(2000)
                await page.wait_for_load_state("networkidle", timeout=30000)
                await page.wait_for_timeout(3000)
                print("✓ Search submitted")
            else:
                print("\n⚠️  Could not find search button")
            
            # Check page for any error messages or messages
            page_text = await page.evaluate("document.body.innerText")
            if "error" in page_text.lower() or "invalid" in page_text.lower():
                error_sections = [line for line in page_text.split("\n") if "error" in line.lower() or "invalid" in line.lower()]
                if error_sections:
                    print("\n⚠️  Possible error messages found:")
                    for err in error_sections[:5]:
                        print(f"  - {err[:100]}")
            
            # Check for "no results" or "0 records" messages
            if "no record" in page_text.lower() or "0 record" in page_text.lower() or "no result" in page_text.lower():
                print("\n📋 Page contains 'no results' message - search completed but returned no records")
            
            # Check for results in the update panel first
            print("\n🔍 Checking for results in update panel...")
            results_update_panel = await page.query_selector('#ctl00_PlaceHolderMain_RecordSearchResultInfo_updatePanel')
            
            if results_update_panel:
                print("✓ Found RecordSearchResultInfo update panel")
                panel_html = await results_update_panel.inner_html()
                panel_text = await results_update_panel.inner_text()
                
                print(f"📄 Update panel text content: {panel_text[:200] if panel_text else '(empty)'}")
                
                # Save panel HTML for inspection
                with open("debug_san_antonio_results_panel.html", "w", encoding="utf-8") as f:
                    f.write(panel_html)
                print("💾 Update panel HTML saved: debug_san_antonio_results_panel.html")
                
                # Look for tables in the update panel
                tables_in_panel = await results_update_panel.query_selector_all("table")
                print(f"📊 Found {len(tables_in_panel)} table(s) in update panel")
                
                # Look for any divs or other containers that might have results
                divs_in_panel = await results_update_panel.query_selector_all("div")
                print(f"📦 Found {len(divs_in_panel)} div(s) in update panel")
                
                # Check for grid or list elements
                grid_elements = await results_update_panel.query_selector_all("[class*='grid'], [class*='Grid'], [id*='grid'], [id*='Grid']")
                print(f"📊 Found {len(grid_elements)} grid-like element(s) in update panel")
                
                for i, table in enumerate(tables_in_panel):
                    table_id = await table.get_attribute("id")
                    table_class = await table.get_attribute("class")
                    print(f"  Table {i+1}: id={table_id}, class={table_class}")
            
            # Check for results - try multiple table selectors
            results_table = None
            table_selectors = [
                "#ctl00_PlaceHolderMain_RecordSearchResultInfo_updatePanel table.aca_grid_table",
                "#ctl00_PlaceHolderMain_RecordSearchResultInfo_updatePanel table[id*='grid']",
                "#ctl00_PlaceHolderMain_RecordSearchResultInfo_updatePanel table",
                "table.aca_grid_table",
                "table[id*='grid']",
                "table.aca_grid",
                "table",
            ]
            
            for selector in table_selectors:
                results_table = await page.query_selector(selector)
                if results_table:
                    print(f"\n✓ Found results table with selector: {selector}")
                    break
            
            if results_table:
                table_id = await results_table.get_attribute("id")
                table_class = await results_table.get_attribute("class")
                print(f"  Table: id={table_id}, class={table_class}")
                
                # Count rows
                all_rows = await results_table.query_selector_all("tr")
                print(f"📊 Total rows: {len(all_rows)}")
                
                # Check header
                header_row = await results_table.query_selector("tr:first-child, tr.aca_grid_header, thead tr")
                if header_row:
                    header_text = await header_row.inner_text()
                    print(f"📋 Header: {header_text}")
                    
                    # Get header cells to understand column structure
                    header_cells = await header_row.query_selector_all("th, td")
                    header_cell_texts = []
                    for cell in header_cells:
                        text = await cell.inner_text()
                        header_cell_texts.append(text.strip())
                    print(f"📋 Header cells: {header_cell_texts}")
                
                # Inspect first few data rows
                data_rows = await results_table.query_selector_all("tr:not(:first-child)")
                print(f"📊 Data rows (excluding header): {len(data_rows)}")
                
                for i, row in enumerate(data_rows[:3]):  # First 3 rows
                    cells = await row.query_selector_all("td")
                    cell_texts = []
                    for cell in cells:
                        text = await cell.inner_text()
                        cell_texts.append(text.strip())
                    print(f"  Row {i+1}: {cell_texts}")
                    
                    # Check for links in first cell (permit ID)
                    first_cell = cells[0] if cells else None
                    if first_cell:
                        link = await first_cell.query_selector("a")
                        if link:
                            href = await link.get_attribute("href")
                            link_text = await link.inner_text()
                            print(f"    → Link in first cell: '{link_text}' -> {href}")
                
                # Save table HTML
                table_html = await results_table.inner_html()
                with open("debug_san_antonio_table.html", "w", encoding="utf-8") as f:
                    f.write(table_html)
                print("💾 Table HTML saved: debug_san_antonio_table.html")
            else:
                print("⚠️  No results table found with any selector")
                # Save full page HTML for inspection
                page_html = await page.content()
                with open("debug_san_antonio_full_page.html", "w", encoding="utf-8") as f:
                    f.write(page_html)
                print("💾 Full page HTML saved: debug_san_antonio_full_page.html")
            
            # Final screenshot
            await page.screenshot(path="debug_san_antonio_results.png", full_page=True)
            print("📸 Screenshot saved: debug_san_antonio_results.png")
            
            # Keep browser open for inspection
            print("\n⏳ Browser will stay open for 30 seconds for inspection...")
            print("   Check the screenshots and HTML files for details.")
            await page.wait_for_timeout(30000)
            
            await browser.close()


if __name__ == "__main__":
    asyncio.run(main())

