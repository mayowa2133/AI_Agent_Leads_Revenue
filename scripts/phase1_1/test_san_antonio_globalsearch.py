from __future__ import annotations

import asyncio
import os
from datetime import date

from src.core.security import tenant_scoped_session
from playwright.async_api import async_playwright


async def main():
    """Test GlobalSearch function with network monitoring"""
    print("\n" + "="*70)
    print("SAN ANTONIO - GLOBALSEARCH FUNCTION TEST")
    print("="*70)
    
    tenant_id = os.environ.get("TENANT_ID", "demo")
    
    async with tenant_scoped_session(tenant_id):
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context()
            page = await context.new_page()
            
            # Track AJAX requests
            ajax_requests = []
            
            def handle_response(response):
                url = response.url
                if 'UpdatePanel' in url or 'ScriptResource' in url or 'WebResource' in url or 'Search' in url:
                    ajax_requests.append({
                        'url': url,
                        'status': response.status,
                        'method': response.request.method,
                    })
            
            page.on("response", handle_response)
            
            # Navigate
            search_url = "https://aca-prod.accela.com/COSA/Cap/CapHome.aspx?module=Fire&TabName=Search"
            await page.goto(search_url, wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_timeout(3000)
            
            # Setup form
            search_type = await page.query_selector('#ctl00_PlaceHolderMain_ddlSearchType')
            if search_type:
                await search_type.select_option(label="General Search")
                await page.wait_for_timeout(2000)
            
            start_date = date(2025, 9, 1)
            end_date = date(2025, 10, 31)
            
            start_input = await page.query_selector('#ctl00_PlaceHolderMain_generalSearchForm_txtGSStartDate')
            end_input = await page.query_selector('#ctl00_PlaceHolderMain_generalSearchForm_txtGSEndDate')
            
            if start_input and end_input:
                await start_input.fill(start_date.strftime("%m/%d/%Y"))
                await end_input.fill(end_date.strftime("%m/%d/%Y"))
                await page.wait_for_timeout(1000)
            
            # Enable button
            await page.evaluate("""
                const btn = document.getElementById('btnSearch');
                if (btn) {
                    btn.removeAttribute('disabled');
                    btn.classList.remove('ButtonDisabled');
                }
            """)
            await page.wait_for_timeout(500)
            
            # Clear AJAX tracking
            ajax_requests.clear()
            
            # Inspect GlobalSearch function
            print("\n🔍 INSPECTING GLOBALSEARCH:")
            gs_info = await page.evaluate("""
                (() => {
                    if (typeof GlobalSearch === 'undefined') {
                        return {exists: false};
                    }
                    
                    // Try to get function source
                    const gsStr = GlobalSearch.toString();
                    return {
                        exists: true,
                        isFunction: typeof GlobalSearch === 'function',
                        sourceLength: gsStr.length,
                        sourcePreview: gsStr.substring(0, 500)
                    };
                })();
            """)
            print(f"  GlobalSearch exists: {gs_info.get('exists', False)}")
            if gs_info.get('exists'):
                print(f"  Is function: {gs_info.get('isFunction', False)}")
                print(f"  Source preview: {gs_info.get('sourcePreview', '')[:200]}")
            
            # Try calling GlobalSearch with different approaches
            print("\n🚀 TRYING GLOBALSEARCH CALLS:")
            
            # Method 1: Direct constructor call
            print("  Method 1: new GlobalSearch(...)")
            try:
                result = await page.evaluate("""
                    (() => {
                        try {
                            new GlobalSearch("txtSearchCondition", "btnSearch", '', '');
                            return 'called';
                        } catch(e) {
                            return 'error: ' + e.message;
                        }
                    })();
                """)
                print(f"    Result: {result}")
                await page.wait_for_timeout(5000)
                print(f"    AJAX requests after call: {len(ajax_requests)}")
            except Exception as e:
                print(f"    Exception: {e}")
            
            # Method 2: Trigger button click which should call GlobalSearch
            print("  Method 2: Button click (should trigger GlobalSearch)")
            ajax_requests.clear()
            try:
                await page.evaluate("""
                    document.getElementById('btnSearch').click();
                """)
                await page.wait_for_timeout(5000)
                print(f"    AJAX requests after click: {len(ajax_requests)}")
                for req in ajax_requests[:3]:
                    print(f"      - {req['method']} {req['url'][:80]}")
            except Exception as e:
                print(f"    Exception: {e}")
            
            # Method 3: Check if there's a form validation issue
            print("  Method 3: Check form validation")
            validation = await page.evaluate("""
                (() => {
                    const form = document.getElementById('aspnetForm');
                    if (!form) return {formFound: false};
                    
                    // Check if form has validation
                    const validators = form.querySelectorAll('[class*="validator"], [id*="Validator"]');
                    const requiredFields = form.querySelectorAll('[required]');
                    
                    return {
                        formFound: true,
                        validators: validators.length,
                        requiredFields: requiredFields.length,
                        formAction: form.action,
                        formMethod: form.method
                    };
                })();
            """)
            print(f"    Validation info: {validation}")
            
            # Check final state
            print("\n📊 FINAL STATE:")
            panel = await page.query_selector('#ctl00_PlaceHolderMain_RecordSearchResultInfo_updatePanel')
            if panel:
                panel_text = await panel.evaluate("el => el.innerText")
                print(f"  Update panel text: {len(panel_text) if panel_text else 0} chars")
                if panel_text and len(panel_text) > 10:
                    print(f"  Preview: {panel_text[:200]}")
            
            await page.screenshot(path="debug_san_antonio_globalsearch.png", full_page=True)
            print("\n📸 Screenshot: debug_san_antonio_globalsearch.png")
            
            print("\n⏳ Keeping browser open for 60 seconds...")
            await page.wait_for_timeout(60000)
            await browser.close()


if __name__ == "__main__":
    asyncio.run(main())

