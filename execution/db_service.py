import os
import sys
import sqlite3
import datetime
from typing import List, Dict, Any, Optional

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from config import supabase

LOCAL_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "hitfar_catalog.db")

def _init_local_db():
    conn = sqlite3.connect(LOCAL_DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS hitfar_catalog (
            id TEXT PRIMARY KEY,
            item_type TEXT DEFAULT 'Accessories - Cases',
            manufacturer TEXT NOT NULL,
            upc TEXT DEFAULT '-',
            supplier_sku TEXT UNIQUE NOT NULL,
            hitfar_sku TEXT NOT NULL,
            mpn TEXT DEFAULT '',
            sku TEXT DEFAULT '-',
            name TEXT NOT NULL,
            short_name TEXT DEFAULT '-',
            price REAL,
            cost REAL,
            active INTEGER DEFAULT 1,
            allow_cost_override INTEGER DEFAULT 1,
            location_scope TEXT DEFAULT 'global',
            location TEXT DEFAULT '',
            created_date TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            last_order_po TEXT,
            last_order_date TEXT,
            ordered_qty INTEGER DEFAULT 0,
            shipped_qty INTEGER DEFAULT 0
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_supplier_sku ON hitfar_catalog(supplier_sku)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_created_date ON hitfar_catalog(created_date)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_manufacturer ON hitfar_catalog(manufacturer)")
    conn.commit()
    conn.close()

def is_supabase_available() -> bool:
    if supabase is None:
        return False
    try:
        res = supabase.table("hitfar_catalog").select("id").limit(1).execute()
        return True
    except Exception as e:
        return False

def get_existing_supplier_skus() -> set:
    """Returns a set of all supplier_sku strings currently stored in the database."""
    if is_supabase_available():
        all_skus = set()
        page_size = 1000
        start = 0
        while True:
            res = supabase.table("hitfar_catalog").select("supplier_sku").range(start, start + page_size - 1).execute()
            if not res.data:
                break
            for row in res.data:
                if row.get("supplier_sku"):
                    all_skus.add(row["supplier_sku"])
            if len(res.data) < page_size:
                break
            start += page_size
        return all_skus
    else:
        _init_local_db()
        conn = sqlite3.connect(LOCAL_DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT supplier_sku FROM hitfar_catalog")
        rows = cur.fetchall()
        conn.close()
        return {r[0] for r in rows if r[0]}

def insert_catalog_items(items: List[Dict[str, Any]]) -> int:
    """Inserts new catalog items into database."""
    if not items:
        return 0
        
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    today_str = datetime.date.today().isoformat()
    
    # Normalize items
    formatted_items = []
    import uuid
    for it in items:
        supplier_sku = it.get("supplier_sku") or f"Hitfar:{it.get('hitfar_sku', '')}"
        hitfar_sku = it.get("hitfar_sku") or supplier_sku.replace("Hitfar:", "")
        created_date = it.get("created_date") or today_str
        
        formatted_items.append({
            "id": str(it.get("id") or uuid.uuid4()),
            "item_type": it.get("item_type", "Accessories - Cases"),
            "manufacturer": it.get("manufacturer", "HyperGear"),
            "upc": it.get("upc", "-"),
            "supplier_sku": supplier_sku,
            "hitfar_sku": hitfar_sku,
            "mpn": it.get("mpn", ""),
            "sku": it.get("sku", "-"),
            "name": it.get("name", ""),
            "short_name": it.get("short_name", "-"),
            "price": it.get("price"),
            "cost": it.get("cost"),
            "active": it.get("active", 1),
            "allow_cost_override": it.get("allow_cost_override", 1),
            "location_scope": it.get("location_scope", "global"),
            "location": it.get("location", ""),
            "created_date": created_date,
            "created_at": it.get("created_at", now_iso),
            "updated_at": now_iso,
            "last_order_po": it.get("last_order_po", ""),
            "last_order_date": it.get("last_order_date", today_str),
            "ordered_qty": it.get("ordered_qty", 0),
            "shipped_qty": it.get("shipped_qty", 0)
        })
        
    if is_supabase_available():
        # Batch insert in chunks of 500
        inserted_count = 0
        chunk_size = 500
        for i in range(0, len(formatted_items), chunk_size):
            chunk = formatted_items[i:i + chunk_size]
            res = supabase.table("hitfar_catalog").upsert(chunk, on_conflict="supplier_sku").execute()
            inserted_count += len(chunk)
        return inserted_count
    else:
        _init_local_db()
        conn = sqlite3.connect(LOCAL_DB_PATH)
        cur = conn.cursor()
        cur.executemany("""
            INSERT INTO hitfar_catalog (
                id, item_type, manufacturer, upc, supplier_sku, hitfar_sku, mpn, sku,
                name, short_name, price, cost, active, allow_cost_override, location_scope,
                location, created_date, created_at, updated_at, last_order_po, last_order_date,
                ordered_qty, shipped_qty
            ) VALUES (
                :id, :item_type, :manufacturer, :upc, :supplier_sku, :hitfar_sku, :mpn, :sku,
                :name, :short_name, :price, :cost, :active, :allow_cost_override, :location_scope,
                :location, :created_date, :created_at, :updated_at, :last_order_po, :last_order_date,
                :ordered_qty, :shipped_qty
            )
            ON CONFLICT(supplier_sku) DO UPDATE SET
                price = excluded.price,
                cost = excluded.cost,
                updated_at = excluded.updated_at,
                last_order_po = excluded.last_order_po,
                ordered_qty = excluded.ordered_qty,
                shipped_qty = excluded.shipped_qty
        """, formatted_items)
        conn.commit()
        conn.close()
        return len(formatted_items)

def query_catalog(
    search: Optional[str] = None,
    created_date_start: Optional[str] = None,
    created_date_end: Optional[str] = None,
    manufacturer: Optional[str] = None,
    missing_msrp_only: bool = False,
    limit: int = 500,
    offset: int = 0
) -> Dict[str, Any]:
    """Queries catalog items with multi-filtering and pagination."""
    if is_supabase_available():
        query = supabase.table("hitfar_catalog").select("*", count="exact")
        
        if search:
            s = f"%{search}%"
            query = query.or_(f"name.ilike.{s},supplier_sku.ilike.{s},hitfar_sku.ilike.{s},mpn.ilike.{s}")
            
        if created_date_start:
            query = query.gte("created_date", created_date_start)
        if created_date_end:
            query = query.lte("created_date", created_date_end)
            
        if manufacturer and manufacturer != "All":
            query = query.eq("manufacturer", manufacturer)
            
        if missing_msrp_only:
            query = query.or_("price.is.null,price.eq.0")
            
        query = query.order("created_at", desc=True).range(offset, offset + limit - 1)
        res = query.execute()
        
        return {
            "items": res.data,
            "total": res.count or len(res.data)
        }
    else:
        _init_local_db()
        conn = sqlite3.connect(LOCAL_DB_PATH)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        
        sql = "SELECT * FROM hitfar_catalog WHERE 1=1"
        count_sql = "SELECT COUNT(*) FROM hitfar_catalog WHERE 1=1"
        params = []
        
        if search:
            sql += " AND (name LIKE ? OR supplier_sku LIKE ? OR hitfar_sku LIKE ? OR mpn LIKE ?)"
            count_sql += " AND (name LIKE ? OR supplier_sku LIKE ? OR hitfar_sku LIKE ? OR mpn LIKE ?)"
            s_param = f"%{search}%"
            params.extend([s_param, s_param, s_param, s_param])
            
        if created_date_start:
            sql += " AND created_date >= ?"
            count_sql += " AND created_date >= ?"
            params.append(created_date_start)
            
        if created_date_end:
            sql += " AND created_date <= ?"
            count_sql += " AND created_date <= ?"
            params.append(created_date_end)
            
        if manufacturer and manufacturer != "All":
            sql += " AND manufacturer = ?"
            count_sql += " AND manufacturer = ?"
            params.append(manufacturer)
            
        if missing_msrp_only:
            sql += " AND (price IS NULL OR price = 0)"
            count_sql += " AND (price IS NULL OR price = 0)"
            
        cur.execute(count_sql, params)
        total_count = cur.fetchone()[0]
        
        sql += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        cur.execute(sql, params + [limit, offset])
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        
        return {
            "items": rows,
            "total": total_count
        }

def update_item_price(item_id: str, new_price: float) -> bool:
    """Updates the MSRP price of a specific catalog item."""
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    if is_supabase_available():
        res = supabase.table("hitfar_catalog").update({
            "price": new_price,
            "updated_at": now_iso
        }).eq("id", item_id).execute()
        return bool(res.data)
    else:
        _init_local_db()
        conn = sqlite3.connect(LOCAL_DB_PATH)
        cur = conn.cursor()
        cur.execute("UPDATE hitfar_catalog SET price = ?, updated_at = ? WHERE id = ?", (new_price, now_iso, item_id))
        conn.commit()
        updated = cur.rowcount > 0
        conn.close()
        return updated

def get_catalog_stats() -> Dict[str, Any]:
    """Retrieves high-level catalog statistics for dashboard KPI cards."""
    today_str = datetime.date.today().isoformat()
    
    if is_supabase_available():
        total_res = supabase.table("hitfar_catalog").select("id", count="exact").execute()
        today_res = supabase.table("hitfar_catalog").select("id", count="exact").eq("created_date", today_str).execute()
        missing_res = supabase.table("hitfar_catalog").select("id", count="exact").or_("price.is.null,price.eq.0").execute()
        
        # Unique manufacturers
        all_mfrs = supabase.table("hitfar_catalog").select("manufacturer").execute()
        unique_mfrs = sorted(list(set(r["manufacturer"] for r in all_mfrs.data if r.get("manufacturer"))))
        
        return {
            "total_items": total_res.count or 0,
            "added_today": today_res.count or 0,
            "missing_msrp": missing_res.count or 0,
            "manufacturers": unique_mfrs,
            "database_backend": "Supabase"
        }
    else:
        _init_local_db()
        conn = sqlite3.connect(LOCAL_DB_PATH)
        cur = conn.cursor()
        
        cur.execute("SELECT COUNT(*) FROM hitfar_catalog")
        total_items = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(*) FROM hitfar_catalog WHERE created_date = ?", (today_str,))
        added_today = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(*) FROM hitfar_catalog WHERE price IS NULL OR price = 0")
        missing_msrp = cur.fetchone()[0]
        
        cur.execute("SELECT DISTINCT manufacturer FROM hitfar_catalog WHERE manufacturer IS NOT NULL ORDER BY manufacturer")
        unique_mfrs = [r[0] for r in cur.fetchall()]
        
        conn.close()
        return {
            "total_items": total_items,
            "added_today": added_today,
            "missing_msrp": missing_msrp,
            "manufacturers": unique_mfrs,
            "database_backend": "SQLite (Local)"
        }
