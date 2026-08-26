from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    
    print("Navigating to https://hitfar.com...")
    page.goto("https://hitfar.com", timeout=60000)
    time.sleep(5)
    
    # Save homepage HTML
    with open("hitfar_sku/.tmp/homepage.html", "w", encoding="utf-8") as f:
        f.write(page.content())
    page.screenshot(path="hitfar_sku/.tmp/homepage.png")
    
    # Try searching via the UI search input
    search_input = page.query_selector("input[type='search'], input[name='q'], input[placeholder*='Search'], #search, .search-input")
    if search_input:
        print("Found search input! Typing 15-11215...")
        search_input.fill("15-11215")
        page.keyboard.press("Enter")
        time.sleep(5)
        page.screenshot(path="hitfar_sku/.tmp/search_result.png")
        with open("hitfar_sku/.tmp/search_result.html", "w", encoding="utf-8") as f:
            f.write(page.content())
        print("Search URL after enter:", page.url)
    else:
        print("No search input found by basic selector. Inspecting inputs...")
        inputs = page.query_selector_all("input")
        for inp in inputs:
            print("Input:", inp.get_attribute("name"), inp.get_attribute("id"), inp.get_attribute("placeholder"), inp.get_attribute("class"))
            
    browser.close()
