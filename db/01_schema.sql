-- Types ENUM (idempotent)
DO $$ BEGIN
  CREATE TYPE type_mouvement AS ENUM ('ENTREE','SORTIE','TRANSFERT','INVENTAIRE');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- Table produits
CREATE TABLE IF NOT EXISTS produits (
  id SERIAL PRIMARY KEY,
  nom TEXT NOT NULL,
  prix_achat NUMERIC(10,2),
  prix_vente NUMERIC(10,2),
  tva NUMERIC(5,2) DEFAULT 0,
  seuil_alerte NUMERIC(12,3) DEFAULT 0,
  actif BOOLEAN DEFAULT TRUE
);

-- Codes-barres (1 produit -> N codes)
CREATE TABLE IF NOT EXISTS produits_barcodes (
  id SERIAL PRIMARY KEY,
  produit_id INT NOT NULL REFERENCES produits(id) ON DELETE CASCADE,
  code TEXT NOT NULL,
  symbologie TEXT,            -- EAN-13, UPC-A, EAN-8, CODE128…
  pays_iso2 CHAR(2),
  is_principal BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP NOT NULL DEFAULT now(),
  UNIQUE(code)
);
CREATE INDEX IF NOT EXISTS idx_barcode_produit ON produits_barcodes(produit_id);
CREATE INDEX IF NOT EXISTS idx_barcode_code    ON produits_barcodes(code);

-- Mouvements
CREATE TABLE IF NOT EXISTS mouvements_stock (
  id SERIAL PRIMARY KEY,
  produit_id INT NOT NULL REFERENCES produits(id) ON DELETE CASCADE,
  type type_mouvement NOT NULL,
  quantite NUMERIC(12,3) NOT NULL,
  source TEXT,
  date_mvt TIMESTAMP NOT NULL DEFAULT now()
);
