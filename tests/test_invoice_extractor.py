"""Tests unitaires pour l'extracteur de lignes METRO."""

from __future__ import annotations

import invoice_extractor


def _df_to_records(df) -> list[dict[str, object]]:
    return df.where(df.notnull(), None).to_dict("records")


def test_extract_products_handles_multiline_descriptions():
    raw_text = """
    3245678901234 12345678 FILETS DE SAUMON FUME LABEL ROUGE
    NORVEGE 2X150G D 0,300 3 59,70 179,10 D
    3760056789012 87654321 JUS D'ORANGE FRAIS 1L PRESSE A FROID
    BIO SANS SUCRE AJOUTE G 1,000 6 3,25 19,50 G
    """

    df = invoice_extractor.extract_products_from_metro_invoice(raw_text)
    records = _df_to_records(df)

    assert len(records) == 2

    first = records[0]
    assert first["codes"] == "3245678901234"
    assert first["numero_article"] == "12345678"
    assert first["nom"].startswith("FILETS DE SAUMON FUME")
    assert first["qte_init"] == 3.0
    assert first["montant_total_facture"] == 179.1
    assert first["prix_achat"] == round(179.1 / 3.0, 4)
    assert first["tva_code"] == "D"
    assert first["tva"] == 20.0

    second = records[1]
    assert second["codes"] == "3760056789012"
    assert second["tva_code"] == "G"
    assert second["qte_init"] == 6.0
    assert second["prix_achat"] == round(19.5 / 6.0, 4)


def test_extract_products_returns_empty_frame_when_no_matches():
    raw_text = "Facture METRO\nAucun produit ici"

    df = invoice_extractor.extract_products_from_metro_invoice(raw_text)

    assert df.empty
    assert list(df.columns) == [
        "nom",
        "codes",
        "numero_article",
        "colisage",
        "qte_init",
        "prix_achat",
        "prix_vente",
        "tva",
        "tva_code",
        "montant_total_facture",
    ]
