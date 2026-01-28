"""Comprehensive inspection of Accela detail page structure."""

from __future__ import annotations

import asyncio
from playwright.async_api import async_playwright
from src.signal_engine.scrapers.accela_scraper import create_accela_scraper


async def inspect_structure():
    """Inspect detail page HTML structure comprehensively."""
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
                permit_id = await (await rows[0].query_selector('td:nth-child(2)')).inner_text()
                print(f"Opening detail page for: {permit_id.strip()}\n")
                
                # Click to open detail page
                async with page.expect_navigation(timeout=15000, wait_until="networkidle"):
                    await detail_link.click()
                await page.wait_for_timeout(3000)
                
                print(f"Detail page URL: {page.url}\n")
                
                # Check for tabs
                tabs = await page.query_selector_all('a[href*="TabName"], .tab, [class*="tab"]')
                if tabs:
                    print(f"Found {len(tabs)} potential tabs")
                    for i, tab in enumerate(tabs[:5], 1):
                        tab_text = await tab.inner_text()
                        print(f"  Tab {i}: {tab_text[:50]}")
                
                # Get page structure
                structure = await page.evaluate("""
                    () => {
                        const result = {
                            hasApplicant: false,
                            hasAddress: false,
                            applicantElements: [],
                            addressElements: [],
                            tables: [],
                            inputs: []
                        };
                        
                        // Search for applicant-related elements
                        const applicantSelectors = [
                            '[id*="applicant" i]',
                            '[id*="contractor" i]',
                            '[name*="applicant" i]',
                            '[name*="contractor" i]'
                        ];
                        
                        for (const selector of applicantSelectors) {
                            const elems = document.querySelectorAll(selector);
                            for (const elem of elems) {
                                const tag = elem.tagName;
                                const id = elem.id || '';
                                const name = elem.name || '';
                                const value = elem.value || '';
                                const text = elem.innerText || '';
                                
                                result.applicantElements.push({
                                    selector: selector,
                                    tag: tag,
                                    id: id,
                                    name: name,
                                    value: value.substring(0, 100),
                                    text: text.substring(0, 100)
                                });
                                result.hasApplicant = true;
                            }
                        }
                        
                        // Search for address-related elements
                        const addressSelectors = [
                            '[id*="address" i]',
                            '[id*="location" i]',
                            '[name*="address" i]',
                            '[name*="location" i]'
                        ];
                        
                        for (const selector of addressSelectors) {
                            const elems = document.querySelectorAll(selector);
                            for (const elem of elems) {
                                const tag = elem.tagName;
                                const id = elem.id || '';
                                const name = elem.name || '';
                                const value = elem.value || '';
                                const text = elem.innerText || '';
                                
                                result.addressElements.push({
                                    selector: selector,
                                    tag: tag,
                                    id: id,
                                    name: name,
                                    value: value.substring(0, 100),
                                    text: text.substring(0, 100)
                                });
                                result.hasAddress = true;
                            }
                        }
                        
                        // Get all tables
                        const tables = document.querySelectorAll('table');
                        for (const table of tables) {
                            const tableText = table.innerText || '';
                            if (tableText.length > 0 && tableText.length < 500) {
                                result.tables.push({
                                    rowCount: table.querySelectorAll('tr').length,
                                    text: tableText.substring(0, 200)
                                });
                            }
                        }
                        
                        // Get all input fields with values
                        const inputs = document.querySelectorAll('input[value], textarea');
                        for (const input of inputs) {
                            const value = input.value || '';
                            if (value.length > 2 && value.length < 200) {
                                result.inputs.push({
                                    tag: input.tagName,
                                    id: input.id || '',
                                    name: input.name || '',
                                    type: input.type || '',
                                    value: value.substring(0, 100)
                                });
                            }
                        }
                        
                        return result;
                    }
                """)
                
                print("="*80)
                print("APPLICANT ELEMENTS FOUND")
                print("="*80)
                if structure['hasApplicant']:
                    for elem in structure['applicantElements'][:10]:
                        print(f"\nTag: {elem['tag']}, ID: {elem['id']}, Name: {elem['name']}")
                        print(f"  Value: '{elem['value']}'")
                        print(f"  Text: '{elem['text']}'")
                else:
                    print("No applicant elements found with standard selectors")
                
                print("\n" + "="*80)
                print("ADDRESS ELEMENTS FOUND")
                print("="*80)
                if structure['hasAddress']:
                    for elem in structure['addressElements'][:10]:
                        print(f"\nTag: {elem['tag']}, ID: {elem['id']}, Name: {elem['name']}")
                        print(f"  Value: '{elem['value']}'")
                        print(f"  Text: '{elem['text']}'")
                else:
                    print("No address elements found with standard selectors")
                
                print("\n" + "="*80)
                print("INPUT FIELDS WITH VALUES")
                print("="*80)
                for inp in structure['inputs'][:15]:
                    print(f"\n{inp['tag']} - ID: {inp['id']}, Name: {inp['name']}, Type: {inp['type']}")
                    print(f"  Value: '{inp['value']}'")
                
                print("\n" + "="*80)
                print("TABLES FOUND")
                print("="*80)
                for i, table in enumerate(structure['tables'][:5], 1):
                    print(f"\nTable {i} ({table['rowCount']} rows):")
                    print(f"  Text: {table['text'][:300]}")
        
        await browser.close()


if __name__ == "__main__":
    asyncio.run(inspect_structure())
