import types

import sys
from pathlib import Path

import pandas as pd

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import invoice_extractor  # noqa: E402


class DummyPage:
    def __init__(self, text):
        self._text = text

    def extract_text(self):
        return self._text


class DummyPdfReader:
    def __init__(self, _file):
        self.pages = [DummyPage("Page 1"), DummyPage("Page 2")]


class DummyDocument:
    def __init__(self, _file):
        self.paragraphs = [types.SimpleNamespace(text="Paragraph 1"), types.SimpleNamespace(text="Paragraph 2")]


class DummyUpload:
    def __init__(self, file_type, name="test.pdf", content=b""):
        self.type = file_type
        self.name = name
        self._content = content

    def getvalue(self):
        return self._content


def test_clean_data_strips_and_normalises():
    assert invoice_extractor.clean_data(" 12,5- ") == "12.5"
    assert invoice_extractor.clean_data(7) == 7


def test_extract_text_from_pdf(monkeypatch):
    monkeypatch.setattr(invoice_extractor, "PdfReader", DummyPdfReader)
    uploaded = DummyUpload("application/pdf")

    text = invoice_extractor.extract_text_from_file(uploaded)
    assert text == "Page 1Page 2"


def test_extract_text_from_docx(monkeypatch):
    monkeypatch.setattr(invoice_extractor, "Document", DummyDocument)
    uploaded = DummyUpload("application/vnd.openxmlformats-officedocument.wordprocessingml.document", name="file.docx")

    text = invoice_extractor.extract_text_from_file(uploaded)
    assert text == "Paragraph 1\nParagraph 2"


def test_extract_text_from_plain_text():
    uploaded = DummyUpload("text/plain", content=b"hello world")
    assert invoice_extractor.extract_text_from_file(uploaded) == "hello world"


def test_extract_products_from_metro_invoice_builds_dataframe():
    raw_text = """
    1234567890123 123456 Produit Test 1.00 3 3.00 D
    9876543210987 765432 Produit Deux 2.00 1 2.00 P
    """

    df = invoice_extractor.extract_products_from_metro_invoice(raw_text)

    assert isinstance(df, pd.DataFrame)
    assert {"nom", "prix_vente", "tva", "qte_init", "codes", "prix_achat", "tva_code"}.issubset(df.columns)
    assert list(df["nom"]) == ["Produit Test", "Produit Deux"]
    assert list(df["qte_init"]) == [3, 1]
    assert list(df["codes"]) == ["1234567890123", "9876543210987"]
    assert list(df["tva"]) == [20.0, 5.5]
    assert list(df["prix_vente"]) == [1.0, 2.0]
    assert list(df["prix_achat"]) == [1.0, 2.0]
    assert list(df["tva_code"]) == ["D", "P"]


def test_extract_products_with_custom_tva_map():
    raw_text = """
    1234567890123 123456 Produit Test 1.00 3 3.00 Z
    """

    df = invoice_extractor.extract_products_from_metro_invoice(raw_text, tva_map={"Z": 2.1}, default_tva=19.6)

    assert df.loc[0, "tva"] == 2.1
    assert df.loc[0, "tva_code"] == "Z"


def test_extract_text_from_unsupported_type():
    uploaded = DummyUpload("application/octet-stream", name="data.bin")
    assert invoice_extractor.extract_text_from_file(uploaded) == ""
