import sys
sys.path.append('.')
from hitfar_sku.execution.test_column_coords import parse_pdf

prods = parse_pdf('hitfar_sku/order pdf.pdf')
total_calc = sum(p['qty'] * p['cost'] for p in prods if p['qty'] is not None and p['cost'] is not None)
print(f"Calculated Subtotal: ${total_calc:.2f}")
print(f"Expected Subtotal:   $4355.41")
print(f"Difference:          ${total_calc - 4355.41:.2f}")
