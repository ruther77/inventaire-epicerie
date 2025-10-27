import sys
from pathlib import Path

import pandas as pd

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import extractor  # noqa: E402


def test_clean_data_normalizes_string():
    assert extractor.clean_data(" 1,23- ") == "1.23"
    assert extractor.clean_data(5) == 5


def test_extract_products_parses_basic_invoice():
    raw_text = """
    1234567890123 123456 Pain au chocolat 1.50 2 3.00 D
    9876543210987 765432 Jus de pomme 0.80 5 4.00 P
    """

    df = extractor.extract_products_from_metro_invoice(raw_text)

    assert isinstance(df, pd.DataFrame)
    assert len(df) == 2
    assert list(df["EAN"]) == ["1234567890123", "9876543210987"]
    assert list(df["Numéro Article"]) == ["123456", "765432"]
    assert df.loc[0, "Désignation"].startswith("Pain au chocolat")
    assert df.loc[1, "Quantité"] == 5
    assert df.loc[0, "Montant Total"] == 3.0
