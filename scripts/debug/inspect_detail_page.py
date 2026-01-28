"""Inspect detail page structure to understand how to extract actual values."""

from __future__ import annotations

import asyncio
from playwright.async_api import async_playwright
from src.signal_engine.scrapers.accela_scraper import create_accela_scraper


async def inspect_detail_page():
    """Inspect a detail page to see the HTML structure."""
    scraper = create_accela_scraper("COSA", "Fire", days_back=30, max_pages=1)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # Navigate and search
        await scraper._run_search(page)
        
        # Get first permit's detail link
        rows = await page.query_selector_all('table.aca_grid_table tbody tr:not(.aca_grid_header)')
        if rows:
            detail_link = await rows[0].query_selector('td:nth-child(2) a')
            if detail_link:
                # Click to open detail page
                async with page.expect_navigation(timeout=15000, wait_until="networkidle"):
                    await detail_link.click()
                await page.wait_for_timeout(3000)
                
                print("="*80)
                print("DETAIL PAGE STRUCTURE ANALYSIS")
                print("="*80)
                print(f"\nCurrent URL: {page.url}\n")
                
                # Look for applicant-related elements
                print("APPLICANT ELEMENTS:")
                print("-"*80)
                
                # Try various selectors
                applicant_selectors = [
                    '[id*="applicant" i]',
                    '[id*="contractor" i]',
                    '[id*="owner" i]',
                    'label:has-text("Applicant")',
                    'label:has-text("Contractor")',
                ]
                
                for selector in applicant_selectors:
                    elems = await page.query_selector_all(selector)
                    if elems:
                        print(f"\nSelector: {selector}")
                        for i, elem in enumerate(elems[:3], 1):
                            tag = await elem.evaluate("el => el.tagName")
                            text = await elem.inner_text()
                            html = await elem.inner_html()
                            value = await elem.get_attribute('value') if tag.lower() == 'input' else None
                            
                            print(f"  Element {i}:")
                            print(f"    Tag: {tag}")
                            print(f"    Text: {text[:100]}")
                            if value:
                                print(f"    Value: {value[:100]}")
                            print(f"    HTML: {html[:200]}")
                            
                            # Try to find associated input/span
                            if tag.lower() == 'label':
                                label_for = await elem.get_attribute('for')
                                if label_for:
                                    associated = await page.query_selector(f'#{label_for}')
                                    if associated:
                                        assoc_text = await associated.inner_text()
                                        assoc_value = await associated.get_attribute('value')
                                        print(f"    Associated element (for={label_for}):")
                                        print(f"      Text: {assoc_text[:100]}")
                                        if assoc_value:
                                            print(f"      Value: {assoc_value[:100]}")
                
                # Look for address-related elements
                print("\n\nADDRESS ELEMENTS:")
                print("-"*80)
                
                address_selectors = [
                    '[id*="address" i]',
                    '[id*="location" i]',
                    '[id*="site" i]',
                    'label:has-text("Address")',
                    'label:has-text("Location")',
                ]
                
                for selector in address_selectors:
                    elems = await page.query_selector_all(selector)
                    if elems:
                        print(f"\nSelector: {selector}")
                        for i, elem in enumerate(elems[:3], 1):
                            tag = await elem.evaluate("el => el.tagName")
                            text = await elem.inner_text()
                            html = await elem.inner_html()
                            value = await elem.get_attribute('value') if tag.lower() == 'input' else None
                            
                            print(f"  Element {i}:")
                            print(f"    Tag: {tag}")
                            print(f"    Text: {text[:100]}")
                            if value:
                                print(f"    Value: {value[:100]}")
                            print(f"    HTML: {html[:200]}")
                            
                            # Try to find associated input/span
                            if tag.lower() == 'label':
                                label_for = await elem.get_attribute('for')
                                if label_for:
                                    associated = await page.query_selector(f'#{label_for}')
                                    if associated:
                                        assoc_text = await associated.inner_text()
                                        assoc_value = await associated.get_attribute('value')
                                        print(f"    Associated element (for={label_for}):")
                                        print(f"      Text: {assoc_text[:100]}")
                                        if assoc_value:
                                            print(f"      Value: {assoc_value[:100]}")
                
                # Look at table structures
                print("\n\nTABLE STRUCTURES:")
                print("-"*80)
                tables = await page.query_selector_all('table')
                for i, table in enumerate(tables[:2], 1):
                    table_text = await table.inner_text()
                    if any(term in table_text.lower() for term in ['applicant', 'address', 'location', 'contractor']):
                        print(f"\nTable {i}:")
                        rows = await table.query_selector_all('tr')
                        for j, row in enumerate(rows[:5], 1):
                            row_text = await row.inner_text()
                            if any(term in row_text.lower() for term in ['applicant', 'address', 'location']):
                                print(f"  Row {j}: {row_text[:150]}")
                                cells = await row.query_selector_all('td, th')
                                for k, cell in enumerate(cells):
                                    cell_text = await cell.inner_text()
                                    if cell_text.strip():
                                        print(f"    Cell {k}: {cell_text[:80]}")
        
        await browser.close()


if __name__ == "__main__":
    asyncio.run(inspect_detail_page())
