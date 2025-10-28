import importlib
import sys
import types
from collections import namedtuple

import pytest


class DummyResult:
    def __init__(self, fetchone_value=None):
        self._fetchone_value = fetchone_value

    def fetchone(self):
        return self._fetchone_value


class DummyConnection:
    def __init__(self, handler=None):
        self.handler = handler or (lambda statement, params: None)
        self.executions = []

    def execute(self, statement, params=None):
        self.executions.append((statement, params))
        return self.handler(statement, params)


class DummyContextManager:
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
        return DummyContextManager(self.connection)

    def connect(self):
        return DummyContextManager(self.connection)


@pytest.fixture(autouse=True)
def stub_streamlit(monkeypatch):
    if "streamlit" in sys.modules:
        monkeypatch.setattr(sys.modules["streamlit"], "cache_resource", lambda func: func)
        yield
    else:
        stub = types.SimpleNamespace(cache_resource=lambda func: func)
        sys.modules["streamlit"] = stub
        yield
        sys.modules.pop("streamlit", None)


@pytest.fixture
def data_repository():
    return importlib.import_module("data_repository")


def test_exec_sql_supports_batch_params(monkeypatch, data_repository):
    connection = DummyConnection()
    engine = DummyEngine(connection)
    monkeypatch.setattr(data_repository, "get_engine", lambda: engine)

    params = [{"value": 1}, {"value": 2}]
    data_repository.exec_sql("INSERT INTO table VALUES (:value)", params=params)

    assert len(connection.executions) == 1
    statement, received_params = connection.executions[0]
    assert isinstance(statement, data_repository.TextClause)
    assert statement.text == "INSERT INTO table VALUES (:value)"
    assert received_params == params


def test_exec_sql_return_id_fetches_first_column(monkeypatch, data_repository):
    expected_id = 42

    def handler(statement, params):
        return DummyResult((expected_id, "unused"))

    connection = DummyConnection(handler=handler)
    engine = DummyEngine(connection)
    monkeypatch.setattr(data_repository, "get_engine", lambda: engine)

    new_id = data_repository.exec_sql_return_id("INSERT ... RETURNING id")
    assert new_id == expected_id


def test_get_product_options_returns_name_id_pairs(monkeypatch, data_repository):
    Row = namedtuple("Row", ["nom", "id"])

    def handler(statement, params):
        return [Row("Banane", 1), Row("Pomme", 2)]

    connection = DummyConnection(handler=handler)
    engine = DummyEngine(connection)
    monkeypatch.setattr(data_repository, "get_engine", lambda: engine)

    options = data_repository.get_product_options()
    assert options == [("Banane", 1), ("Pomme", 2)]


def test_get_product_details_accepts_string_identifier(monkeypatch, data_repository):
    ProductRow = namedtuple("ProductRow", ["id", "nom", "quantite_stock"])
    product_row = ProductRow(5, "Fraise", 12)

    def handler(statement, params):
        assert params["identifier_int"] is None
        assert params["identifier_str"] == "ABC"
        return DummyResult(product_row)

    connection = DummyConnection(handler=handler)
    engine = DummyEngine(connection)
    monkeypatch.setattr(data_repository, "get_engine", lambda: engine)

    details = data_repository.get_product_details("ABC")
    assert details == product_row._asdict()


def test_query_df_accepts_string_sql(monkeypatch, data_repository):
    captured = {}
    dummy_df = object()

    def fake_read_sql(statement, conn, params=None):
        captured["statement"] = statement
        captured["params"] = params
        captured["conn"] = conn
        return dummy_df

    connection = object()
    engine = DummyEngine(connection)
    monkeypatch.setattr(data_repository, "get_engine", lambda: engine)
    monkeypatch.setattr(data_repository.pd, "read_sql", fake_read_sql)

    result = data_repository.query_df("SELECT 1", params={"foo": "bar"})

    assert result is dummy_df
    assert isinstance(captured["statement"], data_repository.TextClause)
    assert captured["statement"].text == "SELECT 1"
    assert captured["params"] == {"foo": "bar"}
    assert captured["conn"] is connection


def test_query_df_accepts_text_clause(monkeypatch, data_repository):
    captured = {}
    dummy_df = object()

    def fake_read_sql(statement, conn, params=None):
        captured["statement"] = statement
        captured["params"] = params
        captured["conn"] = conn
        return dummy_df

    connection = object()
    engine = DummyEngine(connection)
    monkeypatch.setattr(data_repository, "get_engine", lambda: engine)
    monkeypatch.setattr(data_repository.pd, "read_sql", fake_read_sql)

    text_clause = data_repository.text("SELECT * FROM produits")
    result = data_repository.query_df(text_clause)

    assert result is dummy_df
    assert captured["statement"] is text_clause
    assert captured["params"] is None
    assert captured["conn"] is connection
