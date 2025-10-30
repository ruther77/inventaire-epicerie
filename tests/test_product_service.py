import pytest
from sqlalchemy import create_engine, text

import product_service
import products_loader


@pytest.fixture()
def sqlite_engine(monkeypatch):
    engine = create_engine("sqlite:///:memory:", future=True)
    with engine.begin() as conn:
        conn.exec_driver_sql("PRAGMA foreign_keys = ON")
        conn.exec_driver_sql(
            """
            CREATE TABLE produits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nom TEXT NOT NULL,
                prix_vente REAL,
                tva REAL,
                actif BOOLEAN DEFAULT 1
            )
            """
        )
        conn.exec_driver_sql(
            """
            CREATE TABLE produits_barcodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                produit_id INTEGER NOT NULL,
                code TEXT NOT NULL UNIQUE,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (produit_id) REFERENCES produits(id) ON DELETE CASCADE
            )
            """
        )
    monkeypatch.setattr(product_service, "get_engine", lambda: engine)
    monkeypatch.setattr(products_loader, "get_engine", lambda: engine)
    return engine


def test_parse_barcode_input_normalises_and_deduplicates():
    raw = " 1234567890123 ;1234567890123\n  9876543210987 "
    assert product_service.parse_barcode_input(raw) == ["1234567890123", "9876543210987"]


def test_update_catalog_entry_updates_fields_and_barcodes(sqlite_engine):
    with sqlite_engine.begin() as conn:
        pid = conn.execute(
            text("INSERT INTO produits (nom, prix_vente, tva) VALUES (:n, :p, :t)"),
            {"n": "Riz", "p": 2.5, "t": 5.5},
        ).lastrowid
        conn.execute(
            text("INSERT INTO produits_barcodes (produit_id, code) VALUES (:pid, :code)"),
            {"pid": pid, "code": "321"},
        )

    result = product_service.update_catalog_entry(
        pid,
        {"nom": "Riz parfumé", "prix_vente": 2.9},
        "123456; 654321",
    )

    assert result["fields_updated"] == 2
    assert result["barcodes"]["added"] == 2
    assert result["barcodes"]["removed"] == 1

    with sqlite_engine.connect() as conn:
        row = conn.execute(text("SELECT nom, prix_vente FROM produits WHERE id = :pid"), {"pid": pid}).fetchone()
        assert row == ("Riz parfumé", 2.9)
        codes = {
            r[0]
            for r in conn.execute(
                text("SELECT code FROM produits_barcodes WHERE produit_id = :pid"),
                {"pid": pid},
            )
        }
        assert codes == {"123456", "654321"}


def test_delete_product_by_barcode_removes_single_code(sqlite_engine):
    with sqlite_engine.begin() as conn:
        pid = conn.execute(
            text("INSERT INTO produits (nom) VALUES (:n)"),
            {"n": "Jus"},
        ).lastrowid
        conn.execute(
            text("INSERT INTO produits_barcodes (produit_id, code) VALUES (:pid, :code)"),
            [{"pid": pid, "code": "12345678"}, {"pid": pid, "code": "87654321"}],
        )

    outcome = product_service.delete_product_by_barcode("12345678")
    assert outcome["action"] == "barcode_removed"
    assert outcome["remaining_barcodes"] == 1

    with sqlite_engine.connect() as conn:
        codes = {
            r[0]
            for r in conn.execute(
                text("SELECT code FROM produits_barcodes WHERE produit_id = :pid"),
                {"pid": outcome["product_id"]},
            )
        }
        assert codes == {"87654321"}


def test_delete_product_by_barcode_deletes_product_if_last_code(sqlite_engine):
    with sqlite_engine.begin() as conn:
        pid = conn.execute(
            text("INSERT INTO produits (nom) VALUES (:n)"),
            {"n": "Huile"},
        ).lastrowid
        conn.execute(
            text("INSERT INTO produits_barcodes (produit_id, code) VALUES (:pid, :code)"),
            {"pid": pid, "code": "99999999"},
        )

    outcome = product_service.delete_product_by_barcode("99999999")
    assert outcome["action"] == "product_deleted"
    assert outcome["remaining_barcodes"] == 0

    with sqlite_engine.connect() as conn:
        product = conn.execute(text("SELECT * FROM produits WHERE id = :pid"), {"pid": outcome["product_id"]}).fetchone()
        assert product is None
