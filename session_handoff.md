# Hitfar SKU Session Handoff

**Project**: Hitfar SKU Manager & Ingestion Portal  
**Repository**: [https://github.com/mrvenom1989-code/hitfar_sku_excel](https://github.com/mrvenom1989-code/hitfar_sku_excel)  
**Database**: Supabase `public.hitfar_catalog` on `https://lcqkwuoghxdierkzscpy.supabase.co`  
**Date**: August 27, 2026

---

## 1. Project Overview & Objective

The **Hitfar SKU** portal is an automated ingestion and catalog synchronization system for Mobile Klinik / Reputation Guardian. It ingests Hitfar purchase order invoices (`.pdf`), extracts line items (Supplier SKUs, product names, quantities, wholesale costs), scrapes retail MSRPs dynamically from [hitfar.com](https://www.hitfar.com), deduplicates against the Supabase database, flags missing MSRPs for manual entry, and exports standardized 13-column catalog spreadsheets conforming to `order sku.xlsx`.

---

## 2. System Architecture & Components

### 3-Layer Architecture Structure:
- **Layer 1 (Directives)**:
  - `hitfar_sku/directives/hitfar_sku_sync.md`: SOP detailing data dictionary, mapping logic, and scraping rules.
- **Layer 2 (Orchestration & REST API)**:
  - `hitfar_sku/app.py`: Flask backend serving frontend routes and REST endpoints (`/api/stats`, `/api/catalog`, `/api/upload-pdf`, `/api/update-price`, `/api/rescrape-sku`, `/api/export`).
- **Layer 3 (Deterministic Execution Tools)**:
  - `hitfar_sku/execution/process_hitfar_order.py`: PDF layout coordinate extractor (`pdfplumber`) & concurrent Playwright Hitfar MSRP scraper.
  - `hitfar_sku/execution/db_service.py`: Supabase database service with 1,000-row PostgREST pagination loop, HTTPX retry wrapper, and deduplication logic.
  - `hitfar_sku/execution/excel_exporter.py`: Generates styled 13-column `order sku.xlsx` spreadsheets.
  - `hitfar_sku/execution/seed_catalog.py`: Seeds initial catalog data into Supabase.
  - `hitfar_sku/execution/test_api.py`: Automated end-to-end API test suite.

### Frontend UI (`templates/index.html`, `static/css/style.css`, `static/js/app.js`):
- **Theme**: Clean light theme matching the Reputation Guardian color system (`#f8fafc` background, `#ffffff` cards, `#D71920` crimson red accent bar & buttons).
- **KPI Row (3 Cards)**: Total SKUs in Catalog (216), Added Today (216), Missing MSRP (1).
- **Filter Toolbar**: Substring search, sorting dropdown preset, date range quick-pills (`All Dates`, `Today`, `Last 7 Days`, `Last 30 Days`, `Custom Date`), brand pills (`Gear4`, `House of Marley`, `HyperGear`, `SPECTRUM`, `ZAGG`), and `Show Missing MSRP Only` toggle.
- **Scrollable Catalog Table**: Fixed-height container (`max-height: 560px`) with `position: sticky` headers and clickable column sort indicators (`▲▼`).
- **Modals**: Drag-and-drop PDF upload with ingestion report summary, and inline / modal MSRP price editor.

---

## 3. Database Schema (`public.hitfar_catalog`)

The table is deployed on Supabase:
- `id` (UUID, Primary Key)
- `item_type` (TEXT, default: 'Accessories - Cases')
- `manufacturer` (TEXT)
- `upc` (TEXT, default: '-')
- `supplier_sku` (TEXT, UNIQUE, format: `Hitfar:<Hitfar SKU>`)
- `hitfar_sku` (TEXT, raw SKU number e.g. `15-11215`)
- `mpn` (TEXT, manufacturer part number)
- `sku` (TEXT, default: '-')
- `name` (TEXT, product title)
- `short_name` (TEXT, default: '-')
- `price` (NUMERIC, MSRP retail price scraped from Hitfar.com)
- `cost` (NUMERIC, wholesale purchase cost from invoice)
- `active` (INTEGER, default: 1)
- `allow_cost_override` (INTEGER, default: 1)
- `location_scope` (TEXT, default: 'global')
- `location` (TEXT)
- `created_date` (DATE, default: CURRENT_DATE)
- `created_at` / `updated_at` (TIMESTAMPTZ)
- `last_order_po` (TEXT)
- `last_order_date` (DATE)
- `ordered_qty` / `shipped_qty` (INTEGER)

---

## 4. How to Run & Verify

### Local Development:
```bash
cd hitfar_sku
npm run dev
# OR: python app.py
# OR: .\run_app.bat
```
App is served on `http://localhost:5000`.

### Running Automated Test Suite:
```bash
python hitfar_sku/execution/test_api.py
```

### Vercel Deployment:
`hitfar_sku/vercel.json` is configured for deployment with `@vercel/python` builder. Supabase environment variables (`SUPABASE_URL`, `SUPABASE_KEY`) are identical to `advanced_reputation_guardian`.
