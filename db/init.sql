
-- Minimal schema (only if original missing)
CREATE TABLE IF NOT EXISTS public.produits (
  id SERIAL PRIMARY KEY,
  nom TEXT NOT NULL,
  prix_vente NUMERIC(12,2) DEFAULT 0,
  tva NUMERIC(5,2) DEFAULT 0,
  actif BOOLEAN DEFAULT TRUE
);
CREATE TABLE IF NOT EXISTS public.produits_barcodes (
  id SERIAL PRIMARY KEY,
  produit_id INT REFERENCES public.produits(id) ON DELETE CASCADE,
  code TEXT UNIQUE
);
CREATE TABLE IF NOT EXISTS public.mouvements_stock (
  id SERIAL PRIMARY KEY,
  produit_id INT REFERENCES public.produits(id) ON DELETE CASCADE,
  type TEXT NOT NULL,
  quantite NUMERIC(12,3) NOT NULL,
  source TEXT,
  created_at TIMESTAMP DEFAULT NOW()
);


-- === Added by upgrade (indexes & search_path) ===
DO $$ BEGIN
  EXECUTE 'ALTER ROLE ' || current_user || ' IN DATABASE ' || current_database() || ' SET search_path TO public';
EXCEPTION WHEN others THEN
  NULL;
END $$;

CREATE INDEX IF NOT EXISTS idx_produits_nom_ci ON public.produits (LOWER(nom));
CREATE INDEX IF NOT EXISTS idx_barcodes_code_ci ON public.produits_barcodes (LOWER(code));
