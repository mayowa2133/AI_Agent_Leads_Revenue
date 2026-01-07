from __future__ import annotations

import asyncio
from playwright.async_api import async_playwright


async def main():
    """Inspect Mecklenburg page to find submit button"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        # Navigate to home
        await page.goto("https://webpermit.mecklenburgcountync.gov/", wait_until="networkidle")
        await page.wait_for_timeout(1000)
        
        # Click View Permits
        view_permits = await page.query_selector('a:has-text("View Permits")')
        if view_permits:
            await view_permits.click()
            await page.wait_for_load_state("networkidle")
            await page.wait_for_timeout(1500)
        
        # Click By Address
        by_address = await page.query_selector('a:has-text("By Address")')
        if by_address:
            await by_address.click()
            await page.wait_for_load_state("networkidle")
            await page.wait_for_timeout(2000)
        
        # Fill form
        street_num = await page.query_selector('input[name*="StreetNumber"], input[id*="StreetNumber"]')
        street_name = await page.query_selector('input[name*="StreetName"], input[id*="StreetName"]')
        
        if street_num and street_name:
            await street_num.fill("111")
            await street_name.fill("E CARSON")
            await page.wait_for_timeout(500)
        
        # Find ALL buttons/inputs on the page
        print("\n🔍 Searching for submit buttons...")
        all_buttons = await page.query_selector_all('input, button, a[onclick]')
        print(f"Found {len(all_buttons)} button-like elements\n")
        
        for i, btn in enumerate(all_buttons[:30]):  # First 30
            btn_type = await btn.get_attribute("type")
            btn_id = await btn.get_attribute("id")
            btn_name = await btn.get_attribute("name")
            btn_value = await btn.get_attribute("value")
            btn_class = await btn.get_attribute("class")
            btn_onclick = await btn.get_attribute("onclick")
            try:
                btn_text = await btn.inner_text()
            except:
                btn_text = ""
            
            # Show buttons that might be submit buttons
            if (btn_type in ["submit", "button", "image"] or 
                btn_value and "search" in btn_value.lower() or
                btn_id and "search" in btn_id.lower() or
                btn_id and "btn" in btn_id.lower() or
                btn_onclick):
                print(f"  Button {i+1}:")
                print(f"    type={btn_type}, id={btn_id}, name={btn_name}")
                print(f"    value={btn_value}, class={btn_class}")
                print(f"    onclick={btn_onclick[:50] if btn_onclick else None}")
                print(f"    text={btn_text[:30]}")
                print()
        
        print("\n⏳ Keeping browser open for 30 seconds for manual inspection...")
        await page.wait_for_timeout(30000)
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())

