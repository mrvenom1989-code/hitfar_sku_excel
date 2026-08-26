import pdfplumber
import re

def parse_pdf_detailed(pdf_path):
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
                
                # Also extract Total Shipped and Backorder
                shipped_words = [w for w in item_words if 460 < w['x0'] and w['x1'] <= 515]
                shipped_text = " ".join([w['text'] for w in sorted(shipped_words, key=lambda x: (x['top'], x['x0']))])
                
                backorder_words = [w for w in item_words if 515 < w['x0']]
                backorder_text = " ".join([w['text'] for w in sorted(backorder_words, key=lambda x: (x['top'], x['x0']))])
                
                all_products.append({
                    "page": page_idx,
                    "name": name,
                    "hitfar_sku": hitfar_sku,
                    "mpn": mpn,
                    "qty": qty,
                    "cost": cost,
                    "shipped_text": shipped_text,
                    "backorder_text": backorder_text
                })
                
    return all_products

if __name__ == '__main__':
    prods = parse_pdf_detailed('hitfar_sku/order pdf.pdf')
    for idx, p in enumerate(prods):
        if p['cost'] == 5.99:
            print(f"P{p['page']} [{idx+1}] Qty={p['qty']} Cost={p['cost']} Shipped='{p['shipped_text']}' Backorder='{p['backorder_text']}' Name={p['name']}")
