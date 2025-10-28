import pandas as pd
import pandas.testing as pd_testing
from sqlalchemy import text

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import data_repository


class _FakeResult:
    def __init__(self, rows, columns):
        self._rows = rows
        self._columns = columns

    def keys(self):
        return list(self._columns)

    def fetchall(self):
        return list(self._rows)


class _FakeConnection:
    def __init__(self, executed_container):
        self._executed = executed_container

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, statement):
        raise TypeError("expected string or bytes-like object, got 'TextClause'")

    def exec_driver_sql(self, sql_text):
        self._executed["sql"] = sql_text
        return _FakeResult(rows=[(7,)], columns=["val"])


class _FakeEngine:
    def __init__(self, executed_container):
        self._executed = executed_container

    def begin(self):
        return _FakeConnection(self._executed)


def test_query_df_retries_with_literal_sql(monkeypatch):
    executed = {}

    fake_engine = _FakeEngine(executed)
    monkeypatch.setattr(data_repository, "get_engine", lambda: fake_engine)

    df = data_repository.query_df(text("SELECT :value AS val"), params={"value": 7})

    assert executed["sql"].strip() == "SELECT 7 AS val"
    expected = pd.DataFrame([(7,)], columns=["val"])
    pd_testing.assert_frame_equal(df, expected)
