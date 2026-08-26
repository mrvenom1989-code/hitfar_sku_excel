import pdfplumber
import re
import json

def parse_hitfar_pdf(pdf_path):
    all_items = []
    
    with pdfplumber.open(pdf_path) as pdf:
        for page_idx, page in enumerate(pdf.pages):
            text = page.extract_text()
            lines = [l.strip() for l in text.split('\n') if l.strip()]
            
            # Find table items
            # In each page, let's inspect the flow of items
            i = 0
            while i < len(lines):
                line = lines[i]
                if 'Hitfar SKU:' in line:
                    # Previous lines (up to previous item or header) make up the product name
                    name_parts = []
                    k = i - 1
                    while k >= 0:
                        prev = lines[k]
                        if 'Hitfar SKU:' in prev or 'Product Quantity Price' in prev or 'Backorder' in prev or 'ITEMS ORDERED' in prev or '217 total records' in prev or 'Notes ' in prev or 'Subtotal ' in prev or 'Discount ' in prev or 'Tax ' in prev or 'Total $' in prev:
                            break
                        # Check if prev looks like a quantity/price/tracking line from previous item
                        if re.search(r'\b(each|\d+ each|\$\d+\.\d{2}|1Z[A-Z0-9]+)\b', prev):
                            break
                        name_parts.insert(0, prev)
                        k -= 1
                    
                    product_name = " ".join(name_parts).strip()
                    
                    sku_match = re.search(r'Hitfar SKU:\s*([^\s|]+)', line)
                    hitfar_sku = sku_match.group(1) if sku_match else ""
                    
                    mpn_match = re.search(r'MPN:\s*([^\s]+)', line)
                    mpn = mpn_match.group(1) if mpn_match else ""
                    
                    # Look ahead for price & quantity
                    # Example line ahead might be: "5 each $4.99"
                    combined_ahead = " ".join(lines[i:min(i+6, len(lines))])
                    
                    price_match = re.search(r'\$(\d+\.\d{2})', combined_ahead)
                    unit_cost = float(price_match.group(1)) if price_match else None
                    
                    qty_match = re.search(r'(\d+)\s+each', combined_ahead)
                    ordered_qty = int(qty_match.group(1)) if qty_match else None
                    
                    all_items.append({
                        "page": page_idx + 1,
                        "name": product_name,
                        "hitfar_sku": hitfar_sku,
                        "mpn": mpn,
                        "ordered_qty": ordered_qty,
                        "unit_cost": unit_cost,
                        "raw_sku_line": line
                    })
                i += 1
                
    return all_items

if __name__ == '__main__':
    items = parse_hitfar_pdf('hitfar_sku/order pdf.pdf')
    print(f"Extracted {len(items)} items:")
    for idx, item in enumerate(items[:15]):
        print(f"[{idx+1}] SKU: {item['hitfar_sku']} | Cost: ${item['unit_cost']} | Qty: {item['ordered_qty']} | Name: {item['name']}")
    
    print("\nCheck last 5 items:")
    for idx, item in enumerate(items[-5:]):
        print(f"[{len(items)-5+idx+1}] SKU: {item['hitfar_sku']} | Cost: ${item['unit_cost']} | Qty: {item['ordered_qty']} | Name: {item['name']}")
