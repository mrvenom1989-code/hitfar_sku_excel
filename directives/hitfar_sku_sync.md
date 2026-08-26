# Directive: Hitfar SKU Order Processor & Catalog Sync

## Goal
Extract order invoice data from Hitfar PDF purchase orders (`hitfar_sku/order pdf.pdf`), scrape the corresponding retail MSRPs from `www.hitfar.com` for each Hitfar SKU, and populate an inventory/catalog import spreadsheet (`hitfar_sku/order sku.xlsx`).

## Inputs
- **Order Invoice PDF**: `hitfar_sku/order pdf.pdf`
- **Target Excel File**: `hitfar_sku/order sku.xlsx`

## Field Mapping Specifications

| Excel Column | Column Header | Value Source / Logic | Example Value |
| :--- | :--- | :--- | :--- |
| **A** | `Item Type` | Default category | `Accessories - Cases` |
| **B** | `Manufacturer` | Derived brand from product title (`HyperGear`, `ZAGG`, `House of Marley`, `SPECTRUM`, `Gear4`, `Blu Element`) | `HyperGear` |
| **C** | `UPC` | Placeholder | `-` |
| **D** | `Supplier SKUs` | Hitfar SKU prefix + code from PDF | `Hitfar:15-11215` |
| **E** | `SKU` | Placeholder | `-` |
| **F** | `Name` | Full product name from PDF description | `HyperGear 4 ft. 120cm USB-A to USB-C Braided Charge and Sync Cable - White` |
| **G** | `Short Name` | Placeholder | `-` |
| **H** | `Price` | MSRP scraped dynamically from `hitfar.com/product/?search=<SKU>` | `14.99` |
| **I** | `Cost` | Purchase cost per unit from PDF invoice | `4.99` |
| **J** | `Active` | Active flag | `1` |
| **K** | `Allow Cost Override` | Cost override flag | `1` |
| **L** | `Location Scope` | Scope | `global` |
| **M** | `Location` | Blank | `""` |

## Execution Tool
- Script: `hitfar_sku/execution/process_hitfar_order.py`
- Command: `python hitfar_sku/execution/process_hitfar_order.py`

## Architecture & Caching
- **Playwright Concurrency**: Scrapes Hitfar product pages concurrently using headless browser instances.
- **Cache Persistence**: Cached MSRP lookups are saved in `hitfar_sku/.tmp/msrp_cache.json` to prevent unnecessary re-scraping.
- **PDF Layout Extraction**: Uses `pdfplumber` bounding-box coordinates to accurately capture multi-line product titles and aligned prices.
