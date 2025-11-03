-- Types ENUM (idempotent)
DO $$ BEGIN
  CREATE TYPE type_mouvement AS ENUM ('ENTREE','SORTIE','TRANSFERT','INVENTAIRE');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- Table produits
CREATE TABLE IF NOT EXISTS produits (
  id SERIAL PRIMARY KEY,
  nom TEXT NOT NULL,
  categorie TEXT NOT NULL DEFAULT 'Autre',
  prix_achat NUMERIC(10,2),
  prix_vente NUMERIC(10,2),
  tva NUMERIC(5,2) DEFAULT 0,
  seuil_alerte NUMERIC(12,3) DEFAULT 0,
  actif BOOLEAN DEFAULT TRUE,
  stock_actuel NUMERIC(12,3) DEFAULT 0,
  created_at TIMESTAMP NOT NULL DEFAULT now(),
  updated_at TIMESTAMP NOT NULL DEFAULT now()
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

-- Catégories
CREATE TABLE IF NOT EXISTS categories (
  id SERIAL PRIMARY KEY,
  nom TEXT NOT NULL UNIQUE,
  description TEXT,
  created_at TIMESTAMP NOT NULL DEFAULT now(),
  updated_at TIMESTAMP NOT NULL DEFAULT now()
);

-- Clients
CREATE TABLE IF NOT EXISTS clients (
  id SERIAL PRIMARY KEY,
  nom TEXT NOT NULL,
  telephone TEXT,
  email TEXT,
  adresse TEXT,
  created_at TIMESTAMP NOT NULL DEFAULT now(),
  updated_at TIMESTAMP NOT NULL DEFAULT now()
);

-- Fournisseurs
CREATE TABLE IF NOT EXISTS fournisseurs (
  id SERIAL PRIMARY KEY,
  nom TEXT NOT NULL,
  telephone TEXT,
  email TEXT,
  adresse TEXT,
  created_at TIMESTAMP NOT NULL DEFAULT now(),
  updated_at TIMESTAMP NOT NULL DEFAULT now()
);

-- Commandes clients
CREATE TABLE IF NOT EXISTS commandes (
  id SERIAL PRIMARY KEY,
  numero TEXT NOT NULL UNIQUE,
  date_commande TIMESTAMP NOT NULL DEFAULT now(),
  client_id INT REFERENCES clients(id) ON DELETE SET NULL,
  statut TEXT NOT NULL DEFAULT 'Brouillon',
  total_ht NUMERIC(12,2) DEFAULT 0,
  total_ttc NUMERIC(12,2) DEFAULT 0,
  created_at TIMESTAMP NOT NULL DEFAULT now(),
  updated_at TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS commandes_lignes (
  id SERIAL PRIMARY KEY,
  commande_id INT NOT NULL REFERENCES commandes(id) ON DELETE CASCADE,
  produit_id INT REFERENCES produits(id) ON DELETE SET NULL,
  quantite NUMERIC(12,3) NOT NULL CHECK (quantite > 0),
  prix_unitaire NUMERIC(10,2) NOT NULL CHECK (prix_unitaire >= 0),
  tva NUMERIC(5,2) DEFAULT 0 CHECK (tva >= 0)
);

-- Approvisionnements fournisseurs
CREATE TABLE IF NOT EXISTS approvisionnements (
  id SERIAL PRIMARY KEY,
  numero TEXT NOT NULL UNIQUE,
  date_appro TIMESTAMP NOT NULL DEFAULT now(),
  fournisseur_id INT REFERENCES fournisseurs(id) ON DELETE SET NULL,
  statut TEXT NOT NULL DEFAULT 'Reçu',
  total_ht NUMERIC(12,2) DEFAULT 0,
  created_at TIMESTAMP NOT NULL DEFAULT now(),
  updated_at TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS approvisionnements_lignes (
  id SERIAL PRIMARY KEY,
  approvisionnement_id INT NOT NULL REFERENCES approvisionnements(id) ON DELETE CASCADE,
  produit_id INT REFERENCES produits(id) ON DELETE SET NULL,
  quantite NUMERIC(12,3) NOT NULL CHECK (quantite > 0),
  prix_unitaire NUMERIC(10,2) NOT NULL CHECK (prix_unitaire >= 0)
);

-- Mouvements
CREATE TABLE IF NOT EXISTS mouvements_stock (
  id SERIAL PRIMARY KEY,
  produit_id INT NOT NULL REFERENCES produits(id) ON DELETE CASCADE,
  type type_mouvement NOT NULL,
  quantite NUMERIC(12,3) NOT NULL,
  source TEXT,
  date_mvt TIMESTAMP NOT NULL DEFAULT now()
);
