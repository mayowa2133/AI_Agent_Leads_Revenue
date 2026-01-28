"""Debug Accela table structure using the actual scraper logic."""

from __future__ import annotations

import asyncio
from playwright.async_api import async_playwright
from src.signal_engine.scrapers.accela_scraper import AccelaScraper


async def debug_table_structure():
    """Use the scraper to get to results page, then inspect structure."""
    scraper = AccelaScraper(
        city_code="COSA",
        module="Fire",
        days_back=30,
        max_pages=1,
        extract_applicant=False,  # Disable for debugging
    )
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # Navigate to start URL and run search
        await page.goto(scraper.start_url, wait_until="networkidle")
        await page.wait_for_timeout(2000)
        
        # Run search using scraper's method
        await scraper._run_search(page)
        
        # Now we should be on results page - inspect it
        page_url = page.url
        print(f"Current URL: {page_url}")
        
        # Find rows using scraper's selectors
        rows = await page.query_selector_all('table.aca_grid_table tbody tr:not(.aca_grid_header), table[id*="grid"] tbody tr:not(:first-child), table[id*="gvPermitList"] tbody tr:not(:first-child)')
        if not rows:
            rows = await page.query_selector_all('table.aca_grid_table tr:not(.aca_grid_header), table[id*="grid"] tr:not(:first-child)')
        if not rows:
            rows = await page.query_selector_all('table tbody tr:not(:first-child), table tr:not(:first-child)')
        
        print(f"\nFound {len(rows)} rows")
        
        # Inspect first 2 data rows (skip header)
        for i, row in enumerate(rows[:2], 1):
            print(f"\n{'='*80}")
            print(f"ROW {i}")
            print(f"{'='*80}")
            
            # Get row text
            row_text = await row.inner_text()
            print(f"Row Text:\n{row_text}")
            
            # Get all cells
            cells = await row.query_selector_all('td, th')
            print(f"\nNumber of cells: {len(cells)}")
            
            for j, cell in enumerate(cells):
                cell_text = await cell.inner_text()
                print(f"  Cell {j}: '{cell_text[:80]}'")
                
                # Check for links
                links = await cell.query_selector_all('a')
                if links:
                    for link in links:
                        href = await link.get_attribute('href')
                        link_text = await link.inner_text()
                        print(f"    -> Link: '{link_text}' -> {href[:80] if href else 'None'}")
            
            # Test our selectors
            print(f"\n  Testing Selectors:")
            permit_id_elem = await row.query_selector('td:nth-child(2)')
            permit_type_elem = await row.query_selector('td:nth-child(3)')
            address_elem = await row.query_selector('td:nth-child(5)')
            status_elem = await row.query_selector('td:nth-child(6)')
            
            print(f"    td:nth-child(2) (permit_id): {await permit_id_elem.inner_text() if permit_id_elem else 'NOT FOUND'}")
            print(f"    td:nth-child(3) (permit_type): {await permit_type_elem.inner_text() if permit_type_elem else 'NOT FOUND'}")
            print(f"    td:nth-child(5) (address): {await address_elem.inner_text() if address_elem else 'NOT FOUND'}")
            print(f"    td:nth-child(6) (status): {await status_elem.inner_text() if status_elem else 'NOT FOUND'}")
            
            # Test evaluate function
            print(f"\n  Testing Evaluate Function:")
            row_data = await row.evaluate("""
                (row) => {
                    const cells = row.querySelectorAll('td');
                    if (cells.length < 3) return {error: 'Not enough cells', count: cells.length};
                    
                    const result = {
                        cell_count: cells.length,
                        cells: []
                    };
                    
                    for (let i = 0; i < cells.length; i++) {
                        result.cells.push({
                            index: i,
                            text: cells[i].innerText.trim(),
                            has_link: cells[i].querySelector('a') !== null
                        });
                    }
                    
                    // Try to extract permit data
                    const permitId = cells[1] ? cells[1].innerText.trim() : '';
                    const permitType = cells[2] ? cells[2].innerText.trim() : '';
                    
                    result.permit_id = permitId;
                    result.permit_type = permitType;
                    result.address = cells[4] ? cells[4].innerText.trim() : '';
                    result.status = cells[5] ? cells[5].innerText.trim() : '';
                    
                    return result;
                }
            """)
            print(f"    Evaluate result: {row_data}")
        
        await browser.close()


if __name__ == "__main__":
    asyncio.run(debug_table_structure())
