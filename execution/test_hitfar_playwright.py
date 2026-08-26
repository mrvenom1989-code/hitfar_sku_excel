from playwright.sync_api import sync_playwright
import time
import re

def test_hitfar_search(skus):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        # Navigate to hitfar
        print("Navigating to hitfar.com...")
        page.goto("https://hitfar.com", timeout=60000)
        time.sleep(3)
        print("Page title:", page.title())
        
        results = {}
        for sku in skus:
            # Let's search using the search URL or search input
            search_url = f"https://hitfar.com/search?q={sku}"
            print(f"\nSearching for SKU: {sku} -> {search_url}")
            page.goto(search_url, timeout=30000)
            page.wait_for_load_state("networkidle")
            time.sleep(2)
            
            # Check content
            content = page.content()
            
            # Look for MSRP in page content
            # Common patterns: MSRP: $xx.xx, <span class="...price...">
            msrp_matches = re.findall(r'MSRP[:\s]*\$?(\d+\.\d{2})', content, re.IGNORECASE)
            print(f"MSRP regex matches on search page: {msrp_matches}")
            
            # Check if there are product links or cards
            product_links = page.query_selector_all("a[href*='/product/'], a[href*='/p/'], .product-item, .product-card")
            print(f"Product links/cards found: {len(product_links)}")
            
            # Print text snippet around MSRP or price
            lines = page.inner_text("body").split('\n')
            relevant_lines = [l.strip() for l in lines if any(k in l.lower() for k in ['msrp', 'price', '$', sku.lower()])]
            print("Relevant lines preview:")
            for l in relevant_lines[:8]:
                print("  ", l)
                
            results[sku] = {
                "msrp_matches": msrp_matches,
                "relevant_lines": relevant_lines[:5]
            }
            
        browser.close()
        return results

if __name__ == '__main__':
    test_skus = ['15-11215', '15-11214', '15-14070', '15-14666']
    res = test_hitfar_search(test_skus)
