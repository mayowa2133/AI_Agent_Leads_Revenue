"""Debug script to inspect Accela table structure and fix extraction."""

from __future__ import annotations

import asyncio
from playwright.async_api import async_playwright


async def debug_accela_table_structure():
    """Inspect the actual HTML structure of Accela results table."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # Show browser for debugging
        page = await browser.new_page()
        
        # Navigate to San Antonio Fire permits
        url = "https://aca-prod.accela.com/COSA/Cap/CapHome.aspx?module=Fire"
        await page.goto(url, wait_until="networkidle")
        await page.wait_for_timeout(2000)
        
        # Click Global Search
        try:
            global_search_btn = await page.query_selector('a[href*="GlobalSearch"]')
            if global_search_btn:
                print("Clicking Global Search...")
                await global_search_btn.click()
                await page.wait_for_timeout(2000)
        except Exception as e:
            print(f"Could not click Global Search: {e}")
        
        # Try JavaScript GlobalSearch function
        try:
            print("Trying JavaScript GlobalSearch...")
            await page.evaluate("""
                if (typeof GlobalSearch === 'function') {
                    GlobalSearch();
                }
            """)
            await page.wait_for_timeout(2000)
        except Exception as e:
            print(f"JavaScript GlobalSearch failed: {e}")
        
        # Wait for navigation to results page
        try:
            print("Waiting for results page...")
            await page.wait_for_url("**/GlobalSearchResults*", timeout=10000)
            await page.wait_for_timeout(3000)
        except Exception as e:
            print(f"Did not navigate to results page: {e}")
            # Try clicking search button
            try:
                search_btn = await page.query_selector('input[type="submit"][value*="Search"], button[type="submit"], input[id*="btnSearch"]')
                if search_btn:
                    print("Clicking search button...")
                    await search_btn.click()
                    await page.wait_for_load_state("networkidle", timeout=15000)
                    await page.wait_for_timeout(3000)
            except Exception as e2:
                print(f"Could not click search: {e2}")
        
        # Check if we're on results page
        page_url = page.url
        print(f"Current URL: {page_url}")
        
        if "GlobalSearchResults" in page_url:
            print("\n✅ On GlobalSearchResults page")
            
            # Find all rows
            rows = await page.query_selector_all('table.aca_grid_table tbody tr:not(.aca_grid_header), table[id*="grid"] tbody tr:not(:first-child), table[id*="gvPermitList"] tbody tr:not(:first-child)')
            if not rows:
                rows = await page.query_selector_all('table.aca_grid_table tr:not(.aca_grid_header), table[id*="grid"] tr:not(:first-child)')
            if not rows:
                rows = await page.query_selector_all('table tbody tr:not(:first-child), table tr:not(:first-child)')
            
            print(f"Found {len(rows)} rows")
            
            # Inspect first few data rows
            for i, row in enumerate(rows[:3], 1):
                print(f"\n{'='*80}")
                print(f"ROW {i}")
                print(f"{'='*80}")
                
                # Get row HTML
                row_html = await row.inner_html()
                print(f"Row HTML (first 500 chars): {row_html[:500]}")
                
                # Get row text
                row_text = await row.inner_text()
                print(f"\nRow Text:\n{row_text}")
                
                # Get all cells
                cells = await row.query_selector_all('td, th')
                print(f"\nNumber of cells: {len(cells)}")
                
                for j, cell in enumerate(cells):
                    cell_text = await cell.inner_text()
                    cell_html = await cell.inner_html()
                    print(f"\n  Cell {j}:")
                    print(f"    Text: {cell_text[:100]}")
                    print(f"    HTML: {cell_html[:200]}")
                    
                    # Check for links
                    links = await cell.query_selector_all('a')
                    if links:
                        for link in links:
                            href = await link.get_attribute('href')
                            link_text = await link.inner_text()
                            print(f"    Link: {link_text} -> {href[:100] if href else 'None'}")
                
                # Try our selectors
                print(f"\n  Testing Selectors:")
                permit_id_elem = await row.query_selector('td:nth-child(2)')
                permit_type_elem = await row.query_selector('td:nth-child(3)')
                address_elem = await row.query_selector('td:nth-child(5)')
                status_elem = await row.query_selector('td:nth-child(6)')
                
                print(f"    td:nth-child(2) (permit_id): {await permit_id_elem.inner_text() if permit_id_elem else 'NOT FOUND'}")
                print(f"    td:nth-child(3) (permit_type): {await permit_type_elem.inner_text() if permit_type_elem else 'NOT FOUND'}")
                print(f"    td:nth-child(5) (address): {await address_elem.inner_text() if address_elem else 'NOT FOUND'}")
                print(f"    td:nth-child(6) (status): {await status_elem.inner_text() if status_elem else 'NOT FOUND'}")
        
        # Keep browser open for manual inspection
        print("\n" + "="*80)
        print("Browser will stay open for 30 seconds for manual inspection...")
        print("="*80)
        await page.wait_for_timeout(30000)
        
        await browser.close()


if __name__ == "__main__":
    asyncio.run(debug_accela_table_structure())
