from __future__ import annotations

import io
import re
from typing import Iterable, Mapping

import pandas as pd

try:  # pragma: no cover - import de compatibilité
    from pypdf import PdfReader
except ImportError:  # pragma: no cover - environnement sans pypdf
    class PdfReader:  # type: ignore
        """Substitut minimal rappelant d'installer pypdf."""

        def __init__(self, *_args, **_kwargs):
            raise ImportError(
                "La dépendance 'pypdf' est requise pour lire les factures PDF. "
                "Ajoutez-la via `pip install pypdf`."
            )
from docx import Document

# Mapping par défaut des codes TVA METRO connus.
#
# Les codes sont documentés par METRO et couvrent l'ensemble des taux
# appliqués sur les factures françaises :
#
# - 20 % (taux normal)      : A, C, D, F, J, K
# - 10 % (taux intermédiaire): B, H, N, T
# - 5,5 % (taux réduit)     : E, I, L, P, Q, R, S, U, V, W, Y
# - 2,1 % (taux particulier): M
# - 0 % (exonérations)      : G, O, X, Z
#
# Un code inconnu tombera sur ``default_tva`` mais il est toujours possible
# de surcharger ce mapping via ``tva_map`` lors de l'appel.
_METRO_TVA_CODE_GROUPS: tuple[tuple[float, tuple[str, ...]], ...] = (
    (20.0, ("A", "C", "D", "F", "J", "K")),
    (10.0, ("B", "H", "N", "T")),
    (5.5, ("E", "I", "L", "P", "Q", "R", "S", "U", "V", "W", "Y")),
    (2.1, ("M",)),
    (0.0, ("G", "O", "X", "Z")),
)

DEFAULT_TVA_CODE_MAP: dict[str, float] = {
    code: rate
    for rate, codes in _METRO_TVA_CODE_GROUPS
    for code in codes
}

def clean_data(value):
    """Nettoie une valeur numérique (remplace la virgule par le point)."""
    if isinstance(value, str):
        # Remplace la virgule par le point et supprime tout caractère non numérique/point/espace
        return value.replace(',', '.').replace('-', '').strip()
    return value

def extract_text_from_file(uploaded_file):
    """
    Extrait le texte brut d'un fichier téléversé (PDF ou DOCX/DOC).
    """
    file_type = uploaded_file.type

    if hasattr(uploaded_file, "seek"):
        uploaded_file.seek(0)

    # 1. Traitement des PDF
    if 'pdf' in file_type:
        try:
            pdf_reader = PdfReader(uploaded_file)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() or ""
            return text
        except Exception:
            return "Erreur lors de la lecture du PDF."

    # 2. Traitement des DOCX (Word)
    elif 'word' in file_type or 'document' in file_type or uploaded_file.name.endswith('.docx'):
        try:
            document = Document(uploaded_file)
            text = '\n'.join([paragraph.text for paragraph in document.paragraphs])
            return text
        except Exception:
            return "Erreur lors de la lecture du fichier Word (.docx)."

    # 3. Traitement du texte brut
    elif 'text' in file_type or uploaded_file.name.endswith('.txt'):
        return uploaded_file.getvalue().decode("utf-8")
        
    else:
        return "" # Type de fichier non supporté

# Fichier : invoice_extractor.py (Mise à jour de la fonction d'extraction)

# ... (les imports et la fonction clean_data restent inchangés) ...

def _normalise_tva_code(code: str | None) -> str | None:
    if not code:
        return None
    cleaned = str(code).strip().upper()
    return cleaned or None


def _resolve_tva_value(code: str | None, tva_lookup: Mapping[str, float], default_tva: float) -> float:
    if code is None:
        return default_tva
    if code in tva_lookup:
        return float(tva_lookup[code])
    return default_tva


