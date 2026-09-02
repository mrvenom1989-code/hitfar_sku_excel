import os
import sys
import tempfile
from flask import Flask, render_template, request, jsonify, send_file
from werkzeug.utils import secure_filename

# Ensure hitfar_sku directory is in Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from config import SECRET_KEY
from execution.db_service import (
    get_existing_supplier_skus,
    insert_catalog_items,
    query_catalog,
    update_item_price,
    get_catalog_stats,
    is_supabase_available
)
from execution.process_hitfar_order import parse_pdf_orders, scrape_hitfar_msrp_batch
from execution.excel_exporter import generate_excel_bytes

app = Flask(
    __name__,
    static_folder=os.path.join(current_dir, "static"),
    static_url_path="/static",
    template_folder=os.path.join(current_dir, "templates")
)
app.secret_key = SECRET_KEY
app.config['MAX_CONTENT_LENGTH'] = 32 * 1024 * 1024  # 32MB max upload

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/stats", methods=["GET"])
def api_stats():
    try:
        stats = get_catalog_stats()
        return jsonify({"success": True, "stats": stats})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/catalog", methods=["GET"])
def api_catalog():
    try:
        search = request.args.get("search", "").strip() or None
        date_start = request.args.get("date_start", "").strip() or None
        date_end = request.args.get("date_end", "").strip() or None
        manufacturer = request.args.get("manufacturer", "").strip() or None
        missing_msrp = request.args.get("missing_msrp", "").lower() == "true"
        limit = int(request.args.get("limit", 1000))
        offset = int(request.args.get("offset", 0))

        result = query_catalog(
            search=search,
            created_date_start=date_start,
            created_date_end=date_end,
            manufacturer=manufacturer,
            missing_msrp_only=missing_msrp,
            limit=limit,
            offset=offset
        )
        return jsonify({"success": True, "data": result["items"], "total": result["total"]})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/upload-pdf", methods=["POST"])
