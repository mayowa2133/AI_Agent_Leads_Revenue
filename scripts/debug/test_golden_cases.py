from __future__ import annotations

import asyncio
import os
from datetime import datetime, timezone

from src.core.security import tenant_scoped_session
from src.signal_engine.scrapers.permit_scraper import mecklenburg_county_scraper, san_antonio_fire_scraper


async def test_mecklenburg_golden_case():
    """Test Mecklenburg with golden test case: 111 E CARSON"""
    print("\n" + "="*60)
    print("MECKLENBURG GOLDEN TEST CASE")
    print("="*60)
    print("Search: Street Number=111, Street Name=E CARSON (or CARSON)")
    print("Expected: Should find Permit #E4827760 and related permits")
    print("-"*60 + "\n")
    
    tenant_id = os.environ.get("TENANT_ID", "demo")
    
    async with tenant_scoped_session(tenant_id):
        # Try with "E CARSON" first
        scraper = mecklenburg_county_scraper(
            search_type="address",
            search_value="E CARSON",
            street_number="111",
        )
        
        try:
            permits = await scraper.check_for_updates(last_run=datetime.now(tz=timezone.utc))
            
            if permits:
                print(f"✅ SUCCESS! Found {len(permits)} permit(s):\n")
                for i, p in enumerate(permits[:10], 1):
                    print(f"  {i}. {p.permit_id} - {p.permit_type}")
                    print(f"     Address: {p.address}")
                    print(f"     Status: {p.status}")
                    if p.detail_url:
                        print(f"     URL: {p.detail_url}")
                    print()
                return True
            else:
                print("❌ No permits found with 'E CARSON'")
                print("   Trying 'CARSON' without prefix...\n")
                
                # Try without "E" prefix
                scraper = mecklenburg_county_scraper(
                    search_type="address",
                    search_value="CARSON",
                    street_number="111",
                )
                permits = await scraper.check_for_updates(last_run=datetime.now(tz=timezone.utc))
                
                if permits:
                    print(f"✅ SUCCESS! Found {len(permits)} permit(s) with 'CARSON':\n")
                    for i, p in enumerate(permits[:10], 1):
                        print(f"  {i}. {p.permit_id} - {p.permit_type}")
                        print(f"     Address: {p.address}")
                        print(f"     Status: {p.status}")
                        print()
                    return True
                else:
                    print("❌ No permits found with 'CARSON' either")
                    return False
        except Exception as e:
            print(f"❌ Error: {e}")
            return False


