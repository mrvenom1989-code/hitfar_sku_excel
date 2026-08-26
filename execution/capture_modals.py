import os
from playwright.sync_api import sync_playwright

output_dir = "hitfar_sku/.tmp/screenshots"
os.makedirs(output_dir, exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1400, "height": 900})
    page.goto("http://127.0.0.1:5000")
    page.wait_for_selector("#btnOpenUploadModal")
    
    # 1. Upload Modal
    page.click("#btnOpenUploadModal")
    page.wait_for_selector("#uploadModal:not(.hidden)")
    page.screenshot(path=os.path.join(output_dir, "upload_modal.png"))
    page.click("#btnCloseUploadModal")
    page.wait_for_timeout(300)
    
    # 2. Edit Modal
    page.evaluate("openEditModal('test-id', 'iPhone 15/14/13 ZAGG/GEAR4 Graphene Everest Snap Case', 'Hitfar:15-11644', 7.99, '')")
    page.wait_for_selector("#editModal:not(.hidden)")
    page.screenshot(path=os.path.join(output_dir, "edit_modal.png"))
    page.click("#btnCloseEditModal")
    page.wait_for_timeout(300)
    
    # 3. Missing MSRP filter
    page.click(".switch-label")
    page.wait_for_timeout(500)
    page.screenshot(path=os.path.join(output_dir, "missing_msrp_view.png"))
    
    browser.close()
    print("Modals & filter screenshots captured!")
