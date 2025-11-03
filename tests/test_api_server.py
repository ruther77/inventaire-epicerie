import importlib

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

pytest.importorskip("fastapi")


@pytest.fixture()
def api_client(tmp_path, monkeypatch):
    db_path = tmp_path / "api.sqlite3"
    database_url = f"sqlite+pysqlite:///{db_path}"
    monkeypatch.setenv("DATABASE_URL", database_url)

    from data_repository import configure_engine, get_engine

    configure_engine(database_url=database_url)
    engine = get_engine()

    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE produits (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nom TEXT NOT NULL,
                    categorie TEXT,
                    prix_vente REAL,
                    prix_achat REAL,
                    tva REAL,
                    stock_actuel REAL DEFAULT 0,
                    seuil_alerte REAL,
                    actif BOOLEAN DEFAULT 1
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE produits_barcodes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    produit_id INTEGER NOT NULL,
                    code TEXT UNIQUE,
                    FOREIGN KEY(produit_id) REFERENCES produits(id)
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE mouvements_stock (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    produit_id INTEGER NOT NULL,
                    type TEXT NOT NULL,
                    quantite REAL NOT NULL,
                    source TEXT,
                    date_mvt DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(produit_id) REFERENCES produits(id)
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TRIGGER trg_update_stock AFTER INSERT ON mouvements_stock
                BEGIN
                    UPDATE produits
                    SET stock_actuel = COALESCE(stock_actuel, 0) + CASE
                        WHEN NEW.type IN ('ENTREE', 'INVENTAIRE', 'TRANSFERT') THEN NEW.quantite
                        WHEN NEW.type = 'SORTIE' THEN -NEW.quantite
                        ELSE 0
                    END
                    WHERE id = NEW.produit_id;
                END;
                """
            )
        )

        conn.execute(
            text(
                """
                INSERT INTO produits (id, nom, categorie, prix_vente, prix_achat, tva, stock_actuel, seuil_alerte, actif)
                VALUES
                    (1, 'Pommes', 'Fruits', 2.5, 1.2, 5.5, 0, 2, 1),
                    (2, 'Jus de Pomme', 'Boissons', 3.8, 1.8, 5.5, 0, 1, 0)
                """
            )
        )
        conn.execute(
            text(
                """
                INSERT INTO produits_barcodes (produit_id, code) VALUES
                    (1, '3700000000001'),
                    (2, '8855000012345')
                """
            )
        )
        conn.execute(
            text(
                """
                INSERT INTO mouvements_stock (produit_id, type, quantite, source, date_mvt) VALUES
                    (1, 'ENTREE', 5, 'Réception fournisseur', '2024-01-01T10:00:00'),
                    (1, 'SORTIE', 2, 'Vente test', '2024-01-02T12:30:00')
                """
            )
        )

    import api_server

    importlib.reload(api_server)
    client = TestClient(api_server.app)

    yield client, engine

    engine.dispose()


def test_healthcheck_ok(api_client):
    client, _ = api_client
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_list_products_and_filters(api_client):
    client, _ = api_client

    response = client.get("/products")
    assert response.status_code == 200
    items = response.json()
    assert len(items) == 1
    assert items[0]["nom"] == "Pommes"
    assert items[0]["stock_actuel"] == 3.0

    response = client.get("/products", params={"include_inactive": "true"})
    assert response.status_code == 200
    assert {item["id"] for item in response.json()} == {1, 2}

    response = client.get("/products", params={"search": "12345", "include_inactive": "true"})
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == 2


def test_get_product_detail(api_client):
    client, _ = api_client

    response = client.get("/products/1")
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == 1
    assert body["mouvements_total"] == 2
    assert body["barcodes"] == ["3700000000001"]
    assert body["dernier_mouvement"].startswith("2024-01-02")

    missing = client.get("/products/999")
    assert missing.status_code == 404


def test_list_product_movements(api_client):
    client, _ = api_client

    response = client.get("/products/1/movements", params={"limit": 1})
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["type"] == "SORTIE"

    response = client.get("/stock/movements", params={"product_id": 1, "limit": 5})
    assert response.status_code == 200
    assert len(response.json()) >= 2


def test_update_stock_creates_movement(api_client):
    client, _ = api_client

    payload = {"product_id": 1, "quantity": 4, "type": "ENTREE", "source": "API Test"}
    response = client.post("/stock/update", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["product_id"] == 1
    assert body["quantity"] == 4.0
    assert body["source"] == "API Test"

    detail = client.get("/products/1").json()
    assert detail["stock_actuel"] == 7.0
    assert detail["mouvements_total"] == 3


def test_bulk_update_partial_success(api_client):
    client, _ = api_client

    payload = {
        "updates": [
            {"product_id": 1, "quantity": 1, "type": "SORTIE", "source": "Inventaire"},
            {"product_id": 999, "quantity": 2, "type": "ENTREE"},
        ]
    }
    response = client.post("/stock/bulk-update", json=payload)
    assert response.status_code == 207
    body = response.json()
    assert body["accepted"] == 1
    assert len(body["results"]) == 1
    assert body["errors"]
    assert "999" in body["errors"][0]

    movements = client.get("/stock/movements", params={"product_id": 1, "limit": 5}).json()
    assert any(mvt["type"] == "SORTIE" and mvt["quantite"] == 1.0 for mvt in movements)