def api_upload_pdf():
    if "file" not in request.files:
        return jsonify({"success": False, "error": "No file uploaded."}), 400
        
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"success": False, "error": "Empty filename."}), 400
        
    if not file.filename.lower().endswith(".pdf"):
        return jsonify({"success": False, "error": "Only PDF invoice files are supported."}), 400
        
    temp_dir = tempfile.mkdtemp()
    temp_pdf_path = os.path.join(temp_dir, secure_filename(file.filename))
    file.save(temp_pdf_path)
    
    try:
        # Step 1: Parse PDF
        parsed_products = parse_pdf_orders(temp_pdf_path)
        if not parsed_products:
            return jsonify({"success": False, "error": "No products could be extracted from PDF."}), 400
            
        # Step 2: Compare against database to identify new vs existing
        existing_skus = get_existing_supplier_skus()
        
        new_items = []
        existing_items = []
        
        for p in parsed_products:
            supplier_sku = f"Hitfar:{p['hitfar_sku']}"
            if supplier_sku in existing_skus:
                existing_items.append(p)
            else:
                new_items.append(p)
                
        # Step 3: Scrape MSRP only for newly discovered SKUs
        unique_new_skus = list(dict.fromkeys([p['hitfar_sku'] for p in new_items if p['hitfar_sku']]))
        scraped_price_map = {}
        missing_msrp_skus = []
        
        if unique_new_skus:
            try:
                scraped_price_map = scrape_hitfar_msrp_batch(unique_new_skus, max_concurrency=4)
            except Exception as scrape_err:
                print(f"[API UPLOAD WARNING] Scraper error: {scrape_err}")
                scraped_price_map = {}
                
            for sku in unique_new_skus:
                price = scraped_price_map.get(sku)
                if price is None:
                    missing_msrp_skus.append(sku)
                    
            # Populate MSRP into new items
            for it in new_items:
                it["price"] = scraped_price_map.get(it["hitfar_sku"])
                
        # Step 4: Always persist new items into catalog
        if new_items:
            insert_catalog_items(new_items)
            
        # Update existing items with latest cost & order data
        if existing_items:
            try:
                insert_catalog_items(existing_items)
            except Exception as sync_err:
                print(f"[API UPLOAD] Existing items sync note: {sync_err}")
            
        return jsonify({
            "success": True,
            "filename": file.filename,
            "total_items_in_pdf": len(parsed_products),
            "new_items_count": len(new_items),
            "existing_items_count": len(existing_items),
            "msrps_scraped_count": len(unique_new_skus) - len(missing_msrp_skus),
            "missing_msrp_skus": missing_msrp_skus,
            "new_items": new_items,
            "existing_items": existing_items
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": f"Failed to process PDF: {str(e)}"}), 500
    finally:
        if os.path.exists(temp_pdf_path):
            try:
                os.remove(temp_pdf_path)
            except Exception:
                pass

@app.route("/api/update-price", methods=["POST"])
def api_update_price():
    try:
        data = request.get_json() or {}
        item_id = data.get("id")
        price = data.get("price")
        
        if not item_id or price is None:
            return jsonify({"success": False, "error": "Missing item id or price."}), 400
            
        new_price = float(price)
        success = update_item_price(item_id, new_price)
        if success:
            return jsonify({"success": True, "message": "Price updated successfully."})
        else:
            return jsonify({"success": False, "error": "Item not found or update failed."}), 404
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/rescrape-sku", methods=["POST"])
def api_rescrape_sku():
    try:
        data = request.get_json() or {}
        item_id = data.get("id")
        hitfar_sku = data.get("hitfar_sku")
        
        if not hitfar_sku:
            return jsonify({"success": False, "error": "Missing SKU."}), 400
            
        # Scrape single SKU
        price_map = scrape_hitfar_msrp_batch([hitfar_sku], max_concurrency=1)
        msrp = price_map.get(hitfar_sku)
        
        if msrp is not None and item_id:
            update_item_price(item_id, msrp)
            
        return jsonify({
            "success": True,
            "hitfar_sku": hitfar_sku,
            "price": msrp,
            "found": msrp is not None
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/sync-msrps", methods=["POST"])
def api_sync_msrps():
    try:
        data = request.get_json() or {}
        force_all = data.get("all", False)
        
        if force_all:
            result = query_catalog(limit=5000)
            items = result.get("items", [])
        else:
            result = query_catalog(missing_msrp_only=True, limit=5000)
            items = result.get("items", [])
            
        if not items:
            return jsonify({
                "success": True,
                "message": "All items in the catalog already have valid retail MSRPs.",
                "updated_count": 0,
                "total_checked": 0
            })
            
        skus_to_scrape = list(dict.fromkeys([it["hitfar_sku"] for it in items if it.get("hitfar_sku")]))
        price_map = scrape_hitfar_msrp_batch(skus_to_scrape)
        
        updated_count = 0
        for it in items:
            h_sku = it.get("hitfar_sku")
            new_price = price_map.get(h_sku)
            if new_price is not None and new_price != it.get("price"):
                success = update_item_price(it["id"], new_price)
                if success:
                    updated_count += 1
                    
        return jsonify({
            "success": True,
            "message": f"Sync complete: Successfully updated {updated_count} item(s) with live MSRP.",
            "updated_count": updated_count,
            "total_checked": len(items),
            "unresolved_count": len(skus_to_scrape) - sum(1 for s in skus_to_scrape if price_map.get(s) is not None)
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/export", methods=["GET"])
def api_export():
    try:
        search = request.args.get("search", "").strip() or None
        date_start = request.args.get("date_start", "").strip() or None
        date_end = request.args.get("date_end", "").strip() or None
        manufacturer = request.args.get("manufacturer", "").strip() or None
        missing_msrp = request.args.get("missing_msrp", "").lower() == "true"
        
        result = query_catalog(
            search=search,
            created_date_start=date_start,
            created_date_end=date_end,
            manufacturer=manufacturer,
            missing_msrp_only=missing_msrp,
            limit=5000,
            offset=0
        )
        
        excel_stream = generate_excel_bytes(result["items"])
        return send_file(
            excel_stream,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment=True,
            download_name="order_sku_export.xlsx"
        )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
