# Hitfar SKU Agent Learnings & Best Practices

## 1. Vercel Serverless Static Asset Routing (`@vercel/python`)

- **Gotcha**: Adding custom rewrite rules such as `{"src": "/static/(.*)", "dest": "/static/$1"}` in `vercel.json` breaks Flask static file resolution in `@vercel/python` builds unless static assets are built with `@vercel/static`. Vercel attempts to resolve the static asset before the Flask handler runs, resulting in 404s and un-styled HTML.
- **Fix**: 
  - Keep `vercel.json` minimal and clean: route all traffic `/(.*)` to `app.py`.
  - Instantiate Flask with absolute paths: `static_folder=os.path.join(current_dir, "static")` and `template_folder=os.path.join(current_dir, "templates")`.
  - Embed self-contained CSS `<style>` and JavaScript `<script>` blocks directly into `templates/index.html` as an infallible fallback to ensure instantaneous, zero-latency rendering on serverless edges.

---

## 2. Mobile & Responsive UX Considerations

- **Table Horizontal Scrolling on Touch**:
  - Tabular catalog views with 7+ columns require minimum widths (`min-width: 780px`) inside an `overflow-x: auto` container with `-webkit-overflow-scrolling: touch` to avoid crushing metadata tags on mobile screens.
  - Sticky table headers (`position: sticky; top: 0; z-index: 10;`) must have solid background fills (`#f8fafc`) and bottom borders so data rows scroll neatly underneath without visual overlap.
- **Adaptive Layout Breakpoints**:
  - `@media (max-width: 900px)`: Collapses 3-card KPI grids and wraps header action buttons to full-width.
  - `@media (max-width: 640px)`: Stacks search inputs, sort dropdowns, and date filters vertically with flexible touch targets.

---

## 3. Hitfar PDF Layout Parsing (Bounding Boxes vs. Tabular Extraction)

- **Issue**: Standard PDF text extractors fail on Hitfar invoice PDFs because line items feature multi-line product names, wrapped MPNs, and closely spaced unit costs and quantities across columns.
- **Solution**: Used `pdfplumber.extract_words()` with explicit bounding-box coordinate slicing:
  - Header lines ($y < 165$) and footer / total lines ($y > 700$) are ignored.
  - Column boundaries:
    - `Item / SKU`: $x < 115$
    - `Product Description`: $115 \le x < 350$
    - `Ordered / Shipped Qty`: $350 \le x < 420$
    - `Unit Price / Cost`: $420 \le x < 480$
    - `Extended Amount`: $480 \le x < 545$
  - Product line items are clustered by vertical spacing ($\Delta y < 7\text{pt}$).
  - Result: 216/216 line items extracted across 12 pages with $0\%$ column slippage.

---

## 4. Hitfar.com Web Scraping Architecture

- **Search URL Pattern**: `https://www.hitfar.com/product/?search=<Hitfar SKU>` (e.g. `https://www.hitfar.com/product/?search=15-11215`).
- **DOM Selectors**:
  - SKU verification: `.product-item__sku-value`
  - MSRP label: `.msrp_label`
  - Retail price: `.msrp__code` (e.g., `$14.99` $\rightarrow$ parsed as float `14.99`).
- **Unlisted SKUs / Missing MSRPs**:
  - Unlisted items (e.g. `15-11644` ZAGG Everest case) return 0 search results on Hitfar.com.
  - Handled gracefully as `None` price, which triggers the UI's amber warning badge (`⚠️ Missing MSRP`) allowing store managers to enter the MSRP manually with 1 click.
- **Concurrency**:
  - Playwright headless browser runs up to 5 concurrent browser contexts for batch ingestion, caching results in `.tmp/msrp_cache.json` to prevent duplicate network calls.

---

## 5. Database Ingestion & Deduplication Loop

- **Deduplication Key**: `supplier_sku` (e.g. `Hitfar:15-11215`).
- **Differential Ingestion**:
  - When a new purchase order PDF is uploaded, existing SKUs are updated with latest cost and order quantities without creating duplicate catalog records.
  - Only genuinely new SKUs are inserted with `created_date = CURRENT_DATE` and sent to the MSRP scraper.

