import importlib.util
from decimal import Decimal
import importlib
from pathlib import Path
import sys

import pandas as pd
import pytest


_MODULE_PATH = Path(__file__).resolve().parents[1] / "inventory_service.py"
_ROOT = _MODULE_PATH.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
_SPEC = importlib.util.spec_from_file_location("inventory_service_under_test", _MODULE_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise ImportError(f"Unable to load inventory_service from {_MODULE_PATH}")
inventory_service = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(inventory_service)

import cart_normalizer


sales_module = importlib.import_module("services.sales")


class DummyScalarResult:
    def __init__(self, value):
        self._value = value

    def scalar(self):
        return self._value


class DummyFetchResult:
    def __init__(self, row):
        self._row = row

    def fetchone(self):
        return self._row


class DummyConnection:
    def __init__(self, handler):
        self.handler = handler
        self.executions = []

    def execute(self, statement, params=None):
        self.executions.append((statement, params))
        return self.handler(statement, params)


class DummyContext:
    def __init__(self, connection):
        self.connection = connection

    def __enter__(self):
        return self.connection

    def __exit__(self, exc_type, exc, tb):
        return False


class DummyEngine:
    def __init__(self, connection):
        self.connection = connection

    def begin(self):
        return DummyContext(self.connection)


def _use_sale_service(monkeypatch, engine):
    monkeypatch.setattr(sales_module, "text", lambda sql: sql)
    monkeypatch.setattr(sales_module, "instrument_sqlalchemy_engine", lambda _engine: None)
    inventory_service.set_sale_service(sales_module.SaleService(lambda: engine))


def test_process_sale_transaction_returns_false_for_empty_cart():
    success, message, receipt = inventory_service.process_sale_transaction([], "user")

    assert success is False
    assert message == "Le panier est vide, aucune vente n'a été effectuée."
    assert receipt is None


def test_process_sale_transaction_fails_when_stock_insufficient(monkeypatch):
    calls = []

    def handler(statement, params):
        calls.append(statement)
        if "SELECT EXISTS" in statement:
            return DummyScalarResult(True)
        if "SELECT stock_actuel" in statement:
            return DummyFetchResult((2,))
        pytest.fail(f"Unexpected statement executed: {statement}")

    connection = DummyConnection(handler)
    engine = DummyEngine(connection)
    _use_sale_service(monkeypatch, engine)

    success, message, receipt = inventory_service.process_sale_transaction([
        {"id": 1, "qty": 5}
    ], "user")

    assert success is False
    assert "Stock insuffisant" in (message or "")
    assert receipt is None
    stock_queries = sum(
        1 for stmt in calls if isinstance(stmt, str) and "SELECT stock_actuel" in stmt
    )
    assert stock_queries == 1
    assert not any("INSERT INTO mouvements_stock" in stmt for stmt in calls if isinstance(stmt, str))


def test_process_sale_transaction_updates_stock_without_trigger(monkeypatch):
    execution_log = []

    def handler(statement, params):
        execution_log.append((statement, params))
        if "SELECT EXISTS" in statement:
            return DummyScalarResult(False)
        if "SELECT stock_actuel" in statement:
            return DummyFetchResult((10,))
        if "UPDATE produits" in statement:
            return DummyFetchResult(None)
        if "INSERT INTO mouvements_stock" in statement:
            return DummyFetchResult(None)
        return DummyFetchResult(None)

    connection = DummyConnection(handler)
    engine = DummyEngine(connection)
    _use_sale_service(monkeypatch, engine)

    success, message, receipt = inventory_service.process_sale_transaction([
        {"id": 3, "qty": 4}
    ], "admin")

    assert success is True
    assert message is None
    assert isinstance(receipt, dict)
    assert receipt.get("filename", "").endswith(".pdf")
    assert isinstance(receipt.get("content"), (bytes, bytearray))
    statements = [stmt for stmt, _ in execution_log]
    assert any("UPDATE produits" in stmt for stmt in statements)
    assert any("INSERT INTO mouvements_stock" in stmt for stmt in statements)


def test_process_sale_transaction_handles_legacy_cart_keys(monkeypatch):
    execution_log = []

    def handler(statement, params):
        execution_log.append((statement, params))
        if "SELECT EXISTS" in statement:
            return DummyScalarResult(True)
        if "SELECT stock_actuel" in statement:
            return DummyFetchResult((25,))
        if "INSERT INTO mouvements_stock" in statement:
            return DummyFetchResult(None)
        if "UPDATE produits" in statement:
            return DummyFetchResult(None)
        return DummyFetchResult(None)

    connection = DummyConnection(handler)
    engine = DummyEngine(connection)
    _use_sale_service(monkeypatch, engine)

    legacy_cart = [
        {
            "product_id": "7",
            "name": "Ancien Produit",
            "quantite": "3",
            "price": "4,50",
            "tva": "20",
        }
    ]

    normalised = cart_normalizer.normalize_cart_rows(legacy_cart)
    assert normalised[0]["prix_total"] == pytest.approx(13.5)

    success, message, receipt = inventory_service.process_sale_transaction(normalised, "legacy_user")

    assert success is True
    assert message is None
    assert receipt is not None

    insert_params_list = next(
        params
        for stmt, params in execution_log
        if isinstance(stmt, str) and "INSERT INTO mouvements_stock" in stmt
    )
    assert insert_params_list
    assert insert_params_list[0]["qty"] == Decimal("3")


def _stubbed_match_df(code: str, product_id: int) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "code": code.lower(),
                "produit_id": product_id,
                "produit_nom": "Produit Test",
                "categorie": "Divers",
                "prix_achat_catalogue": 1.0,
                "prix_vente_catalogue": 2.0,
            }
        ]
    )


