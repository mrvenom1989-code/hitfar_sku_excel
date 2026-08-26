import pdfplumber
import re

with pdfplumber.open('hitfar_sku/order pdf.pdf') as pdf:
    for page_idx, page in enumerate(pdf.pages, 1):
        text = page.extract_text()
        lines = text.split('\n')
        # Check for any line with 15- or 118- or MPN or SKU
        for line_no, line in enumerate(lines):
            if ('MPN' in line or 'SKU' in line) and 'Hitfar SKU:' not in line:
                print(f"Page {page_idx} Line {line_no}: {line}")
            # Check for any item name that might not have SKU
            if 'each' in line:
                # check previous lines
                prev_context = " /// ".join(lines[max(0, line_no-3):line_no+1])
                # print if no Hitfar SKU in context
                if 'Hitfar' not in prev_context:
                    print(f"Page {page_idx} 'each' without Hitfar: {prev_context}")