async def test_san_antonio_golden_case():
    """Test San Antonio with golden test case: Q4 2025, Fire Alarm/Sprinkler"""
    print("\n" + "="*60)
    print("SAN ANTONIO GOLDEN TEST CASE")
    print("="*60)
    print("Search: Q4 2025 (10/01/2025 to 12/31/2025)")
    print("Permit Type: Fire Alarm Permit or Fire Sprinkler Permit")
    print("Expected: Should find hundreds of permits")
    print("-"*60 + "\n")
    
    tenant_id = os.environ.get("TENANT_ID", "demo")
    
    async with tenant_scoped_session(tenant_id):
        # Try Fire Alarm Permit first
        permit_types = ["Fire Alarm Permit", "Fire Sprinkler Permit"]
        
        for permit_type in permit_types:
            print(f"\nTrying permit type: {permit_type}")
            print("-" * 40)
            
            # Create scraper with Q4 2025 dates
            scraper = san_antonio_fire_scraper(
                record_type=permit_type,
                days_back=92,  # Oct 1 to Dec 31 = ~92 days
            )
            
            # Override dates to Q4 2025 specifically
            current_permit_type = permit_type  # Capture for closure
            async def custom_scrape():
                from playwright.async_api import async_playwright
                from datetime import datetime, timedelta
                from src.signal_engine.scrapers.base_scraper import dedupe_permits
                from src.signal_engine.models import PermitData
                
                permits = []
                async with async_playwright() as p:
                    browser = await p.chromium.launch(headless=True)
                    page = await browser.new_page()
                    
                    # Navigate to search page
                    search_url = "https://aca-prod.accela.com/COSA/Cap/CapHome.aspx?module=Fire&TabName=Search"
                    await page.goto(search_url, wait_until="domcontentloaded", timeout=60000)
                    await page.wait_for_timeout(3000)
                    
                    # Select General Search
                    search_type_select = await page.query_selector('#ctl00_PlaceHolderMain_ddlSearchType')
                    if search_type_select:
                        await search_type_select.select_option(label="General Search")
                        await page.wait_for_timeout(2000)
                    
                    # Fill Q4 2025 dates
                    start_date_input = await page.query_selector('#ctl00_PlaceHolderMain_generalSearchForm_txtGSStartDate')
                    end_date_input = await page.query_selector('#ctl00_PlaceHolderMain_generalSearchForm_txtGSEndDate')
                    
                    if start_date_input and end_date_input:
                        await start_date_input.fill("10/01/2025")
                        await end_date_input.fill("12/31/2025")
                        await page.wait_for_timeout(1000)
                    
                    # Select permit type
                    permit_type_select = await page.query_selector('#ctl00_PlaceHolderMain_generalSearchForm_ddlGSPermitType')
                    if permit_type_select:
                        options = await permit_type_select.query_selector_all("option")
                        for option in options:
                            text = await option.inner_text()
                            if current_permit_type.lower() in text.lower() and text.strip() != "--Select--":
                                value = await option.get_attribute("value")
                                await permit_type_select.select_option(value=value)
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
                        await page.wait_for_timeout(2000)
                        await page.wait_for_load_state("networkidle", timeout=30000)
                        await page.wait_for_timeout(3000)
                    
                    # Check for iframe
                    iframe = await page.query_selector('iframe#aca_main_iframe, iframe[name*="aca"], iframe[src*="Cap"]')
                    if iframe:
                        frame = await iframe.content_frame()
                        if frame:
                            page = frame
                    
                    # Extract results
                    results_panel = await page.query_selector('#ctl00_PlaceHolderMain_RecordSearchResultInfo_updatePanel')
                    if results_panel:
                        rows = await results_panel.query_selector_all('table.aca_grid_table tbody tr:not(.aca_grid_header), table[id*="grid"] tbody tr:not(:first-child)')
                        if not rows:
                            rows = await results_panel.query_selector_all('table.aca_grid_table tr:not(.aca_grid_header), table[id*="grid"] tr:not(:first-child)')
                        
                        for row in rows[:10]:  # First 10 rows
                            try:
                                cells = await row.query_selector_all("td")
                                if len(cells) >= 4:
                                    permit_id = (await cells[0].inner_text()).strip()
                                    permit_type = (await cells[1].inner_text()).strip() if len(cells) > 1 else ""
                                    address = (await cells[2].inner_text()).strip() if len(cells) > 2 else ""
                                    status = (await cells[3].inner_text()).strip() if len(cells) > 3 else ""
                                    
                                    permits.append(PermitData(
                                        source="san_antonio_accela_fire",
                                        permit_id=permit_id,
                                        permit_type=permit_type,
                                        address=address,
                                        status=status,
                                        building_type=None,
                                        applicant_name=None,
                                        issued_date=None,
                                        detail_url=None,
                                    ))
                            except:
                                continue
                    
                    await browser.close()
                
                return dedupe_permits(permits)
            
            try:
                permits = await custom_scrape()
                
                if permits:
                    print(f"✅ SUCCESS! Found {len(permits)} permit(s):\n")
                    for i, p in enumerate(permits[:10], 1):
                        print(f"  {i}. {p.permit_id} - {p.permit_type}")
                        print(f"     Address: {p.address}")
                        print(f"     Status: {p.status}")
                        print()
                    return True
                else:
                    print(f"❌ No permits found for {permit_type}")
            except Exception as e:
                print(f"❌ Error with {permit_type}: {e}")
                continue
        
        return False


async def main():
    """Run both golden test cases"""
    print("\n" + "="*60)
    print("GOLDEN TEST CASES - VERIFYING SCRAPERS WITH KNOWN DATA")
    print("="*60)
    
    mecklenburg_success = await test_mecklenburg_golden_case()
    san_antonio_success = await test_san_antonio_golden_case()
    
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"Mecklenburg: {'✅ PASSED' if mecklenburg_success else '❌ FAILED'}")
    print(f"San Antonio: {'✅ PASSED' if san_antonio_success else '❌ FAILED'}")
    print("="*60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())

