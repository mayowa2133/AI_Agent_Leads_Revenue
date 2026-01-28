"""Debug detail page extraction to see what we're actually finding."""

from __future__ import annotations

import asyncio
from playwright.async_api import async_playwright
from src.signal_engine.scrapers.accela_scraper import create_accela_scraper


async def debug_extraction():
    """Debug what we're extracting from detail pages."""
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
                print("="*80)
                print("TESTING APPLICANT EXTRACTION")
                print("="*80)
                
                # Test applicant selectors
                applicant_selectors = [
                    '[id*="applicant" i]',
                    '[id*="contractor" i]',
                    'label:has-text("Applicant")',
                ]
                
                for selector in applicant_selectors:
                    elems = await page.query_selector_all(selector)
                    print(f"\nSelector '{selector}': Found {len(elems)} elements")
                    for i, elem in enumerate(elems[:3], 1):
                        tag = await elem.evaluate("el => el.tagName")
                        text = await elem.inner_text()
                        value = await elem.get_attribute('value')
                        
                        print(f"  Element {i}:")
                        print(f"    Tag: {tag}")
                        print(f"    Text: '{text[:100]}'")
                        if value:
                            print(f"    Value: '{value[:100]}'")
                        
                        # If it's a label, find associated element
                        if tag.lower() == 'label':
                            label_for = await elem.get_attribute('for')
                            if label_for:
                                assoc = await page.query_selector(f'#{label_for}')
                                if assoc:
                                    assoc_tag = await assoc.evaluate("el => el.tagName")
                                    assoc_text = await assoc.inner_text()
                                    assoc_value = await assoc.get_attribute('value')
                                    print(f"    Associated ({label_for}):")
                                    print(f"      Tag: {assoc_tag}")
                                    print(f"      Text: '{assoc_text[:100]}'")
                                    if assoc_value:
                                        print(f"      Value: '{assoc_value[:100]}'")
                            
                            # Try parent's siblings
                            try:
                                parent = await elem.evaluate_handle('el => el.parentElement')
                                if parent:
                                    siblings = await parent.evaluate("""
                                        (parent) => {
                                            const sibs = Array.from(parent.children);
                                            return sibs.map(s => ({
                                                tag: s.tagName,
                                                text: s.innerText.trim(),
                                                value: s.value || null
                                            }));
                                        }
                                    """)
                                    print(f"    Parent siblings: {siblings[:3]}")
                            except:
                                pass
                
                print("\n" + "="*80)
                print("TESTING ADDRESS EXTRACTION")
                print("="*80)
                
                # Test address selectors
                address_selectors = [
                    '[id*="address" i]',
                    '[id*="location" i]',
                    'label:has-text("Address")',
                    'label:has-text("Location")',
                ]
                
                for selector in address_selectors:
                    elems = await page.query_selector_all(selector)
                    print(f"\nSelector '{selector}': Found {len(elems)} elements")
                    for i, elem in enumerate(elems[:3], 1):
                        tag = await elem.evaluate("el => el.tagName")
                        text = await elem.inner_text()
                        value = await elem.get_attribute('value')
                        
                        print(f"  Element {i}:")
                        print(f"    Tag: {tag}")
                        print(f"    Text: '{text[:100]}'")
                        if value:
                            print(f"    Value: '{value[:100]}'")
                        
                        # If it's a label, find associated element
                        if tag.lower() == 'label':
                            label_for = await elem.get_attribute('for')
                            if label_for:
                                assoc = await page.query_selector(f'#{label_for}')
                                if assoc:
                                    assoc_tag = await assoc.evaluate("el => el.tagName")
                                    assoc_text = await assoc.inner_text()
                                    assoc_value = await assoc.get_attribute('value')
                                    print(f"    Associated ({label_for}):")
                                    print(f"      Tag: {assoc_tag}")
                                    print(f"      Text: '{assoc_text[:100]}'")
                                    if assoc_value:
                                        print(f"      Value: '{assoc_value[:100]}'")
        
        await browser.close()


if __name__ == "__main__":
    asyncio.run(debug_extraction())
