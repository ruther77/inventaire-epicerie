import ast
from pathlib import Path
import math


def _load_to_float():
    source = Path("app.py").read_text(encoding="utf-8")
    module = ast.parse(source, filename="app.py")
    for node in module.body:
        if isinstance(node, ast.FunctionDef) and node.name == "to_float":
            func_module = ast.Module(body=[node], type_ignores=[])
            code = compile(func_module, filename="app.py", mode="exec")
            namespace = {}
            exec(code, {"math": math}, namespace)
            return namespace["to_float"]
    raise RuntimeError("to_float function not found in app.py")


def test_to_float_respects_maxv_upper_bound():
    to_float = _load_to_float()
    assert to_float("150", maxv=100.0) == 100.0


def test_to_float_respects_minv_lower_bound():
    to_float = _load_to_float()
    assert to_float("-5", minv=0.0) == 0.0
