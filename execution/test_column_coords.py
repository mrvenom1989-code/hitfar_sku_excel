import pdfplumber
import re

def parse_pdf(pdf_path):
    all_products = []
    
    with pdfplumber.open(pdf_path) as pdf:
        for page_idx, page in enumerate(pdf.pages, 1):
            words = page.extract_words()
            
            # Find all words that are "Hitfar" followed by "SKU:"
            # Let's locate the bounding box of each "Hitfar SKU:" on this page
            sku_anchors = []
            for i, w in enumerate(words):
                if w['text'] == 'Hitfar' and i + 1 < len(words) and 'SKU' in words[i+1]['text']:
                    sku_anchors.append(w)
                elif 'Hitfar' in w['text'] and 'SKU' in w['text']:
                    sku_anchors.append(w)
                    
            # Also sort anchors by top y
            sku_anchors = sorted(sku_anchors, key=lambda x: x['top'])
            
            # For each anchor, determine its row bounding box
            # Top boundary: bottom of previous anchor + 5 (or top of table header for first item)
            # Bottom boundary: bottom of current anchor + 25 (or top of next anchor)
            for a_idx, anchor in enumerate(sku_anchors):
                # Find upper y bound
                if a_idx == 0:
                    # Look for table header
                    header_words = [w for w in words if w['text'] in ['Product', 'Price', 'Quantity'] and w['top'] < anchor['top']]
                    min_y = max(w['bottom'] for w in header_words) if header_words else 0
                else:
                    # Bottom of previous anchor's data (approx anchor['top'] - 15)
                    min_y = sku_anchors[a_idx - 1]['bottom'] + 5
                    
                # Find lower y bound
                if a_idx + 1 < len(sku_anchors):
                    max_y = sku_anchors[a_idx + 1]['top'] - 15
                else:
                    # Last item on page: look for subtotal/notes or bottom of words
                    subtotal_words = [w for w in words if 'Subtotal' in w['text'] or 'Total $' in w['text'] or 'Notes' in w['text'] or 'Page' in w['text']]
                    valid_sub = [w['top'] for w in subtotal_words if w['top'] > anchor['bottom']]
                    max_y = min(valid_sub) if valid_sub else page.height
                    
                # Words belonging to this item are within [min_y, max_y]
                # In particular, product name is at x <= 305 and min_y <= y <= anchor.bottom + 5
                item_words = [w for w in words if min_y <= w['top'] <= max(max_y, anchor['bottom'] + 15)]
                
                # Product name words (x <= 305 and above the "Hitfar SKU:" line)
                name_words = [w for w in item_words if w['x1'] <= 305 and w['bottom'] <= anchor['top'] + 2]
                name = " ".join([w['text'] for w in sorted(name_words, key=lambda x: (x['top'], x['x0']))]).strip()
                
                # SKU line words (around anchor.top +/- 5, x <= 305)
                sku_line_words = [w for w in item_words if w['x1'] <= 305 and abs(w['top'] - anchor['top']) < 8]
                sku_line_text = " ".join([w['text'] for w in sorted(sku_line_words, key=lambda x: (x['top'], x['x0']))])
                
                sku_m = re.search(r'Hitfar SKU:\s*([^\s|]+)', sku_line_text)
                hitfar_sku = sku_m.group(1) if sku_m else ""
                
                mpn_m = re.search(r'MPN:\s*([^\s]+)', sku_line_text)
                mpn = mpn_m.group(1) if mpn_m else ""
                
                # Quantity words (305 < x <= 355)
                qty_words = [w for w in item_words if 305 < w['x0'] and w['x1'] <= 355]
                qty_text = " ".join([w['text'] for w in sorted(qty_words, key=lambda x: (x['top'], x['x0']))])
                qty_m = re.search(r'(\d+)\s*each', qty_text)
                qty = int(qty_m.group(1)) if qty_m else None
                
                # Price words (355 < x <= 400)
                price_words = [w for w in item_words if 355 < w['x0'] and w['x1'] <= 405]
                price_text = " ".join([w['text'] for w in sorted(price_words, key=lambda x: (x['top'], x['x0']))])
                price_m = re.search(r'\$?(\d+\.\d{2})', price_text)
                cost = float(price_m.group(1)) if price_m else None
                
                all_products.append({
                    "page": page_idx,
                    "index_on_page": a_idx + 1,
                    "name": name,
                    "hitfar_sku": hitfar_sku,
                    "mpn": mpn,
                    "qty": qty,
                    "cost": cost,
                    "raw_sku_line": sku_line_text,
                    "raw_price": price_text,
                    "raw_qty": qty_text
                })
                
    return all_products

if __name__ == '__main__':
    prods = parse_pdf('hitfar_sku/order pdf.pdf')
    print(f"Total products extracted: {len(prods)}")
    
    missing_cost = [p for p in prods if p['cost'] is None]
    missing_sku = [p for p in prods if not p['hitfar_sku']]
    missing_name = [p for p in prods if not p['name']]
    missing_qty = [p for p in prods if p['qty'] is None]
    
    print(f"Missing cost: {len(missing_cost)}")
    print(f"Missing SKU: {len(missing_sku)}")
    print(f"Missing Name: {len(missing_name)}")
    print(f"Missing Qty: {len(missing_qty)}")
    
    for idx, p in enumerate(prods[:10]):
        print(f"[{idx+1}] SKU={p['hitfar_sku']} | MPN={p['mpn']} | Qty={p['qty']} | Cost=${p['cost']} | Name={p['name']}")
