from __future__ import annotations

import asyncio
from playwright.async_api import async_playwright


async def main():
    """Simple Mecklenburg test - just get to results page and inspect"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            # Navigate
            await page.goto("https://webpermit.mecklenburgcountync.gov/", wait_until="networkidle", timeout=60000)
            await page.wait_for_timeout(2000)
            print("✓ Loaded home page")
            
            # View Permits
            view_permits = await page.query_selector('a:has-text("View Permits")')
            if view_permits:
                await view_permits.click()
                await page.wait_for_load_state("networkidle", timeout=60000)
                await page.wait_for_timeout(2000)
                print("✓ Clicked View Permits")
            
            # By Project Name
            by_project = await page.query_selector('a:has-text("By Project Name")')
            if by_project:
                await by_project.click()
                await page.wait_for_load_state("networkidle", timeout=60000)
                await page.wait_for_timeout(3000)
                print("✓ Clicked By Project Name")
            
            # Fill with simple term
            project_input = await page.query_selector('input[name*="ProjectName"], input[id*="ProjectName"]')
            if project_input:
                await project_input.fill("Test")
                print("✓ Filled 'Test'")
                await page.wait_for_timeout(1000)
            
            # Submit
            submit_btn = await page.query_selector('a[id*="PerformSearch"]')
            if submit_btn:
                btn_id = await submit_btn.get_attribute("id")
                print(f"✓ Found button: {btn_id}")
                
                # Click and wait for navigation
                async with page.expect_navigation(timeout=60000, wait_until="networkidle"):
                    await page.evaluate(f"""
                        const btn = document.getElementById('{btn_id}');
                        if (btn && btn.onclick) {{
                            btn.onclick();
                        }} else if (btn) {{
                            btn.click();
                        }}
                    """)
                print("✓ Navigation completed")
                await page.wait_for_timeout(3000)
            
            # Now check for results
            current_url = page.url
            print(f"\n📄 Final URL: {current_url}")
            
            # Look for results table
            results_table = await page.query_selector('#ctl00_MainContent_dgResults')
            if results_table:
                print("\n✅ FOUND RESULTS TABLE!")
                rows = await results_table.query_selector_all("tr:not(.PosseGridHeader)")
                print(f"📊 Found {len(rows)} data rows\n")
                
                # Extract and display first 5 permits
                for i, row in enumerate(rows[:5], 1):
                    try:
                        cells = await row.query_selector_all("td")
                        if len(cells) >= 4:
                            permit_id = (await cells[0].inner_text()).strip()
                            permit_type = (await cells[2].inner_text()).strip() if len(cells) > 2 else ""
                            address = (await cells[1].inner_text()).strip() if len(cells) > 1 else ""
                            status = (await cells[3].inner_text()).strip() if len(cells) > 3 else ""
                            
                            print(f"  Permit {i}:")
                            print(f"    ID: {permit_id}")
                            print(f"    Type: {permit_type}")
                            print(f"    Address: {address}")
                            print(f"    Status: {status}")
                            print()
                    except Exception as e:
                        print(f"  Row {i} error: {e}")
            else:
                print("\n❌ Results table not found")
                # Save page HTML for inspection
                page_html = await page.content()
                with open("debug_mecklenburg_final_page.html", "w", encoding="utf-8") as f:
                    f.write(page_html)
                print("💾 Saved page HTML: debug_mecklenburg_final_page.html")
            
            # Screenshot
            await page.screenshot(path="debug_mecklenburg_final.png", full_page=True)
            print("📸 Screenshot: debug_mecklenburg_final.png")
            
            print("\n⏳ Keeping browser open for 60 seconds...")
            await page.wait_for_timeout(60000)
            
        finally:
            await browser.close()


if __name__ == "__main__":
    asyncio.run(main())

