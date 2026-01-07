from __future__ import annotations

import asyncio
import os
from datetime import date

from src.core.security import tenant_scoped_session
from playwright.async_api import async_playwright


async def main():
    """Comprehensive debug: network requests, JS errors, and alternative search methods"""
    print("\n" + "="*70)
    print("SAN ANTONIO - COMPREHENSIVE DEBUG")
    print("="*70)
    
    tenant_id = os.environ.get("TENANT_ID", "demo")
    
    async with tenant_scoped_session(tenant_id):
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context()
            page = await context.new_page()
            
            # Track network requests
            network_requests = []
            network_responses = []
            
            def handle_request(request):
                network_requests.append({
                    'url': request.url,
                    'method': request.method,
                    'headers': request.headers,
                })
            
            def handle_response(response):
                network_responses.append({
                    'url': response.url,
                    'status': response.status,
                    'headers': response.headers,
                })
            
            page.on("request", handle_request)
            page.on("response", handle_response)
            
            # Track JavaScript errors
            js_errors = []
            
            def handle_console(msg):
                if msg.type == "error":
                    js_errors.append({
                        'text': msg.text,
                        'location': msg.location,
                    })
            
            page.on("console", handle_console)
            
            # Navigate to search
            search_url = "https://aca-prod.accela.com/COSA/Cap/CapHome.aspx?module=Fire&TabName=Search"
            await page.goto(search_url, wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_timeout(3000)
            print("✓ Loaded search page")
            
            # Clear previous network tracking
            network_requests.clear()
            network_responses.clear()
            js_errors.clear()
            
            # Select General Search
            search_type = await page.query_selector('#ctl00_PlaceHolderMain_ddlSearchType')
            if search_type:
                await search_type.select_option(label="General Search")
                await page.wait_for_timeout(2000)
                print("✓ Selected General Search")
            
            # Fill golden search dates
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
                
                print("\n🔍 Clicking search button and monitoring network...")
                await page.evaluate("document.getElementById('btnSearch').click()")
                
                # Wait and monitor
                await page.wait_for_timeout(10000)  # Wait 10 seconds for AJAX
                await page.wait_for_load_state("networkidle", timeout=60000)
                await page.wait_for_timeout(5000)
            
            # Analyze network requests
            print("\n" + "="*70)
            print("NETWORK REQUESTS ANALYSIS:")
            print("="*70)
            print(f"Total requests: {len(network_requests)}")
            print(f"Total responses: {len(network_responses)}")
            
            # Look for AJAX/UpdatePanel requests
            ajax_requests = [r for r in network_requests if 'UpdatePanel' in r['url'] or 'ScriptResource' in r['url'] or 'WebResource' in r['url']]
            print(f"\nAJAX/UpdatePanel requests: {len(ajax_requests)}")
            for req in ajax_requests[:5]:
                print(f"  - {req['method']} {req['url'][:100]}")
            
            # Look for search-related responses
            search_responses = [r for r in network_responses if 'Search' in r['url'] or 'Record' in r['url'] or r['status'] != 200]
            print(f"\nSearch-related responses: {len(search_responses)}")
            for resp in search_responses[:5]:
                print(f"  - Status {resp['status']}: {resp['url'][:100]}")
            
            # Check for JavaScript errors
            print("\n" + "="*70)
            print("JAVASCRIPT ERRORS:")
            print("="*70)
            if js_errors:
                print(f"Found {len(js_errors)} error(s):")
                for err in js_errors[:10]:
                    print(f"  - {err['text']}")
            else:
                print("✓ No JavaScript errors detected")
            
            # Check page state
            print("\n" + "="*70)
            print("PAGE STATE AFTER SEARCH:")
            print("="*70)
            
            # Check update panel
            results_panel = await page.query_selector('#ctl00_PlaceHolderMain_RecordSearchResultInfo_updatePanel')
            if results_panel:
                panel_text = await results_panel.evaluate("el => el.innerText")
                panel_html = await results_panel.evaluate("el => el.innerHTML")
                
                print(f"Update panel found:")
                print(f"  Text length: {len(panel_text) if panel_text else 0}")
                print(f"  HTML length: {len(panel_html) if panel_html else 0}")
                print(f"  Text preview: {panel_text[:200] if panel_text else '(empty)'}")
                
                # Check for tables
                tables = await results_panel.query_selector_all("table")
                print(f"  Tables: {len(tables)}")
                
                # Check for error messages
                errors = await results_panel.query_selector_all('[class*="error"], [class*="Error"], [id*="error"]')
                if errors:
                    print(f"  Error elements: {len(errors)}")
                    for err in errors:
                        err_text = await err.inner_text()
                        print(f"    - {err_text}")
            else:
                print("❌ Update panel not found")
            
            # Check for iframe
            iframe = await page.query_selector('iframe#aca_main_iframe, iframe[name*="aca"], iframe[src*="Cap"]')
            print(f"\nIframe found: {iframe is not None}")
            if iframe:
                iframe_src = await iframe.get_attribute("src")
                print(f"  Iframe src: {iframe_src}")
            
            # Try alternative: Address search
            print("\n" + "="*70)
            print("TRYING ALTERNATIVE: ADDRESS SEARCH")
            print("="*70)
            
            # Navigate back to search
            await page.goto(search_url, wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_timeout(2000)
            
            # Select "Search by Address"
            search_type = await page.query_selector('#ctl00_PlaceHolderMain_ddlSearchType')
            if search_type:
                options = await search_type.query_selector_all("option")
                for opt in options:
                    text = await opt.inner_text()
                    if "Address" in text:
                        await search_type.select_option(label=text)
                        print(f"✓ Selected: {text}")
                        await page.wait_for_timeout(3000)  # Wait for form to change
                        break
            
            # Fill address: 100 ALAMO PLZ (from Gemini's suggestion)
            address_input = await page.query_selector('input[name*="Address"], input[id*="Address"], input[name*="Street"]')
            if address_input:
                await address_input.fill("100 ALAMO PLZ")
                print("✓ Filled address: 100 ALAMO PLZ")
                await page.wait_for_timeout(1000)
            
            # Submit address search
            search_btn = await page.query_selector('#btnSearch')
            if search_btn:
                await page.evaluate("""
                    const btn = document.getElementById('btnSearch');
                    if (btn) {
                        btn.removeAttribute('disabled');
                        btn.classList.remove('ButtonDisabled');
                    }
                """)
                await page.wait_for_timeout(500)
                await page.evaluate("document.getElementById('btnSearch').click()")
                print("✓ Clicked search")
                await page.wait_for_timeout(10000)
                await page.wait_for_load_state("networkidle", timeout=60000)
                await page.wait_for_timeout(5000)
            
            # Check results for address search
            results_panel = await page.query_selector('#ctl00_PlaceHolderMain_RecordSearchResultInfo_updatePanel')
            if results_panel:
                panel_text = await results_panel.evaluate("el => el.innerText")
                tables = await results_panel.query_selector_all("table")
                print(f"\nAddress search results:")
                print(f"  Text length: {len(panel_text) if panel_text else 0}")
                print(f"  Tables: {len(tables)}")
                if panel_text and len(panel_text) > 10:
                    print(f"  Preview: {panel_text[:200]}")
            
            # Screenshot
            await page.screenshot(path="debug_san_antonio_comprehensive.png", full_page=True)
            print("\n📸 Screenshot: debug_san_antonio_comprehensive.png")
            
            print("\n⏳ Keeping browser open for 60 seconds for inspection...")
            await page.wait_for_timeout(60000)
            await browser.close()


if __name__ == "__main__":
    asyncio.run(main())

