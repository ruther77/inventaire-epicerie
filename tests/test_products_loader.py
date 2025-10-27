import sys
from pathlib import Path

import pandas as pd
from sqlalchemy import exc as sa_exc

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import products_loader  # noqa: E402


class DummyResult:
    def __init__(self, row=None):
        self._row = row

    def fetchone(self):
        return self._row


class DummyConnection:
    def __init__(self):
        self.executed = []

    def execute(self, statement, params=None):
        sql = str(statement)
        self.executed.append((sql, params))
        nom = params.get("nom") if isinstance(params, dict) else None

        if "UPDATE produits" in sql:
            if nom == "Bière artisanale":
                return DummyResult(None)
            return DummyResult((202,))

        if "INSERT INTO produits (" in sql:
            if nom == "Bière artisanale":
                return DummyResult((101,))
            raise AssertionError("Unexpected insert for nom", nom)

        if "INSERT INTO mouvements_stock" in sql:
            return DummyResult(None)

        if "INSERT INTO produits_barcodes" in sql:
            # This path is not used in tests because insert_or_update_barcode is patched.
            return DummyResult((params or {}).get("code"))

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


def test_insert_or_update_barcode_status_added_and_skipped():
    connection = DummyConnection()

    def execute_added(statement, params=None):
        return DummyResult((params["code"],))

    def execute_skipped(statement, params=None):
        return DummyResult(None)

    connection.execute = execute_added
    status = products_loader.insert_or_update_barcode(connection, 1, "ABC")
    assert status == "added"

    connection.execute = execute_skipped
    status = products_loader.insert_or_update_barcode(connection, 1, "ABC")
    assert status == "skipped"


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
            raise sa_exc.IntegrityError("stmt", "params", "orig")
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
