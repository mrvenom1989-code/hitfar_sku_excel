-- Hitfar SKU Catalog Schema for Supabase

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Hitfar Catalog Table
CREATE TABLE IF NOT EXISTS public.hitfar_catalog (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    item_type TEXT DEFAULT 'Accessories - Cases',
    manufacturer TEXT NOT NULL,
    upc TEXT DEFAULT '-',
    supplier_sku TEXT UNIQUE NOT NULL,
    hitfar_sku TEXT NOT NULL,
    mpn TEXT DEFAULT '',
    sku TEXT DEFAULT '-',
    name TEXT NOT NULL,
    short_name TEXT DEFAULT '-',
    price NUMERIC(10, 2), -- MSRP from Hitfar
    cost NUMERIC(10, 2),  -- Unit purchase cost from invoice
    active INTEGER DEFAULT 1,
    allow_cost_override INTEGER DEFAULT 1,
    location_scope TEXT DEFAULT 'global',
    location TEXT DEFAULT '',
    created_date DATE NOT NULL DEFAULT CURRENT_DATE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    last_order_po TEXT,
    last_order_date DATE,
    ordered_qty INTEGER DEFAULT 0,
    shipped_qty INTEGER DEFAULT 0
);

-- Index definitions for high-performance querying and filtering
CREATE INDEX IF NOT EXISTS idx_hitfar_supplier_sku ON public.hitfar_catalog(supplier_sku);
CREATE INDEX IF NOT EXISTS idx_hitfar_hitfar_sku ON public.hitfar_catalog(hitfar_sku);
CREATE INDEX IF NOT EXISTS idx_hitfar_created_date ON public.hitfar_catalog(created_date);
CREATE INDEX IF NOT EXISTS idx_hitfar_manufacturer ON public.hitfar_catalog(manufacturer);
CREATE INDEX IF NOT EXISTS idx_hitfar_price ON public.hitfar_catalog(price);

-- Row Level Security (RLS)
ALTER TABLE public.hitfar_catalog ENABLE ROW LEVEL SECURITY;

-- Allow read access for authenticated & service role
CREATE POLICY "Allow all access to hitfar_catalog for service role"
ON public.hitfar_catalog
FOR ALL
USING (true)
WITH CHECK (true);
