import importlib.util
from decimal import Decimal
from pathlib import Path
import sys

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
    monkeypatch.setattr(inventory_service, "get_engine", lambda: engine)
    monkeypatch.setattr(inventory_service, "text", lambda sql: sql)

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
    monkeypatch.setattr(inventory_service, "get_engine", lambda: engine)
    monkeypatch.setattr(inventory_service, "text", lambda sql: sql)

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
    monkeypatch.setattr(inventory_service, "get_engine", lambda: engine)
    monkeypatch.setattr(inventory_service, "text", lambda sql: sql)

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
