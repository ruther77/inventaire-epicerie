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
    """Analyse une facture METRO et renvoie un DataFrame exploitable.

    Args:
        raw_product_text: Texte brut de la facture (ou section produits).
        tva_map: Dictionnaire optionnel pour surcharger le mapping TVA
            (par exemple {"D": 20.0, "P": 5.5}).
        default_tva: Valeur de TVA utilisée si le code n'est pas reconnu.

    Returns:
        DataFrame contenant au minimum les colonnes `nom`, `codes`,
        `qte_init`, `prix_achat`, `prix_vente`, `tva` et `tva_code`.
    """

    # Étape 1: Nettoyage et simplification du texte
    text = re.sub(r'["\s,]+', ' ', raw_product_text or "").strip()
    text = text.replace('\n', '; ')

    pattern = re.compile(
        r'(\d{10,14})'  # EAN
        r'\s*(\d{6,10})'  # Numéro article
        r'\s*(.+?)'  # Désignation
        r'([\d\.]+)'  # Prix unitaire
        r'\s*(\d+)'  # Quantité
        r'\s*([\d\.]+)'  # Montant total
        r'\s*([A-Z])',  # Code TVA
        re.IGNORECASE | re.DOTALL,
    )

    processed_text = text.replace(',', '.')
    overrides = {k.upper(): float(v) for k, v in (tva_map or {}).items()}
    lookup = {**DEFAULT_TVA_CODE_MAP, **overrides}

    records: list[dict[str, object]] = []

    for match in pattern.finditer(processed_text):
        try:
            ean = match.group(1).strip()
            article = match.group(2).strip()
            designation_raw = match.group(3).strip()
            designation = re.sub(
                r'(Duplicata|PRIX AU KG OU AU LITRE|Plus COTIS SECURITE SOCIALE|Total:.*|Volume effectif|Montant TTC|PAGE:.*|Numéro Article|VE unit. L.).*',
                '',
                designation_raw,
            ).strip()

            unit_price = float(match.group(4))
            quantity = max(int(match.group(5)), 0)
            total_amount = float(match.group(6))
            tva_code = _normalise_tva_code(match.group(7))
            tva_value = _resolve_tva_value(tva_code, lookup, default_tva)

            records.append(
                {
                    'nom': designation,
                    'codes': ean,
                    'numero_article': article,
                    'qte_init': quantity,
                    'prix_achat': round(unit_price, 4),
                    'prix_vente': round(unit_price, 4),
                    'tva': round(tva_value, 4),
                    'tva_code': tva_code,
                    'montant_total_facture': round(total_amount, 4),
                }
            )
        except Exception:
            continue

    if not records:
        return pd.DataFrame(columns=[
            'nom',
            'codes',
            'numero_article',
            'qte_init',
            'prix_achat',
            'prix_vente',
            'tva',
            'tva_code',
            'montant_total_facture',
        ])

    df = pd.DataFrame(records)
    desired_order: Iterable[str] = (
        'nom',
        'codes',
        'numero_article',
        'qte_init',
        'prix_achat',
        'prix_vente',
        'tva',
        'tva_code',
        'montant_total_facture',
    )
    columns = [col for col in desired_order if col in df.columns]
    return df.loc[:, columns]

# ... (le bloc if __name__ == '__main__': reste inchangé) ...
if __name__ == '__main__':
    pass
