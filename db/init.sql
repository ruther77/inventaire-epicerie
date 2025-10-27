-- 1. TYPES ENUM (Idempotents)
-- Assure l'existence des types avant la création des tables.
DO $$ BEGIN
    CREATE TYPE type_mouvement AS ENUM ('ENTREE', 'SORTIE', 'TRANSFERT', 'INVENTAIRE');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    -- Mise à jour pour une meilleure catégorisation si nécessaire, sinon la liste originale est conservée.
    CREATE TYPE type_cat AS ENUM ('Epicerie sucree', 'Epicerie salee', 'Alcool', 'Autre', 'Afrique', 'Boissons', 'Hygiene');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

--------------------------------------------------------------------------------
-- 2. TABLES (avec Contraintes d'Intégrité)
--------------------------------------------------------------------------------

-- Table produits (Mise à jour)
CREATE TABLE IF NOT EXISTS produits (
    id SERIAL PRIMARY KEY,
    nom TEXT NOT NULL,
    categorie type_cat DEFAULT 'Autre',
    -- Ajout de contraintes CHECK pour garantir des valeurs non-négatives
    prix_achat NUMERIC(10,2) CHECK (prix_achat >= 0),
    prix_vente NUMERIC(10,2) CHECK (prix_vente >= 0),
    tva NUMERIC(5,2) DEFAULT 0 CHECK (tva >= 0),
    seuil_alerte NUMERIC(12,3) DEFAULT 0 CHECK (seuil_alerte >= 0),
    actif BOOLEAN DEFAULT TRUE,
    -- NOUVEAU: Stock Actuel matérialisé
    stock_actuel NUMERIC(12,3) DEFAULT 0 CHECK (stock_actuel >= 0), 
    -- Ajout de dates de création/mise à jour
    created_at TIMESTAMP NOT NULL DEFAULT now(),
    updated_at TIMESTAMP NOT NULL DEFAULT now()
);
-- ... (Le reste de vos tables: mouvements_stock, produits_barcodes, etc.)
-- Codes-barres (1 produit -> N codes)
CREATE TABLE IF NOT EXISTS produits_barcodes (
    id SERIAL PRIMARY KEY,
    produit_id INT NOT NULL REFERENCES produits(id) ON DELETE CASCADE,
    code TEXT NOT NULL,
    symbologie TEXT,            -- EAN-13, UPC-A, EAN-8, CODE128…
    pays_iso2 CHAR(2),
    is_principal BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT now()
);

-- Mouvements
CREATE TABLE IF NOT EXISTS mouvements_stock (
    id SERIAL PRIMARY KEY,
    produit_id INT NOT NULL REFERENCES produits(id) ON DELETE CASCADE,
    type type_mouvement NOT NULL,
    -- La quantité est toujours positive (ex: une 'SORTIE' a une quantite positive)
    quantite NUMERIC(12,3) NOT NULL CHECK (quantite > 0),
    source TEXT,                -- Ex: Nom du fournisseur, Numéro de commande, Nom de l'utilisateur
    date_mvt TIMESTAMP NOT NULL DEFAULT now(),
    created_at TIMESTAMP NOT NULL DEFAULT now()
);

-- 3. FONCTION DE MISE À JOUR DU STOCK (Trigger)
-- =================================================================
CREATE OR REPLACE FUNCTION update_stock_actuel()
RETURNS TRIGGER AS $$
BEGIN
    -- Mettre à jour le stock dans la table produits
    UPDATE produits
    SET stock_actuel = stock_actuel + CASE
        WHEN NEW.type = 'ENTREE' THEN NEW.quantite
        WHEN NEW.type = 'SORTIE' THEN -NEW.quantite
        -- Ajoutez ici d'autres types si nécessaire (ex: INVENTAIRE, TRANSFERT)
        ELSE 0
    END
    WHERE id = NEW.produit_id;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;


-- 4. TRIGGER
-- =================================================================
-- S'exécute APRÈS chaque INSERTION dans mouvements_stock
CREATE OR REPLACE TRIGGER trg_update_stock_actuel
AFTER INSERT ON mouvements_stock
FOR EACH ROW
EXECUTE FUNCTION update_stock_actuel();


-- 5. NETTOYAGE DES ANCIENNES VUES (Optionnel)
-- =================================================================
-- La vue v_stock_courant n'est plus utile, remplacez-la ou supprimez-la.
-- La vue v_stock_produits doit être réécrite pour utiliser 'stock_actuel'.
CREATE OR REPLACE VIEW v_stock_produits AS
SELECT 
    p.id, 
    p.nom, 
    p.categorie,
    p.prix_vente,
    p.tva,
    p.seuil_alerte,
    p.stock_actuel AS quantite_stock -- Utilise la nouvelle colonne O(1)
FROM produits p
WHERE p.actif = TRUE;

-- Mise à jour de la vue v_alertes_rupture pour utiliser la colonne O(1)
CREATE OR REPLACE VIEW v_alertes_rupture AS
SELECT
    p.id, p.nom, p.categorie, p.stock_actuel as stock, p.seuil_alerte
FROM produits p
WHERE p.stock_actuel <= COALESCE(p.seuil_alerte, 0)
AND p.actif = TRUE
ORDER BY p.stock_actuel ASC;
--------------------------------------------------------------------------------
-- 4. INDEXES & CONTRAINTES UNIQUES
--------------------------------------------------------------------------------

-- Configuration du search_path (maintenue pour compatibilité)
DO $$ BEGIN
    EXECUTE 'ALTER ROLE ' || current_user || ' IN DATABASE ' || current_database() || ' SET search_path TO public';
EXCEPTION WHEN others THEN
    NULL;
END $$;

-- Rendre le nom du produit unique, non sensible à la casse (Case-Insensitive Unique Index)
-- UTILE pour l'import (cf. products_loader.py)
CREATE UNIQUE INDEX IF NOT EXISTS uix_produits_nom_ci ON public.produits (LOWER(nom));

-- Rendre le code-barres unique, non sensible à la casse
CREATE UNIQUE INDEX IF NOT EXISTS uix_barcodes_code_ci ON public.produits_barcodes (LOWER(code));

-- Index pour les recherches fréquentes
CREATE INDEX IF NOT EXISTS idx_barcode_produit ON produits_barcodes(produit_id);
CREATE INDEX IF NOT EXISTS idx_mouvements_produit ON mouvements_stock(produit_id);
CREATE INDEX IF NOT EXISTS idx_mouvements_date ON mouvements_stock(date_mvt);

--------------------------------------------------------------------------------
-- 5. VUES COHÉRENTES ET FONCTIONNELLES
--------------------------------------------------------------------------------

-- VUE DU STOCK COURANT (Méthode 1: Solde Net basé sur l'historique)
CREATE OR REPLACE VIEW v_stock_courant AS
SELECT
    p.id,
    p.nom,
    p.categorie,
    p.prix_achat,
    p.prix_vente,
    p.tva,
    p.seuil_alerte,
    p.actif,
    -- Logique de calcul du solde
    COALESCE(SUM(
        CASE
            WHEN m.type IN ('ENTREE', 'INVENTAIRE', 'TRANSFERT') THEN m.quantite -- NOTE: voir explication ci-dessous
            WHEN m.type = 'SORTIE' THEN -m.quantite
            ELSE 0
        END
    ), 0) AS stock
FROM produits p
LEFT JOIN mouvements_stock m ON m.produit_id = p.id
GROUP BY
    p.id, p.nom, p.categorie, p.prix_achat, p.prix_vente, p.tva, p.seuil_alerte, p.actif
ORDER BY p.nom;

/*
EXPLICATION DU TYPE INVENTAIRE DANS v_stock_courant:
- Si un INVENTAIRE est un 'réglage' qui s'ajoute (ou se soustrait), il doit être traité comme ENTREE ou SORTIE.
- Si un INVENTAIRE (ou un mouvement dit d' 'AJUSTEMENT') est utilisé, il est souvent préférable de le considérer comme une ENTREE.
- Dans le modèle simple (stock net), tout INVENTAIRE est une ENTREE. Un ajustement à la baisse se fait par une SORTIE (type = 'SORTIE', source='Ajustement Inventaire'). Un ajustement à la hausse par une ENTREE (type = 'ENTREE', source='Ajustement Inventaire').
- Ici, on considère 'INVENTAIRE' comme un type d'ENTRÉE.
*/

-- Produits + codes agrégés (maintenu et enrichi)
CREATE OR REPLACE VIEW v_produits_codes AS
SELECT
    p.id, p.nom, p.categorie,
    p.prix_achat, p.prix_vente, p.tva, p.actif,
    COALESCE(string_agg(pb.code, ', ' ORDER BY pb.is_principal DESC, pb.code), '') AS codes
FROM produits p
LEFT JOIN produits_barcodes pb ON pb.produit_id = p.id
GROUP BY p.id, p.nom, p.categorie, p.prix_achat, p.prix_vente, p.tva, p.actif
ORDER BY p.nom;

-- Valorisation du stock (utilise v_stock_courant)
CREATE OR REPLACE VIEW v_valorisation_stock AS
SELECT
    s.id, s.nom, s.categorie, s.stock,
    s.prix_achat,
    -- Utilisation de s.prix_achat qui provient déjà de la vue mère
    ROUND(s.stock * COALESCE(s.prix_achat, 0), 2) AS valeur_achat
FROM v_stock_courant s
WHERE s.stock > 0
ORDER BY valeur_achat DESC;

-- Top ventes 30 jours (maintenu)
CREATE OR REPLACE VIEW v_top_ventes_30j AS
SELECT p.id, p.nom,
    SUM(CASE WHEN m.type='SORTIE' THEN m.quantite ELSE 0 END) AS qte_sorties_30j
FROM produits p
LEFT JOIN mouvements_stock m
    ON m.produit_id = p.id
    AND m.date_mvt >= now() - INTERVAL '30 days'
GROUP BY p.id, p.nom
ORDER BY qte_sorties_30j DESC NULLS LAST;

-- Rotation 30 jours (maintenu)
CREATE OR REPLACE VIEW v_rotation_30j AS
SELECT p.id, p.nom,
    SUM(CASE WHEN m.type='ENTREE' THEN m.quantite ELSE 0 END) AS entrees_30j,
    SUM(CASE WHEN m.type='SORTIE' THEN m.quantite ELSE 0 END) AS sorties_30j
FROM produits p
LEFT JOIN mouvements_stock m
    ON m.produit_id = p.id
    AND m.date_mvt >= now() - INTERVAL '30 days'
GROUP BY p.id, p.nom
ORDER BY sorties_30j DESC NULLS LAST;

-- Anomalies : stock négatif (utilise v_stock_courant)
CREATE OR REPLACE VIEW v_inventaire_negatif AS
SELECT * FROM v_stock_courant WHERE stock < 0 ORDER BY stock ASC;

-- Produits sans code-barres (maintenu)
CREATE OR REPLACE VIEW v_produits_sans_barcode AS
SELECT p.*
FROM produits p
LEFT JOIN produits_barcodes pb ON pb.produit_id = p.id
WHERE pb.id IS NULL
ORDER BY p.nom;

-- Alertes de rupture (utilise v_stock_courant)
CREATE OR REPLACE VIEW v_alertes_rupture AS
SELECT
    s.id, s.nom, s.categorie, (s.stock)::numeric(12,3) as stock, s.seuil_alerte
FROM v_stock_courant s
WHERE (s.stock)::numeric(12,3) <= COALESCE(s.seuil_alerte, 0)
AND s.actif = TRUE
ORDER BY (s.stock)::numeric(12,3) ASC;

-- Mouvements récents (enrichi avec catégorie)
CREATE OR REPLACE VIEW v_mouvements_recents AS
SELECT
    m.id, m.date_mvt, m.type, m.quantite, m.source,
    p.id AS produit_id, p.nom, p.categorie
FROM mouvements_stock m
JOIN produits p ON p.id = m.produit_id
ORDER BY m.date_mvt DESC
LIMIT 500;

-- Alias de compatibilité (maintenu)
CREATE OR REPLACE VIEW stock_courant AS SELECT * FROM v_stock_courant;
CREATE OR REPLACE VIEW v_prod_barcodes AS SELECT * FROM v_produits_codes;
