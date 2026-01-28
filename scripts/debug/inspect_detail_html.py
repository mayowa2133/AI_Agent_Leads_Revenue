"""Inspect actual HTML structure of detail pages to create better selectors."""

from __future__ import annotations

import asyncio
from playwright.async_api import async_playwright
from src.signal_engine.scrapers.accela_scraper import create_accela_scraper


async def inspect_html():
    """Inspect HTML structure of a detail page."""
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
                print("FULL PAGE HTML (first 5000 chars)")
                print("="*80)
                html = await page.content()
                print(html[:5000])
                
                print("\n" + "="*80)
                print("SEARCHING FOR APPLICANT/CONTRACTOR")
                print("="*80)
                
                # Get all elements containing "applicant" or "contractor"
                page_text = await page.evaluate("() => document.body.innerText")
                if "applicant" in page_text.lower() or "contractor" in page_text.lower():
                    # Find the section
                    applicant_section = await page.evaluate("""
                        () => {
                            const body = document.body;
                            const walker = document.createTreeWalker(body, NodeFilter.SHOW_TEXT);
                            let node;
                            let context = null;
                            
                            while (node = walker.nextNode()) {
                                const text = node.textContent.toLowerCase();
                                if (text.includes('applicant') || text.includes('contractor')) {
                                    // Get parent element
                                    let parent = node.parentElement;
                                    for (let i = 0; i < 5 && parent; i++) {
                                        if (parent.tagName === 'TR' || parent.tagName === 'DIV' || parent.tagName === 'TD') {
                                            context = {
                                                tag: parent.tagName,
                                                html: parent.innerHTML.substring(0, 500),
                                                text: parent.innerText.substring(0, 200)
                                            };
                                            break;
                                        }
                                        parent = parent.parentElement;
                                    }
                                    if (context) break;
                                }
                            }
                            return context;
                        }
                    """)
                    if applicant_section:
                        print(f"Found applicant section:")
                        print(f"  Tag: {applicant_section.get('tag')}")
                        print(f"  Text: {applicant_section.get('text')}")
                        print(f"  HTML: {applicant_section.get('html')[:300]}")
                
                print("\n" + "="*80)
                print("SEARCHING FOR ADDRESS/LOCATION")
                print("="*80)
                
                # Get all elements containing "address" or "location"
                if "address" in page_text.lower() or "location" in page_text.lower():
                    address_section = await page.evaluate("""
                        () => {
                            const body = document.body;
                            const walker = document.createTreeWalker(body, NodeFilter.SHOW_TEXT);
                            let node;
                            let context = null;
                            
                            while (node = walker.nextNode()) {
                                const text = node.textContent.toLowerCase();
                                if ((text.includes('address') || text.includes('location')) && !text.includes('email')) {
                                    // Get parent element
                                    let parent = node.parentElement;
                                    for (let i = 0; i < 5 && parent; i++) {
                                        if (parent.tagName === 'TR' || parent.tagName === 'DIV' || parent.tagName === 'TD') {
                                            context = {
                                                tag: parent.tagName,
                                                html: parent.innerHTML.substring(0, 500),
                                                text: parent.innerText.substring(0, 200)
                                            };
                                            break;
                                        }
                                        parent = parent.parentElement;
                                    }
                                    if (context) break;
                                }
                            }
                            return context;
                        }
                    """)
                    if address_section:
                        print(f"Found address section:")
                        print(f"  Tag: {address_section.get('tag')}")
                        print(f"  Text: {address_section.get('text')}")
                        print(f"  HTML: {address_section.get('html')[:300]}")
        
        await browser.close()


if __name__ == "__main__":
    asyncio.run(inspect_html())
