"""Check what's actually on detail pages."""

from __future__ import annotations

import asyncio
from playwright.async_api import async_playwright
from src.signal_engine.scrapers.accela_scraper import create_accela_scraper


async def check_content():
    """Check detail page content."""
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
                
                # Get page text
                page_text = await page.inner_text('body')
                print("="*80)
                print("PAGE TEXT (first 2000 chars)")
                print("="*80)
                print(page_text[:2000])
                
                # Check for applicant/contractor mentions
                print("\n" + "="*80)
                print("SEARCHING FOR APPLICANT/CONTRACTOR IN PAGE TEXT")
                print("="*80)
                if 'applicant' in page_text.lower() or 'contractor' in page_text.lower():
                    # Find lines containing these terms
                    lines = page_text.split('\n')
                    for line in lines:
                        if 'applicant' in line.lower() or 'contractor' in line.lower():
                            print(f"  Found: {line[:150]}")
                
                # Check for address/location mentions
                print("\n" + "="*80)
                print("SEARCHING FOR ADDRESS/LOCATION IN PAGE TEXT")
                print("="*80)
                if 'address' in page_text.lower() or 'location' in page_text.lower():
                    # Find lines containing these terms
                    lines = page_text.split('\n')
                    for line in lines:
                        if ('address' in line.lower() or 'location' in line.lower()) and 'email' not in line.lower():
                            print(f"  Found: {line[:150]}")
        
        await browser.close()


if __name__ == "__main__":
    asyncio.run(check_content())
