"""Inspect what addresses are actually in the results table."""

from __future__ import annotations

import asyncio
from playwright.async_api import async_playwright
from src.signal_engine.scrapers.accela_scraper import create_accela_scraper


async def inspect_addresses():
    """Inspect addresses in results table."""
    scraper = create_accela_scraper("COSA", "Fire", days_back=30, max_pages=1)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # Navigate and search
        await scraper._run_search(page)
        
        # Get all rows
        rows = await page.query_selector_all('table.aca_grid_table tbody tr:not(.aca_grid_header)')
        print(f"Found {len(rows)} data rows\n")
        
        # Inspect first 5 rows for addresses
        for idx, row in enumerate(rows[:5], 1):
            try:
                # Get all cells in the row
                cells = await row.query_selector_all('td')
                print(f"Row {idx}: {len(cells)} cells")
                
                # Try to find address column (usually column 4 or 5)
                for cell_idx, cell in enumerate(cells):
                    cell_text = (await cell.inner_text()).strip()
                    if cell_text and len(cell_text) > 0:
                        # Check if it looks like an address
                        has_number = any(char.isdigit() for char in cell_text)
                        has_street_word = any(word in cell_text.lower() for word in ['st', 'street', 'ave', 'avenue', 'rd', 'road', 'dr', 'drive', 'blvd'])
                        
                        if has_number or has_street_word or len(cell_text) > 10:
                            print(f"  Cell {cell_idx}: '{cell_text[:100]}'")
                            if has_number and has_street_word:
                                print(f"    ✓ Looks like an address!")
                            elif has_number:
                                print(f"    ? Has numbers, might be address")
                print()
            except Exception as e:
                print(f"  Error inspecting row {idx}: {e}")
        
        await browser.close()


if __name__ == "__main__":
    asyncio.run(inspect_addresses())
