"""Comprehensive inspection of detail page to find where company names and addresses are stored."""

from __future__ import annotations

import asyncio
from playwright.async_api import async_playwright
from src.signal_engine.scrapers.accela_scraper import create_accela_scraper


async def inspect_comprehensive():
    """Comprehensive inspection of detail page structure."""
    scraper = create_accela_scraper("COSA", "Fire", days_back=30, max_pages=1)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)  # Use headless=True for automated inspection
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
                print("="*80)
                print("CHECKING FOR TABS")
                print("="*80)
                tabs = await page.query_selector_all('a[href*="TabName"], .tab, [class*="tab"], [id*="tab"]')
                if tabs:
                    print(f"Found {len(tabs)} potential tabs:")
                    for i, tab in enumerate(tabs[:10], 1):
                        try:
                            tab_text = await tab.inner_text()
                            href = await tab.get_attribute('href')
                            print(f"  Tab {i}: '{tab_text[:50]}' - href: {href[:80] if href else 'None'}")
                        except:
                            pass
                else:
                    print("No tabs found")
                
                # Get full page text
                print("\n" + "="*80)
                print("FULL PAGE TEXT (first 2000 chars)")
                print("="*80)
                page_text = await page.inner_text('body')
                print(page_text[:2000])
                
                # Search for "Company Name" in page text
                print("\n" + "="*80)
                print("SEARCHING FOR 'Company Name' IN PAGE TEXT")
                print("="*80)
                if 'Company Name' in page_text or 'company name' in page_text.lower():
                    # Find the line containing "Company Name"
                    lines = page_text.split('\n')
                    for i, line in enumerate(lines):
                        if 'Company Name' in line or 'company name' in line.lower():
                            print(f"Line {i}: {line[:200]}")
                            # Show context (2 lines before and after)
                            for j in range(max(0, i-2), min(len(lines), i+3)):
                                if j != i:
                                    print(f"  Context {j}: {lines[j][:150]}")
                            break
                else:
                    print("'Company Name' NOT FOUND in page text!")
                
                # Search for address patterns
                print("\n" + "="*80)
                print("SEARCHING FOR ADDRESS PATTERNS")
                print("="*80)
                address_keywords = ['Address', 'Location', 'Street', 'Avenue', 'Road']
                found_address = False
                for keyword in address_keywords:
                    if keyword in page_text:
                        found_address = True
                        lines = page_text.split('\n')
                        for i, line in enumerate(lines):
                            if keyword in line and len(line.strip()) > 5:
                                print(f"Found '{keyword}' in line {i}: {line[:200]}")
                                break
                if not found_address:
                    print("No address patterns found")
                
                # Get HTML structure around "Company Name"
                print("\n" + "="*80)
                print("HTML STRUCTURE AROUND 'Company Name'")
                print("="*80)
                try:
                    # Try to find element containing "Company Name"
                    company_elem = await page.evaluate("""
                        () => {
                            const walker = document.createTreeWalker(
                                document.body,
                                NodeFilter.SHOW_TEXT,
                                null
                            );
                            let node;
                            while (node = walker.nextNode()) {
                                if (node.textContent.includes('Company Name')) {
                                    // Get parent element
                                    let parent = node.parentElement;
                                    for (let i = 0; i < 5 && parent; i++) {
                                        if (parent.tagName === 'TD' || parent.tagName === 'DIV' || parent.tagName === 'SPAN') {
                                            return {
                                                tag: parent.tagName,
                                                id: parent.id || '',
                                                className: parent.className || '',
                                                innerHTML: parent.innerHTML.substring(0, 500),
                                                innerText: parent.innerText.substring(0, 200)
                                            };
                                        }
                                        parent = parent.parentElement;
                                    }
                                }
                            }
                            return null;
                        }
                    """)
                    if company_elem:
                        print(f"Tag: {company_elem['tag']}")
                        print(f"ID: {company_elem['id']}")
                        print(f"Class: {company_elem['className']}")
                        print(f"Text: {company_elem['innerText']}")
                        print(f"HTML: {company_elem['innerHTML'][:300]}")
                    else:
                        print("Could not find HTML element containing 'Company Name'")
                except Exception as e:
                    print(f"Error getting HTML structure: {e}")
                
                # Inspection complete
                print("\n" + "="*80)
                print("Inspection complete")
                print("="*80)
        
        await browser.close()


if __name__ == "__main__":
    asyncio.run(inspect_comprehensive())
