from playwright.sync_api import sync_playwright
import time
import re

def test_skus(skus):
    results = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # Create a context with realistic headers
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        # Navigate to homepage first to establish session/cookies
        print("Visiting hitfar.com homepage...")
        page.goto("https://www.hitfar.com", timeout=45000)
        time.sleep(3)
        
        for sku in skus:
            url = f"https://www.hitfar.com/product/?search={sku}"
            print(f"\n[Query] SKU: {sku} -> {url}")
            try:
                page.goto(url, timeout=30000)
                # Wait for product-item or msrp__code
                page.wait_for_selector(".product-item, .msrp__code, .no-products-found, .product-item__sku-value", timeout=10000)
            except Exception as e:
                print(f"Wait timeout for {sku}: {e}")
                
            content = page.content()
            
            # Find msrp
            msrp_elem = page.query_selector(".msrp__code")
            msrp_val = None
            if msrp_elem:
                text = msrp_elem.inner_text().strip()
                m = re.search(r'\$?(\d+\.\d{2})', text)
                if m:
                    msrp_val = float(m.group(1))
            else:
                # Regex fallback on content
                m = re.search(r'MSRP[:\s]*\$?(\d+\.\d{2})', content, re.I)
                if m:
                    msrp_val = float(m.group(1))
                    
            sku_elem = page.query_selector(".product-item__sku-value")
            matched_sku = sku_elem.inner_text().strip() if sku_elem else None
            
            title_elem = page.query_selector(".product-item__title, h1.product-title, .product-item a[title]")
            matched_title = title_elem.inner_text().strip() if title_elem else (title_elem.get_attribute("title") if title_elem else None)
            
            print(f"==> RESULT: SKU={sku} | MSRP=${msrp_val} | Matched SKU={matched_sku} | Title={matched_title}")
            results[sku] = {
                "msrp": msrp_val,
                "matched_sku": matched_sku,
                "title": matched_title
            }
            
        browser.close()
    return results

if __name__ == '__main__':
    sample = ['15-11215', '15-11214', '15-14070', '15-14666', '15-14898']
    test_skus(sample)
