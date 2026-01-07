from __future__ import annotations

import asyncio
import os

from playwright.async_api import async_playwright


async def main():
    """
    Debug script to inspect Mecklenburg County portal page structure.
    This helps us understand what selectors we need.
    """
    street_name = os.environ.get("STREET_NAME", "Main")
    url = "https://webpermit.mecklenburgcountync.gov/Default.aspx?PosseMenuName=ViewPermits"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # Show browser for debugging
        page = await browser.new_page()
        
        print(f"Navigating to: {url}\n")
        await page.goto(url, wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(1000)
        
        # Click "By Address" link
        print("Clicking 'By Address' link...\n")
        by_address_link = await page.query_selector('a[href*="SearchByAddress"]') or \
                         await page.query_selector('a:has-text("By Address")')
        if by_address_link:
            await by_address_link.click()
            await page.wait_for_load_state("networkidle")
            await page.wait_for_timeout(2000)
            print("✓ Navigated to search form\n")
        else:
            print("✗ Could not find 'By Address' link\n")
        
        # Find and fill street input
        print(f"Looking for street name input to fill with: '{street_name}'...\n")
        street_input = None
        for selector in [
            'input[name*="Street"]',
            'input[id*="Street"]',
            'input[type="text"]:not([type="hidden"])',
        ]:
            candidates = await page.query_selector_all(selector)
            for candidate in candidates:
                inp_type = await candidate.get_attribute("type")
                if inp_type != "hidden":
                    street_input = candidate
                    print(f"✓ Found input field with selector: {selector}\n")
                    break
            if street_input:
                break
        
        if street_input:
            await street_input.fill(street_name)
            await page.wait_for_timeout(500)
            print(f"✓ Filled street name: '{street_name}'\n")
            
            # Find and click submit - might be a link or image button
            submit_btn = None
            for selector in [
                'input[type="submit"]',
                'button[type="submit"]',
                'input[value*="Search"]',
                'a:has-text("Search")',
                'img[alt*="Search"]',
                'input[type="image"]',
            ]:
                btn = await page.query_selector(selector)
                if btn:
                    submit_btn = btn
                    print(f"✓ Found submit element with selector: {selector}\n")
                    break
            
            if submit_btn:
                print("Clicking submit...\n")
                await submit_btn.click()
                await page.wait_for_load_state("networkidle")
                await page.wait_for_timeout(3000)
                print("✓ Form submitted, waiting for results...\n")
            else:
                print("✗ Could not find submit button/link\n")
                print("Checking for all links and images on page...\n")
                links = await page.query_selector_all("a, input[type='image'], img[onclick]")
                print(f"Found {len(links)} potential clickable elements:\n")
                for i, link in enumerate(links[:10], 1):  # First 10
                    text = await link.inner_text() or ""
                    href = await link.get_attribute("href") or ""
                    alt = await link.get_attribute("alt") or ""
                    onclick = await link.get_attribute("onclick") or ""
                    print(f"  {i}. text='{text[:30]}', href='{href[:50]}', alt='{alt}', onclick='{onclick[:50]}'")
        
        # Wait a bit for any dynamic content
        await page.wait_for_timeout(2000)
        
        # Check for the results table (after form submission)
        print("\n" + "="*60)
        print("Checking for results table...")
        print("="*60 + "\n")
        
        table = await page.query_selector("table.PosseSearchResultGrid")
        if table:
            print("✓ Found table.PosseSearchResultGrid\n")
            
            # Count rows
            rows = await page.query_selector_all("table.PosseSearchResultGrid tbody tr")
            print(f"Found {len(rows)} total rows in tbody\n")
            
            # Check for specific row classes
            posse_rows = await page.query_selector_all("tr.PosseGridRow, tr.PosseGridAltRow")
            print(f"Found {len(posse_rows)} rows with PosseGridRow/PosseGridAltRow classes\n")
            
            # If we have rows, show first row structure
            if posse_rows:
                first_row = posse_rows[0]
                cells = await first_row.query_selector_all("td")
                print(f"First row has {len(cells)} cells (td elements)\n")
                
                # Print cell contents
                for i, cell in enumerate(cells[:5], 1):  # First 5 cells
                    text = await cell.inner_text()
                    print(f"  Cell {i}: {text.strip()[:50]}")
                
                # Check for links in first cell
                first_cell = cells[0] if cells else None
                if first_cell:
                    link = await first_cell.query_selector("a")
                    if link:
                        href = await link.get_attribute("href")
                        print(f"\n  First cell has a link: {href}")
        else:
            print("✗ table.PosseSearchResultGrid NOT found\n")
            print("Checking for other tables...")
            all_tables = await page.query_selector_all("table")
            print(f"Found {len(all_tables)} total tables on page\n")
            
            # Show page title and some text to understand what we're looking at
            title = await page.title()
            print(f"Page title: {title}\n")
            
            # Check if there's a form or search interface
            form = await page.query_selector("form")
            if form:
                print("Found a form - page may require form submission first\n")
                
                # List all input fields
                inputs = await page.query_selector_all("input")
                print(f"Found {len(inputs)} input fields:")
                for inp in inputs:
                    inp_type = await inp.get_attribute("type") or "text"
                    inp_name = await inp.get_attribute("name") or ""
                    inp_id = await inp.get_attribute("id") or ""
                    inp_placeholder = await inp.get_attribute("placeholder") or ""
                    print(f"  - type={inp_type}, name={inp_name}, id={inp_id}, placeholder={inp_placeholder}")
                
                # List all buttons
                buttons = await page.query_selector_all("button, input[type='submit'], input[type='button']")
                print(f"\nFound {len(buttons)} buttons/submit elements:")
                for btn in buttons:
                    btn_type = await btn.get_attribute("type") or ""
                    btn_value = await btn.get_attribute("value") or ""
                    btn_text = await btn.inner_text() or ""
                    print(f"  - type={btn_type}, value={btn_value}, text={btn_text[:50]}")
        
        print("\n" + "="*60)
        print("Keeping browser open for 10 seconds so you can inspect...")
        print("="*60)
        await page.wait_for_timeout(10000)
        
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())