def extract_products_from_metro_invoice(
    raw_product_text: str,
    *,
    tva_map: Mapping[str, float] | None = None,
    default_tva: float = 20.0,
) -> pd.DataFrame:
    """Analyse et structure les lignes produit d'une facture METRO.

    Les factures METRO listent chaque produit sur une ou plusieurs lignes
    contenant au minimum : le code EAN, la référence article, la description,
    les quantités facturées, le montant total et un code TVA (D, S, X, G…).

    Cette fonction tolère les descriptions multi-lignes et les colonnes
    supplémentaires (colisage, prix unitaire HT/TTC, etc.). L'objectif est de
    restituer un ``DataFrame`` normalisé prêt à être rapproché du catalogue.
    """

    raw_text = (raw_product_text or "").replace("\r\n", "\n")
    if not raw_text.strip():
        return pd.DataFrame(
            columns=[
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
        )

    overrides = {k.upper(): float(v) for k, v in (tva_map or {}).items()}
    lookup = {**DEFAULT_TVA_CODE_MAP, **overrides}

    item_start = re.compile(r"^\s*(?P<ean>\d{10,14})\s+(?P<article>\d{6,10})(?=\s)")

    def _split_lines(text: str) -> list[str]:
        blocks: list[str] = []
        current: list[str] = []
        for line in text.split("\n"):
            stripped = line.strip()
            if not stripped:
                continue
            if item_start.match(stripped):
                if current:
                    blocks.append(" ".join(current))
                current = [stripped]
            else:
                if current:
                    current.append(stripped)
        if current:
            blocks.append(" ".join(current))
        return blocks

    def _is_number(token: str) -> bool:
        return bool(re.fullmatch(r"\d+(?:[.,]\d+)?", token))

    def _parse_float(token: str | None) -> float | None:
        if not token:
            return None
        try:
            return float(token.replace(",", "."))
        except ValueError:
            return None

    records: list[dict[str, object]] = []

    for block in _split_lines(raw_text):
        normalised = re.sub(r"\s+", " ", block).strip()
        match = item_start.match(normalised)
        if not match:
            continue

        ean = match.group("ean")
        article = match.group("article")
        remainder = normalised[match.end():].strip()

        # Extraire le code TVA (une lettre isolée en fin de ligne)
        tva_code = None
        tva_match = re.search(r"([A-Z])$", remainder)
        if tva_match and tva_match.group(1).isalpha():
            tva_code = _normalise_tva_code(tva_match.group(1))
            remainder = remainder[: tva_match.start()].strip()

        # Montant total TTC (dernier nombre de la ligne)
        amount_match = re.search(r"(\d+(?:[.,]\d+)?)$", remainder)
        if not amount_match:
            continue
        amount_value = _parse_float(amount_match.group(1))
        remainder = remainder[: amount_match.start()].strip()

        tokens = remainder.split()
        numeric_tail: list[str] = []
        while tokens and _is_number(tokens[-1]):
            numeric_tail.append(tokens.pop())

        numeric_values = [_parse_float(token) for token in numeric_tail]
        unit_price_value = numeric_values[0] if numeric_values else None
        quantity_value = numeric_values[1] if len(numeric_values) > 1 else None
        colisage_value = numeric_values[2] if len(numeric_values) > 2 else None

        designation = " ".join(tokens).strip()
        designation = re.sub(
            r"(Duplicata|PRIX AU KG OU AU LITRE|Plus COTIS SECURITE SOCIALE|Montant TTC|PAGE:.*|Volume effectif).*",
            "",
            designation,
            flags=re.IGNORECASE,
        ).strip()

        if not designation:
            designation = remainder.strip()

        if amount_value is None:
            continue

        qty = quantity_value or 0.0
        if qty <= 0 and unit_price_value and unit_price_value > 0:
            qty = amount_value / unit_price_value
        unit_price = (
            unit_price_value
            if unit_price_value and unit_price_value > 0
            else (amount_value if qty <= 0 else amount_value / max(qty, 1e-9))
        )

        tva_value = _resolve_tva_value(tva_code, lookup, default_tva)

        records.append(
            {
                "nom": designation,
                "codes": ean,
                "numero_article": article,
                "colisage": round(colisage_value, 4) if colisage_value else None,
                "qte_init": round(qty, 4),
                "prix_achat": round(unit_price, 4),
                "prix_vente": round(unit_price, 4),
                "tva": round(tva_value, 4),
                "tva_code": tva_code,
                "montant_total_facture": round(amount_value, 4),
            }
        )

    if not records:
        return pd.DataFrame(
            columns=[
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
        )

    df = pd.DataFrame.from_records(records)
    desired_order: Iterable[str] = (
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
    )
    columns = [col for col in desired_order if col in df.columns]
    return df.loc[:, columns]

# ... (le bloc if __name__ == '__main__': reste inchangé) ...
if __name__ == '__main__':
    pass
