import os
import sys
sys.path.append(os.path.abspath('.'))
import re
import time
import json
import pdfplumber
import openpyxl
from openpyxl.styles import Font
from playwright.sync_api import sync_playwright

def parse_pdf_orders(pdf_path):
    all_products = []
    
    with pdfplumber.open(pdf_path) as pdf:
        for page_idx, page in enumerate(pdf.pages, 1):
            words = page.extract_words()
            
            sku_anchors = []
            for i, w in enumerate(words):
                if w['text'] == 'Hitfar' and i + 1 < len(words) and 'SKU' in words[i+1]['text']:
                    sku_anchors.append(w)
                elif 'Hitfar' in w['text'] and 'SKU' in w['text']:
                    sku_anchors.append(w)
                    
            sku_anchors = sorted(sku_anchors, key=lambda x: x['top'])
            
            for a_idx, anchor in enumerate(sku_anchors):
                if a_idx == 0:
                    header_words = [w for w in words if w['text'] in ['Product', 'Price', 'Quantity'] and w['top'] < anchor['top']]
                    min_y = max(w['bottom'] for w in header_words) if header_words else 0
                else:
                    min_y = sku_anchors[a_idx - 1]['bottom'] + 5
                    
                if a_idx + 1 < len(sku_anchors):
                    max_y = sku_anchors[a_idx + 1]['top'] - 15
                else:
                    subtotal_words = [w for w in words if 'Subtotal' in w['text'] or 'Total $' in w['text'] or 'Notes' in w['text'] or 'Page' in w['text']]
                    valid_sub = [w['top'] for w in subtotal_words if w['top'] > anchor['bottom']]
                    max_y = min(valid_sub) if valid_sub else page.height
                    
                item_words = [w for w in words if min_y <= w['top'] <= max(max_y, anchor['bottom'] + 15)]
                
                name_words = [w for w in item_words if w['x1'] <= 305 and w['bottom'] <= anchor['top'] + 2]
                name = " ".join([w['text'] for w in sorted(name_words, key=lambda x: (x['top'], x['x0']))]).strip()
                
                sku_line_words = [w for w in item_words if w['x1'] <= 305 and abs(w['top'] - anchor['top']) < 8]
                sku_line_text = " ".join([w['text'] for w in sorted(sku_line_words, key=lambda x: (x['top'], x['x0']))])
                
                sku_m = re.search(r'Hitfar SKU:\s*([^\s|]+)', sku_line_text)
                hitfar_sku = sku_m.group(1) if sku_m else ""
                
                mpn_m = re.search(r'MPN:\s*([^\s]+)', sku_line_text)
                mpn = mpn_m.group(1) if mpn_m else ""
                
                qty_words = [w for w in item_words if 305 < w['x0'] and w['x1'] <= 355]
                qty_text = " ".join([w['text'] for w in sorted(qty_words, key=lambda x: (x['top'], x['x0']))])
                qty_m = re.search(r'(\d+)\s*each', qty_text)
                qty = int(qty_m.group(1)) if qty_m else None
                
                price_words = [w for w in item_words if 355 < w['x0'] and w['x1'] <= 405]
                price_text = " ".join([w['text'] for w in sorted(price_words, key=lambda x: (x['top'], x['x0']))])
                price_m = re.search(r'\$?(\d+\.\d{2})', price_text)
                cost = float(price_m.group(1)) if price_m else None
                
                shipped_words = [w for w in item_words if 460 < w['x0'] and w['x1'] <= 515]
                shipped_text = " ".join([w['text'] for w in sorted(shipped_words, key=lambda x: (x['top'], x['x0']))])
                shipped_m = re.search(r'(\d+)', shipped_text)
                shipped_qty = int(shipped_m.group(1)) if shipped_m else 0
                
                backorder_words = [w for w in item_words if 515 < w['x0']]
                backorder_text = " ".join([w['text'] for w in sorted(backorder_words, key=lambda x: (x['top'], x['x0']))])
                backorder_m = re.search(r'(\d+)', backorder_text)
                backorder_qty = int(backorder_m.group(1)) if backorder_m else 0
                
                # Determine brand / manufacturer
                mfr = "Other"
                n_upper = name.upper()
                if "HYPERGEAR" in n_upper:
                    mfr = "HyperGear"
                elif "HOUSE OF MARLEY" in n_upper or "MARLEY" in n_upper:
                    mfr = "House of Marley"
                elif "ZAGG" in n_upper:
                    mfr = "ZAGG"
                elif "GEAR4" in n_upper or "GEAR 4" in n_upper:
                    mfr = "Gear4"
                elif "SPECTRUM" in n_upper:
                    mfr = "SPECTRUM"
                elif "BLU ELEMENT" in n_upper:
                    mfr = "Blu Element"
                
                all_products.append({
                    "page": page_idx,
                    "name": name,
                    "hitfar_sku": hitfar_sku,
                    "mpn": mpn,
                    "ordered_qty": qty,
                    "cost": cost,
                    "shipped_qty": shipped_qty,
                    "backorder_qty": backorder_qty,
                    "manufacturer": mfr
                })
                
    return all_products

