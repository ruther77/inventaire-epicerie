import sys
from pathlib import Path

import pandas as pd
from sqlalchemy import exc as sa_exc

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import products_loader  # noqa: E402


class DummyRow:
    def __init__(self, produit_id):
        self.produit_id = produit_id


class DummyResult:
    def __init__(self, row=None):
        self._row = row

    def fetchone(self):
        return self._row


class DummyConnection:
    def __init__(self):
        self.executed = []
        self.barcode_map = {}

    def execute(self, statement, params=None):
        sql = str(statement)
        self.executed.append((sql, params))
        params = params or {}
        nom = params.get("nom")

        if "SELECT produit_id" in sql and "produits_barcodes" in sql:
            code = (params.get("code") or "").lower()
            if code in self.barcode_map:
                return DummyResult(DummyRow(self.barcode_map[code]))
            return DummyResult(None)

        if "UPDATE produits" in sql:
            if nom == "Bière artisanale":
                return DummyResult(None)
            if "WHERE id = :pid" in sql and params.get("pid") == 303:
                return DummyResult(None)
            return DummyResult((202,))

        if "INSERT INTO produits (" in sql:
            if nom == "Bière artisanale":
                return DummyResult((101,))
            raise AssertionError("Unexpected insert for nom", nom)

        if "INSERT INTO mouvements_stock" in sql:
            return DummyResult(None)

        if "INSERT INTO produits_barcodes" in sql:
            code = (params.get("code") or "").lower()
            self.barcode_map[code] = params.get("pid")
            return DummyResult(None)

        raise AssertionError(f"Unexpected SQL executed: {sql}")


class DummyContextManager:
    def __init__(self, connection):
        self._connection = connection

    def __enter__(self):
        return self._connection

    def __exit__(self, exc_type, exc, tb):
        return False


class DummyEngine:
    def __init__(self, connection):
        self._connection = connection

    def begin(self):
        return DummyContextManager(self._connection)


def test_insert_or_update_barcode_status_transitions():
    connection = DummyConnection()

    status = products_loader.insert_or_update_barcode(connection, 1, "ABC")
    assert status == "added"

    status = products_loader.insert_or_update_barcode(connection, 1, "abc")
    assert status == "skipped"

    status = products_loader.insert_or_update_barcode(connection, 2, "ABC")
    assert status == "conflict"


def test_clean_codes_and_determine_categorie():
    assert products_loader._clean_codes("111; 222,333\n444") == ["111", "222", "333", "444"]
    assert products_loader._clean_codes(["555", " 666"]) == ["555", "666"]
    assert products_loader.determine_categorie("bière artisanale") == "Alcool"
    assert products_loader.determine_categorie("Savon douceur") == "Hygiene"
    assert products_loader.determine_categorie("Plat Afrique") == "Afrique"


def test_load_products_from_df_summarises_results(monkeypatch):
    df = pd.DataFrame(
        [
            {
                "nom": "Bière artisanale",
                "prix_vente": "5,50",
                "tva": "20",
                "prix_achat": "3",
                "qte_init": "4",
                "codes": "111;222",
            },
            {
                "nom": "Savon douceur",
                "prix_vente": "2.0",
                "tva": "5.5",
                "prix_achat": "1.0",
                "codes": "333",
            },
        ]
    )

    connection = DummyConnection()
    engine = DummyEngine(connection)
    monkeypatch.setattr(products_loader, "get_engine", lambda: engine)

    barcode_calls = []

    def fake_insert_barcode(conn, produit_id, code):
        barcode_calls.append((produit_id, code))
        if code == "111":
            return "added"
        if code == "222":
            return "skipped"
        if code == "333":
            return "conflict"
        return "skipped"

    monkeypatch.setattr(products_loader, "insert_or_update_barcode", fake_insert_barcode)

    summary = products_loader.load_products_from_df(df)

    assert summary["rows_received"] == 2
    assert summary["rows_processed"] == 2
    assert summary["created"] == 1
    assert summary["updated"] == 1
    assert summary["stock_initialized"] == 1
    assert summary["errors"] == []
    assert summary["barcode"] == {"added": 1, "conflicts": 1, "skipped": 1}
    assert barcode_calls == [(101, "111"), (101, "222"), (202, "333")]


def test_load_products_from_df_updates_existing_with_barcode(monkeypatch):
    df = pd.DataFrame(
        [
            {
                "nom": "Produit existant",
                "prix_vente": "12.50",
                "tva": "20",
                "prix_achat": "8.00",
                "qte_init": "5",
                "codes": "444",
            }
        ]
    )

    connection = DummyConnection()
    connection.barcode_map["444"] = 303
    engine = DummyEngine(connection)
    monkeypatch.setattr(products_loader, "get_engine", lambda: engine)

    summary = products_loader.load_products_from_df(df)

    assert summary["rows_received"] == 1
    assert summary["rows_processed"] == 1
    assert summary["created"] == 0
    assert summary["updated"] == 1
    assert summary["stock_initialized"] == 1
    assert summary["barcode"] == {"added": 0, "conflicts": 0, "skipped": 1}

    # Vérifie qu'aucune insertion n'a été réalisée et qu'une mise à jour par ID a eu lieu.
    executed_sql = [sql for sql, _ in connection.executed]
    assert not any("INSERT INTO produits (" in sql for sql in executed_sql)
    assert any("WHERE id = :pid" in sql for sql in executed_sql)

    movement_params = next(
        params for sql, params in connection.executed if "INSERT INTO mouvements_stock" in sql
    )
    assert movement_params["produit_id"] == 303
    assert movement_params["quantite"] == 5.0
    assert movement_params["source"].startswith("Import facture")


def test_load_products_from_df_counts_conflict_on_integrity_error(monkeypatch):
    df = pd.DataFrame(
        [
            {
                "nom": "Produit X",
                "prix_vente": "4",
                "tva": "20",
                "prix_achat": "2",
                "codes": "999",
            }
        ]
    )

    connection = DummyConnection()
    engine = DummyEngine(connection)
    monkeypatch.setattr(products_loader, "get_engine", lambda: engine)

    def raise_integrity(conn, produit_id, code):
        raise sa_exc.IntegrityError("stmt", "params", "orig")

    monkeypatch.setattr(products_loader, "insert_or_update_barcode", raise_integrity)

    summary = products_loader.load_products_from_df(df)

    assert summary["barcode"]["conflicts"] == 1
def test_load_products_from_df_records_errors(monkeypatch):
    df = pd.DataFrame([
        {"nom": " ", "prix_vente": "", "tva": ""},
    ])

    connection = DummyConnection()
    engine = DummyEngine(connection)
    monkeypatch.setattr(products_loader, "get_engine", lambda: engine)

    summary = products_loader.load_products_from_df(df)

    assert summary["rows_received"] == 1
    assert summary["rows_processed"] == 1
    assert len(summary["errors"]) == 1
    error = summary["errors"][0]
    assert error["ligne"] == 2
    assert "Nom du produit manquant" in error["erreur"]


def test_process_products_file_missing_file(tmp_path):
    missing = tmp_path / "missing.csv"
    summary = products_loader.process_products_file(str(missing))

    assert summary["rows_received"] == 0
    assert summary["errors"]
    assert "Fichier introuvable" in summary["errors"][0]["erreur"]
