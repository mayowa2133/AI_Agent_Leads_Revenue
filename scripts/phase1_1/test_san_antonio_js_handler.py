from __future__ import annotations

import asyncio
import os
from datetime import date

from src.core.security import tenant_scoped_session
from playwright.async_api import async_playwright


async def main():
    """Debug: Inspect and trigger search button JavaScript handlers directly"""
    print("\n" + "="*70)
    print("SAN ANTONIO - JAVASCRIPT HANDLER DEBUG")
    print("="*70)
    
    tenant_id = os.environ.get("TENANT_ID", "demo")
    
    async with tenant_scoped_session(tenant_id):
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
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
            
            # Fill dates
            start_date = date(2025, 9, 1)
            end_date = date(2025, 10, 31)
            
            start_input = await page.query_selector('#ctl00_PlaceHolderMain_generalSearchForm_txtGSStartDate')
            end_input = await page.query_selector('#ctl00_PlaceHolderMain_generalSearchForm_txtGSEndDate')
            
            if start_input and end_input:
                await start_input.fill(start_date.strftime("%m/%d/%Y"))
                await end_input.fill(end_date.strftime("%m/%d/%Y"))
                await page.wait_for_timeout(1000)
            
            # Inspect search button
            search_btn = await page.query_selector('#btnSearch')
            if search_btn:
                print("\n📋 SEARCH BUTTON INSPECTION:")
                
                # Get all button attributes
                btn_id = await search_btn.get_attribute("id")
                btn_class = await search_btn.get_attribute("class")
                btn_href = await search_btn.get_attribute("href")
                btn_onclick = await search_btn.get_attribute("onclick")
                btn_type = await search_btn.get_attribute("type")
                
                print(f"  ID: {btn_id}")
                print(f"  Class: {btn_class}")
                print(f"  Href: {btn_href}")
                print(f"  Onclick: {btn_onclick}")
                print(f"  Type: {btn_type}")
                
                # Get button HTML
                btn_html = await search_btn.evaluate("el => el.outerHTML")
                print(f"  HTML: {btn_html[:200]}")
                
                # Check for JavaScript functions in page
                print("\n🔍 CHECKING JAVASCRIPT FUNCTIONS:")
                
                # Check for GlobalSearch function
                has_global_search = await page.evaluate("typeof GlobalSearch !== 'undefined'")
                print(f"  GlobalSearch function exists: {has_global_search}")
                
                # Check for btnSearch click handler
                btn_click_handler = await page.evaluate("""
                    (() => {
                        const btn = document.getElementById('btnSearch');
                        if (btn) {
                            return {
                                hasOnclick: typeof btn.onclick === 'function',
                                hasClick: typeof btn.click === 'function',
                                disabled: btn.disabled,
                                href: btn.href,
                                className: btn.className
                            };
                        }
                        return null;
                    })();
                """)
                print(f"  Button state: {btn_click_handler}")
                
                # Try to find the actual search function
                search_functions = await page.evaluate("""
                    const functions = [];
                    for (let prop in window) {
                        if (typeof window[prop] === 'function' && 
                            (prop.toLowerCase().includes('search') || 
                             prop.toLowerCase().includes('submit') ||
                             prop.toLowerCase().includes('btn'))) {
                            functions.push(prop);
                        }
                    }
                    return functions.slice(0, 20);
                """)
                print(f"  Search-related functions: {search_functions}")
                
                # Enable button
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
                await page.wait_for_timeout(500)
                
                # Try multiple trigger methods
                print("\n🚀 TRYING MULTIPLE TRIGGER METHODS:")
                
                # Method 1: Call GlobalSearch function directly
                print("  Method 1: Call GlobalSearch function...")
                try:
                    result = await page.evaluate("""
                        (() => {
                            if (typeof GlobalSearch !== 'undefined') {
                                // Try to find the search input
                                const searchInput = document.getElementById('txtSearchCondition') || 
                                                   document.querySelector('input[name*="Search"]');
                                const searchText = searchInput ? searchInput.value : '';
                                
                                // Call GlobalSearch constructor
                                try {
                                    new GlobalSearch("txtSearchCondition", "btnSearch", searchText, '');
                                    return 'GlobalSearch called';
                                } catch(e) {
                                    return 'Error: ' + e.message;
                                }
                            }
                            return 'GlobalSearch not found';
                        })();
                    """)
                    print(f"    Result: {result}")
                    await page.wait_for_timeout(5000)
                except Exception as e:
                    print(f"    Error: {e}")
                
                # Check if update panel has content
                panel = await page.query_selector('#ctl00_PlaceHolderMain_RecordSearchResultInfo_updatePanel')
                if panel:
                    panel_text = await panel.evaluate("el => el.innerText")
                    if panel_text and len(panel_text) > 10:
                        print(f"    ✓ Update panel has content: {len(panel_text)} chars")
                    else:
                        print(f"    ✗ Update panel still empty")
                
                # Method 2: Trigger click event
                print("  Method 2: Trigger click event...")
                try:
                    await page.evaluate("""
                        const btn = document.getElementById('btnSearch');
                        if (btn) {
                            const event = new MouseEvent('click', {
                                view: window,
                                bubbles: true,
                                cancelable: true
                            });
                            btn.dispatchEvent(event);
                        }
                    """)
                    await page.wait_for_timeout(3000)
                except Exception as e:
                    print(f"    Error: {e}")
                
                # Method 3: Call href directly
                print("  Method 3: Navigate to href...")
                try:
                    href = await search_btn.get_attribute("href")
                    if href and href != "#":
                        await page.goto(href, wait_until="networkidle", timeout=30000)
                        await page.wait_for_timeout(3000)
                        print(f"    Navigated to: {href}")
                except Exception as e:
                    print(f"    Error: {e}")
                
                # Method 4: Form submit
                print("  Method 4: Form submit...")
                try:
                    await page.evaluate("""
                        const form = document.getElementById('aspnetForm');
                        if (form) {
                            // Set __EVENTTARGET and __EVENTARGUMENT for UpdatePanel
                            const target = document.createElement('input');
                            target.type = 'hidden';
                            target.name = '__EVENTTARGET';
                            target.value = 'ctl00$PlaceHolderMain$btnSearch';
                            form.appendChild(target);
                            
                            form.submit();
                        }
                    """)
                    await page.wait_for_timeout(5000)
                    await page.wait_for_load_state("networkidle", timeout=30000)
                    await page.wait_for_timeout(3000)
                except Exception as e:
                    print(f"    Error: {e}")
                
                # Final check
                print("\n📊 FINAL STATE:")
                panel = await page.query_selector('#ctl00_PlaceHolderMain_RecordSearchResultInfo_updatePanel')
                if panel:
                    panel_text = await panel.evaluate("el => el.innerText")
                    tables = await panel.query_selector_all("table")
                    print(f"  Update panel text: {len(panel_text) if panel_text else 0} chars")
                    print(f"  Tables: {len(tables)}")
                    if panel_text and len(panel_text) > 10:
                        print(f"  Preview: {panel_text[:200]}")
            
            # Screenshot
            await page.screenshot(path="debug_san_antonio_js_handler.png", full_page=True)
            print("\n📸 Screenshot: debug_san_antonio_js_handler.png")
            
            print("\n⏳ Keeping browser open for 60 seconds...")
            await page.wait_for_timeout(60000)
            await browser.close()


if __name__ == "__main__":
    asyncio.run(main())