def _stubbed_price_df(product_id: int, achat: float, vente: float) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "id": product_id,
                "prix_achat": Decimal(str(achat)),
                "prix_vente": Decimal(str(vente)),
            }
        ]
    )


def test_prepare_invoice_price_updates_detects_large_delta(monkeypatch):
    invoice_df = pd.DataFrame(
        [
            {
                "codes": "1234567890123",
                "quantite_recue": 5,
                "prix_achat_facture": 2.0,
                "montant_total_facture": 10.0,
            }
        ]
    )

    monkeypatch.setattr(
        inventory_service,
        "match_invoice_products",
        lambda df: _stubbed_match_df("1234567890123", 42),
    )
    monkeypatch.setattr(
        inventory_service,
        "query_df",
        lambda sql, params=None: _stubbed_price_df(42, 1.2, 2.0),
    )

    plan = inventory_service.prepare_invoice_price_updates(
        invoice_df,
        min_margin=0.4,
        delta_threshold=0.1,
    )

    assert plan["product_count"] == 1
    assert plan["updates_count"] == 1
    assert plan["skipped_count"] == 0
    update_entry = plan["updates"][0]
    assert update_entry["product_id"] == 42
    assert update_entry["invoice_unit_price"] == pytest.approx(2.0)
    assert update_entry["proposed_sale_price"] == pytest.approx(2.8)


def test_apply_invoice_price_updates_calls_update_catalog(monkeypatch):
    invoice_df = pd.DataFrame(
        [
            {
                "codes": "3456789012345",
                "quantite_recue": 8,
                "prix_achat_facture": 1.5,
                "montant_total_facture": 12.0,
            }
        ]
    )

    monkeypatch.setattr(
        inventory_service,
        "match_invoice_products",
        lambda df: _stubbed_match_df("3456789012345", 7),
    )
    monkeypatch.setattr(
        inventory_service,
        "query_df",
        lambda sql, params=None: _stubbed_price_df(7, 1.0, 1.5),
    )

    applied_payloads = []

    def fake_update_catalog_entry(product_id, payload, barcode_field):
        applied_payloads.append((product_id, payload, barcode_field))
        return {"fields_updated": len(payload)}

    monkeypatch.setattr(
        inventory_service,
        "update_catalog_entry",
        fake_update_catalog_entry,
    )

    result = inventory_service.apply_invoice_price_updates(
        invoice_df,
        min_margin=0.4,
        delta_threshold=0.1,
    )

    assert result["applied_updates"] == 1
    assert applied_payloads
    product_id, payload, barcode_field = applied_payloads[0]
    assert product_id == 7
    assert barcode_field is None
    assert payload["prix_achat"] == pytest.approx(1.5)
    assert payload["prix_vente"] == pytest.approx(2.1)
