import pdfplumber
import re

with pdfplumber.open('hitfar_sku/order pdf.pdf') as pdf:
    for page_idx, page in enumerate(pdf.pages, 1):
        text = page.extract_text()
        # Find all occurrences of "each" or "$xx.xx"
        eaches = re.findall(r'\b\d+\s+each\b', text)
        prices = re.findall(r'\$\d+\.\d{2}', text)
        # remove summary prices on page 12 if any
        if page_idx == 12:
            prices = [p for p in prices if p not in ['$4,355.41', '$0.00', '$217.94', '$4,573.35', '$4355.41', '$217.94', '$4573.35']]
        sku_lines = [l for l in text.split('\n') if 'Hitfar SKU:' in l]
        print(f"Page {page_idx:2d}: {len(sku_lines)} SKU lines, {len(eaches)} 'each', {len(prices)} prices")