def scrape_hitfar_msrp_batch(skus_to_scrape, max_concurrency=4):
    print(f"\n--- Starting Hitfar MSRP scraping for {len(skus_to_scrape)} unique SKUs ---")
    sku_price_map = {}
    
    # Check cache file if exists
    cache_path = "hitfar_sku/.tmp/msrp_cache.json"
    if os.path.exists(cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                sku_price_map = json.load(f)
            print(f"Loaded {len(sku_price_map)} cached MSRP records.")
        except Exception as e:
            print(f"Could not load cache: {e}")
            
    missing_skus = [s for s in skus_to_scrape if s not in sku_price_map or sku_price_map[s] is None]
    print(f"SKUs needing scrape: {len(missing_skus)}")
    
    if not missing_skus:
        return sku_price_map
        
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
        )
        
        # Warm up session
        page = context.new_page()
        print("Connecting to hitfar.com session...")
        page.goto("https://www.hitfar.com", timeout=45000)
        time.sleep(2)
        page.close()
        
        # Create worker pages
        workers = [context.new_page() for _ in range(max_concurrency)]
        
        for idx in range(0, len(missing_skus), max_concurrency):
            batch = missing_skus[idx:idx + max_concurrency]
            print(f"Processing batch {idx+1}-{min(idx+len(batch), len(missing_skus))} / {len(missing_skus)}: {batch}")
            
            for w_idx, sku in enumerate(batch):
                w_page = workers[w_idx]
                url = f"https://www.hitfar.com/product/?search={sku}"
                try:
                    w_page.goto(url, timeout=25000)
                except Exception as e:
                    print(f"Error navigating {sku}: {e}")
            
            for w_idx, sku in enumerate(batch):
                w_page = workers[w_idx]
                try:
                    w_page.wait_for_selector(".product-item, .msrp__code, .no-products-found, .product-item__sku-value", timeout=6000)
                except Exception:
                    pass
                
                msrp_val = None
                try:
                    msrp_elem = w_page.query_selector(".msrp__code")
                    if msrp_elem:
                        t = msrp_elem.inner_text().strip()
                        m = re.search(r'\$?(\d+\.\d{2})', t)
                        if m:
                            msrp_val = float(m.group(1))
                    else:
                        content = w_page.content()
                        m = re.search(r'MSRP[:\s]*\$?(\d+\.\d{2})', content, re.I)
                        if m:
                            msrp_val = float(m.group(1))
                except Exception as e:
                    print(f"Extraction error for {sku}: {e}")
                    
                print(f"  [Scraped] {sku} -> MSRP: ${msrp_val}")
                sku_price_map[sku] = msrp_val
                
            # Periodically save cache
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(sku_price_map, f, indent=2)
                
        browser.close()
        
    return sku_price_map

def populate_excel(products, sku_price_map, output_path="hitfar_sku/order sku.xlsx"):
    print(f"\n--- Writing {len(products)} products to Excel: {output_path} ---")
    
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Sheet1"
    
    headers = [
        "Item Type",
        "Manufacturer",
        "UPC",
        "Supplier SKUs",
        "SKU",
        "Name",
        "Short Name",
        "Price",
        "Cost",
        "Active",
        "Allow Cost Override",
        "Location Scope",
        "Location"
    ]
    ws.append(headers)
    
    # Format header row
    header_font = Font(name="Calibri", size=11, bold=True)
    for col_idx in range(1, len(headers) + 1):
        cell = ws.cell(1, col_idx)
        cell.font = header_font
        
    for p in products:
        supplier_sku = f"Hitfar:{p['hitfar_sku']}"
        msrp = sku_price_map.get(p['hitfar_sku'])
        
        row_data = [
            "Accessories - Cases",          # Item Type
            p['manufacturer'],              # Manufacturer
            "-",                            # UPC
            supplier_sku,                   # Supplier SKUs (Col D)
            "-",                            # SKU (Col E)
            p['name'],                      # Name (Col F)
            "-",                            # Short Name (Col G)
            msrp if msrp is not None else "", # Price (MSRP) (Col H)
            p['cost'] if p['cost'] is not None else "", # Cost (Col I)
            1,                              # Active (Col J)
            1,                              # Allow Cost Override (Col K)
            "global",                       # Location Scope (Col L)
            ""                              # Location (Col M)
        ]
        ws.append(row_data)
        
    wb.save(output_path)
    print(f"Successfully saved Excel file with {len(products)} rows to {output_path}")

def run_pipeline():
    pdf_file = "hitfar_sku/order pdf.pdf"
    excel_file = "hitfar_sku/order sku.xlsx"
    
    # Step 1: Parse PDF
    products = parse_pdf_orders(pdf_file)
    print(f"Extracted {len(products)} products from PDF.")
    
    # Step 2: Unique SKUs
    unique_skus = list(dict.fromkeys([p['hitfar_sku'] for p in products if p['hitfar_sku']]))
    print(f"Unique SKUs to check: {len(unique_skus)}")
    
    # Step 3: Scrape MSRP from Hitfar
    sku_price_map = scrape_hitfar_msrp_batch(unique_skus, max_concurrency=6)
    
    # Step 4: Write to Excel
    populate_excel(products, sku_price_map, excel_file)
    
    # Verification summary
    found_prices = sum(1 for s in unique_skus if sku_price_map.get(s) is not None)
    print(f"\n================ SUMMARY ================")
    print(f"Total Products in Order: {len(products)}")
    print(f"Unique SKUs:             {len(unique_skus)}")
    print(f"MSRPs Found on Hitfar:   {found_prices} / {len(unique_skus)}")
    print(f"Excel File Updated:      {excel_file}")
    print(f"=========================================")

if __name__ == '__main__':
    run_pipeline()
