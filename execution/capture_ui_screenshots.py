import os
import time
from playwright.sync_api import sync_playwright

output_dir = "hitfar_sku/.tmp/screenshots"
os.makedirs(output_dir, exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1400, "height": 900})
    
    print("1. Loading dashboard...")
    page.goto("http://127.0.0.1:5000", timeout=15000)
    page.wait_for_timeout(2000)
    page.screenshot(path=os.path.join(output_dir, "dashboard.png"), full_page=True)
    print("Captured dashboard.png")
    
    # 2. Test Missing MSRP Filter
    print("2. Clicking Missing MSRP toggle...")
    page.click("#chkMissingMsrp")
    page.wait_for_timeout(1000)
    page.screenshot(path=os.path.join(output_dir, "missing_msrp_filter.png"))
    print("Captured missing_msrp_filter.png")
    page.click("#chkMissingMsrp") # Uncheck
    page.wait_for_timeout(500)
    
    # 3. Test Search
    print("3. Searching for 'iPhone 17'...")
    page.fill("#searchInput", "iPhone 17")
    page.wait_for_timeout(1000)
    page.screenshot(path=os.path.join(output_dir, "search_iphone17.png"))
    print("Captured search_iphone17.png")
    page.fill("#searchInput", "")
    page.wait_for_timeout(500)
    
    # 4. Open Upload Modal
    print("4. Opening Upload Modal...")
    page.click("#btnOpenUploadModal")
    page.wait_for_timeout(500)
    page.screenshot(path=os.path.join(output_dir, "upload_modal.png"))
    print("Captured upload_modal.png")
    page.click("#btnCloseUploadModal")
    page.wait_for_timeout(500)
    
    # 5. Open Edit Modal on first item
    print("5. Opening Edit Modal...")
    page.evaluate("openEditModal('test-id', 'HyperGear 4 ft. 120cm USB-A to USB-C Cable', 'Hitfar:15-11215', 4.99, 14.99)")
    page.wait_for_timeout(500)
    page.screenshot(path=os.path.join(output_dir, "edit_modal.png"))
    print("Captured edit_modal.png")
    
    browser.close()
    print("All UI screenshots captured successfully!")
