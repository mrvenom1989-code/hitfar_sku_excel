import sys, os
sys.path.append(os.path.abspath('.'))

import json
import openpyxl
from openpyxl.styles import Font
from hitfar_sku.execution.process_hitfar_order import parse_pdf_orders

products = parse_pdf_orders('hitfar_sku/order pdf.pdf')
print(f"Extracted {len(products)} products from PDF.")

with open('hitfar_sku/.tmp/msrp_cache.json', 'r', encoding='utf-8') as f:
    msrp_map = json.load(f)

print(f"Loaded {len(msrp_map)} MSRP records.")

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

header_font = Font(name="Calibri", size=11, bold=True)
for col_idx in range(1, len(headers) + 1):
    cell = ws.cell(1, col_idx)
    cell.font = header_font

for p in products:
    supplier_sku = f"Hitfar:{p['hitfar_sku']}"
    msrp = msrp_map.get(p['hitfar_sku'])
    
    row_data = [
        "Accessories - Cases",          # Item Type (Col A)
        p['manufacturer'],              # Manufacturer (Col B)
        "-",                            # UPC (Col C)
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

out_file = "hitfar_sku/order sku.xlsx"
wb.save(out_file)
print(f"Successfully saved {len(products)} product rows to {out_file}")