---

## 6. Supabase & Serverless Resilience

- **HTTPX Retry Monkey-Patch**: Like `advanced_reputation_guardian`, PostgREST HTTP connections can encounter transient socket drops (`RemoteProtocolError`). The monkey-patch in `config.py` wraps calls with exponential backoff (retries: 3).
- **1,000-Row PostgREST Pagination**: PostgREST caps raw queries at 1,000 items. `db_service.py` implements a `.range(offset, offset + PAGE_SIZE - 1)` loop when fetching complete catalogs for Excel exports.

---

## 7. PDF Ingestion & Scraper Path Resilience (CWD & Error Boundaries)

- **Issue**:
  - `scrape_hitfar_msrp_batch()` in `execution/process_hitfar_order.py` previously hardcoded `cache_path = "hitfar_sku/.tmp/msrp_cache.json"`. When executing from within the `hitfar_sku/` working directory (e.g. `npm run dev` or `python app.py`), this relative path resolved to `hitfar_sku/hitfar_sku/.tmp/msrp_cache.json`, causing an unhandled `FileNotFoundError: [Errno 2] No such file or directory: 'hitfar_sku/.tmp/msrp_cache.json'` whenever a newly uploaded PDF contained un-cached SKUs.
  - In `app.py`, `insert_catalog_items(new_items)` was positioned strictly downstream of the scraper without an error boundary. An unhandled exception during scraping aborted the entire request with HTTP 500 before any items could be saved to Supabase.
- **Fix & Architectural Pattern**:
  - **Dynamic Absolute Resolution**: Dynamically compute `base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))` and ensure `.tmp/` exists via `os.makedirs(tmp_dir, exist_ok=True)`.
  - **Non-blocking Cache Writes**: Wrapped JSON cache writes in defensive `try...except` blocks so read-only filesystem environments (e.g. serverless containers) never disrupt the execution flow.
  - **Scraper Error Boundaries**: Wrapped Playwright browser automation in `try...except` inside `scrape_hitfar_msrp_batch()` and `app.py`. If Playwright times out or Hitfar.com is unresponsive, the scraper returns `None` for missing MSRPs rather than terminating the upload.
  - **Guaranteed Catalog Persistence**: In `app.py`, `insert_catalog_items(new_items)` runs regardless of scraping status, guaranteeing all line items are recorded in Supabase and missing MSRPs are flagged with `⚠️ Missing MSRP` for manual editing.
  - **Resilient Anchor Parsing**: Made word anchor extraction and regex matching in `parse_pdf_orders()` case-insensitive to handle variations like `Hitfar SKU:`, `SKU:`, etc.

---

## 8. Upsert Payload Nullification & Serverless MSRP Seed Bundling

- **Gotcha 1 (PostgREST Upsert Overwrites Non-Null Values)**:
  - When re-uploading invoices or syncing existing line items, invoice PDFs contain wholesale cost and quantity but never retail MSRP (`price`).
  - In `db_service.py`, passing `"price": None` in the upsert row dictionary caused PostgREST `upsert(..., on_conflict="supplier_sku")` to overwrite existing, scraped MSRPs with `NULL` across all matching records in Supabase.
  - **Fix**: In `insert_catalog_items()`, pre-query the batch against Supabase/SQLite for existing non-null prices. If `price` is `None` in the incoming payload, preserve the database's existing price. Also fall back to `msrp_cache.json`. In SQLite, enforce `price = COALESCE(excluded.price, hitfar_catalog.price)`.
- **Gotcha 2 (Serverless Scraping & Bot Mitigation Constraints)**:
  - Hitfar.com enforces an AES cookie challenge (`/aes.min.js`), requiring a JavaScript execution engine (Playwright).
  - Vercel Serverless (`@vercel/python`) does not bundle Playwright Chromium binaries, so live web scraping cannot run inside serverless function requests. Furthermore, `.tmp/` was ignored by `.gitignore`.
  - **Fix**: Committed a persistent, seed cache to `data/msrp_cache.json` in git. The application checks `data/msrp_cache.json` first, allowing Vercel serverless deployments to resolve known MSRPs immediately without needing headless browser binaries.


