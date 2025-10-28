import ast
from pathlib import Path
import types

import pandas as pd
import pandas.testing as pd_testing


def _load_function(name, extra_globals=None):
    source = Path("app.py").read_text(encoding="utf-8")
    module = ast.parse(source, filename="app.py")

    for node in module.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            func_module = ast.Module(body=[node], type_ignores=[])
            code = compile(func_module, filename="app.py", mode="exec")

            globals_dict = {"pd": pd}
            if extra_globals:
                globals_dict.update(extra_globals)

            exec(code, globals_dict)
            return globals_dict[name]

    raise RuntimeError(f"Function {name} not found in app.py")


def _build_streamlit_stub(warning_collector=None, error_collector=None):
    warning_collector = warning_collector if warning_collector is not None else []
    error_collector = error_collector if error_collector is not None else []

    def cache_data(ttl=None):
        def decorator(func):
            return func

        return decorator

    return types.SimpleNamespace(
        cache_data=cache_data,
        warning=lambda message: warning_collector.append(message),
        error=lambda message: error_collector.append(message),
    )


def test_load_table_preview_builds_safe_query():
    captured = {}

    def fake_query(sql):
        captured["sql"] = sql
        return pd.DataFrame([[1]], columns=["id"])

    st_stub = _build_streamlit_stub()
    func = _load_function("load_table_preview", {"query_df": fake_query, "st": st_stub})

    df = func("produits", limit=5)

    assert captured["sql"] == "SELECT * FROM public.produits ORDER BY id DESC LIMIT 5"
    pd_testing.assert_frame_equal(df, pd.DataFrame([[1]], columns=["id"]))


def test_load_table_preview_recovers_from_bad_limit():
    captured = {}

    def fake_query(sql):
        captured["sql"] = sql
        return pd.DataFrame(columns=["id"])

    warnings = []
    st_stub = _build_streamlit_stub(warning_collector=warnings)
    func = _load_function("load_table_preview", {"query_df": fake_query, "st": st_stub})

    df = func("produits_barcodes", limit="invalid")

    assert captured["sql"] == "SELECT * FROM public.produits_barcodes ORDER BY id DESC LIMIT 20"
    assert df.empty
    assert warnings == []


def test_load_stock_diagnostics_orders_by_alias():
    captured = {}

    def fake_query(sql):
        captured["sql"] = sql
        return pd.DataFrame(
            [
                (1, "Produit A", 10, 9.5, 0.5),
                (2, "Produit B", 5, 4.0, 1.0),
            ],
            columns=["id", "nom", "stock_actuel", "stock_calcule", "ecart"],
        )

    st_stub = _build_streamlit_stub()
    func = _load_function("load_stock_diagnostics", {"query_df": fake_query, "st": st_stub})

    df = func()

    assert "ORDER BY ABS(stock_actuel - stock_calcule) DESC, nom" in captured["sql"]
    pd_testing.assert_frame_equal(
        df,
        pd.DataFrame(
            [
                (1, "Produit A", 10, 9.5, 0.5),
                (2, "Produit B", 5, 4.0, 1.0),
            ],
            columns=["id", "nom", "stock_actuel", "stock_calcule", "ecart"],
        ),
    )


def test_load_stock_diagnostics_handles_exception():
    errors = []

    def failing_query(sql):
        raise RuntimeError("boom")

    st_stub = _build_streamlit_stub(error_collector=errors)
    func = _load_function("load_stock_diagnostics", {"query_df": failing_query, "st": st_stub})

    df = func()

    assert errors and "boom" in errors[0]
    assert list(df.columns) == ["id", "nom", "stock_actuel", "stock_calcule", "ecart"]
    assert df.empty
