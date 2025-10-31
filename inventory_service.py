# inventory_service.py
from collections import defaultdict
from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Iterable

import pandas as pd

from data_repository import get_engine, query_df
from sqlalchemy import text, exc as sa_exc


def _as_decimal(value, default: str = "0") -> Decimal:
    """Safely convert any value to Decimal while handling errors."""

    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal(default)

def _normalise_quantity(value) -> Decimal:
    """Convertit n'importe quelle quantité en Decimal positif."""
    try:
        qty = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal("0")

    if qty.is_nan() or qty <= 0:
        return Decimal("0")

    return qty


def process_sale_transaction(cart: list, username: str) -> tuple[bool, str | None, dict[str, bytes] | None]:
    """Enregistre une vente en décrémentant le stock et en traçant les mouvements.

    Args:
        cart: liste d'articles issus du panier (doit contenir au moins les clés ``id`` et ``qty``).
        username: nom d'utilisateur Streamlit effectuant la vente.

    Returns:
        Tuple (succès, message, reçu). En cas d'échec, le reçu vaut ``None``.
    """
    if not cart:
        return False, "Le panier est vide, aucune vente n'a été effectuée.", None

    aggregated: dict[int, dict[str, Decimal | str]] = defaultdict(
        lambda: {
            "qty": Decimal("0"),
            "label": None,
            "unit_price": Decimal("0"),
            "tva_rate": Decimal("0"),
        }
    )

    for raw_item in cart:
        try:
            pid = int(raw_item["id"])
        except (KeyError, TypeError, ValueError):
            return False, "Un article du panier est invalide (identifiant manquant).", None

        qty = _normalise_quantity(raw_item.get("qty"))
        if qty <= 0:
            continue

        aggregated_item = aggregated[pid]
        aggregated_item["qty"] = aggregated_item["qty"] + qty
        aggregated_item["label"] = raw_item.get("nom") or f"Produit {pid}"

        unit_price = _as_decimal(raw_item.get("prix_vente"))
        tva_rate = _as_decimal(raw_item.get("tva"))

        if aggregated_item["unit_price"] == 0 and unit_price > 0:
            aggregated_item["unit_price"] = unit_price

        if aggregated_item["tva_rate"] == 0 and tva_rate >= 0:
            aggregated_item["tva_rate"] = tva_rate

    if not aggregated:
        return False, "Toutes les lignes du panier ont une quantité nulle.", None

    eng = get_engine()

    try:
        with eng.begin() as conn:
            has_stock_trigger = conn.execute(
                text(
                    """
                    SELECT EXISTS (
                        SELECT 1
                        FROM pg_trigger
                        WHERE tgname = 'trg_update_stock_actuel'
                          AND tgrelid = 'mouvements_stock'::regclass
                    )
                    """
                )
            ).scalar()

            missing_products: list[int] = []
            insufficient: list[str] = []

            for pid, item in aggregated.items():
                stock_row = conn.execute(
                    text("SELECT stock_actuel FROM produits WHERE id = :pid FOR UPDATE"),
                    {"pid": pid},
                ).fetchone()

                if stock_row is None:
                    missing_products.append(pid)
                    continue

                current_stock = Decimal(str(stock_row[0] or 0))
                if current_stock < item["qty"]:
                    insufficient.append(
                        f"{item['label']} (stock {current_stock} < vente {item['qty']})"
                    )

            if missing_products:
                return False, f"Produits introuvables: {', '.join(map(str, missing_products))}.", None

            if insufficient:
                return (
                    False,
                    "Stock insuffisant: " + ", ".join(insufficient),
                    None,
                )

            movements_payload = [
                {
                    "pid": pid,
                    "qty": item["qty"],
                    "source": f"Vente par {username or 'inconnu'}",
                }
                for pid, item in aggregated.items()
            ]

            conn.execute(
                text(
                    """
                    INSERT INTO mouvements_stock (produit_id, type, quantite, source)
                    VALUES (:pid, 'SORTIE', :qty, :source)
                    """
                ),
                movements_payload,
            )

            if not has_stock_trigger:
                for payload in movements_payload:
                    conn.execute(
                        text(
                            """
                            UPDATE produits
                            SET stock_actuel = stock_actuel - :qty,
                                updated_at = now()
                            WHERE id = :pid
                            """
                        ),
                        payload,
                    )

        receipt = _build_sale_receipt(aggregated, username)
        return True, None, receipt

    except sa_exc.IntegrityError as exc:
        return False, f"Erreur d'intégrité lors de l'enregistrement de la vente: {exc.orig}", None
    except Exception as exc:  # pragma: no cover - sécurité supplémentaire pour la session Streamlit
        return False, f"Erreur inattendue lors de la vente: {exc}", None


def _build_sale_receipt(aggregated: dict[int, dict[str, Decimal | str]], username: str | None) -> dict[str, bytes]:
    """Construit un ticket PDF minimaliste à partir des lignes agrégées."""

    timestamp = datetime.now()
    header_lines = [
        "L'INCONTOURNABLE MARKET",
        "Nom commercial / Enseigne : L'INCONTOURNABLE MARKET",
        "Adresse : 83 rue des Poissonnières 75018 Paris",
        "RCS Paris : 922 478 706",
        "Activités : Achat et vente de produits",
        "alimentaires et non alimentaires.",
        "Import / export de produits exotiques.",
        "Début d'activité : 10/12/2022",
        "Mode d'exploitation : Exploitation directe",
        "Origine du fonds : Achat auprès de JENNY",
        "Précédent propriétaire : JENNY",
        "JENNY - 83 rue des Poissonnières 75018 Paris",
        "Immatriculation précédente : 899 755 946 R.C.S. Paris",
        "Précédent exploitant : JENNY",
        "Annonce légale : affiches-parisiennes.com (13/12/2022)",
        "",
        f"Ticket généré le {timestamp.strftime('%d/%m/%Y %H:%M:%S')}",
        f"Caissier: {username or 'inconnu'}",
        "",
        "Articles vendus:",
    ]

    total_ht = Decimal("0")
    total_tva = Decimal("0")
    total_ttc = Decimal("0")
    detail_lines: list[str] = []

    for item in aggregated.values():
        qty = item.get("qty", Decimal("0")) or Decimal("0")
        if qty <= 0:
            continue

        label = str(item.get("label") or "Produit")
        unit_price = _as_decimal(item.get("unit_price"), "0")
        tva_rate = _as_decimal(item.get("tva_rate"), "0")

        line_total = (unit_price * qty).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        if tva_rate > 0:
            divisor = Decimal("1") + (tva_rate / Decimal("100"))
            line_ht = (line_total / divisor).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        else:
            line_ht = line_total
        line_tva = (line_total - line_ht).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        total_ht += line_ht
        total_tva += line_tva
        total_ttc += line_total

        unit_display = (line_total / qty).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) if qty else Decimal("0")
        detail_lines.append(
            f"- {label} × {qty} @ {unit_display:.2f} € = {line_total:.2f} €"
        )

    footer_lines = [
        "",
        f"Total HT: {total_ht.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP):.2f} €",
        f"TVA: {total_tva.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP):.2f} €",
        f"Total TTC: {total_ttc.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP):.2f} €",
        "",
        "Merci pour votre achat !",
    ]

    pdf_bytes = _render_receipt_pdf(header_lines + detail_lines + footer_lines)

    filename = f"ticket_{timestamp.strftime('%Y%m%d_%H%M%S')}.pdf"
    return {"filename": filename, "content": pdf_bytes}


def _render_receipt_pdf(lines: list[str]) -> bytes:
    """Encode les lignes du ticket dans un PDF minimaliste."""

    def _escape(value: str) -> str:
        return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

    text_commands = ["BT", "/F1 10 Tf", "40 480 Td"]
    for line in lines:
        text_commands.append(f"({_escape(line)}) Tj")
        text_commands.append("0 -14 Td")
    text_commands.append("ET")
    content_stream = "\n".join(text_commands)
    content_bytes = content_stream.encode("utf-8")

    objects: list[str] = []
    objects.append("<< /Type /Catalog /Pages 2 0 R >>")
    objects.append("<< /Type /Pages /Count 1 /Kids [3 0 R] >>")
    objects.append(
        "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 500] "
        "/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>"
    )
    objects.append(f"<< /Length {len(content_bytes)} >>\nstream\n{content_stream}\nendstream")
    objects.append("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    pdf_parts: list[str] = []
    offsets: list[int] = []
    current_length = 0

    def _append(part: str) -> None:
        nonlocal current_length
        pdf_parts.append(part)
        current_length += len(part)

    def _add_object(obj_number: int, body: str) -> None:
        offsets.append(current_length)
        obj_repr = f"{obj_number} 0 obj\n{body}\nendobj\n"
        _append(obj_repr)

    _append("%PDF-1.4\n")
    for index, body in enumerate(objects, start=1):
        _add_object(index, body)

    xref_offset = current_length
    total_objects = len(objects) + 1
    _append(f"xref\n0 {total_objects}\n")
    _append("0000000000 65535 f \n")
    for offset in offsets:
        _append(f"{offset:010d} 00000 n \n")

    _append("trailer\n")
    _append(f"<< /Size {total_objects} /Root 1 0 R >>\n")
    _append("startxref\n")
    _append(f"{xref_offset}\n")
    _append("%%EOF")

    return "".join(pdf_parts).encode("utf-8")

# ---------------------------------------------------------------------------
#  Pipelines de factures → commandes
# ---------------------------------------------------------------------------


def match_invoice_products(invoice_df: pd.DataFrame) -> pd.DataFrame:
    """Associe les lignes d'une facture aux produits du catalogue via code-barres."""

    if not isinstance(invoice_df, pd.DataFrame) or invoice_df.empty:
        return pd.DataFrame(
            columns=[
                "code",
                "produit_id",
                "produit_nom",
                "categorie",
                "prix_achat_catalogue",
                "prix_vente_catalogue",
            ]
        )

    if "codes" not in invoice_df.columns:
        return pd.DataFrame(
            columns=[
                "code",
                "produit_id",
                "produit_nom",
                "categorie",
                "prix_achat_catalogue",
                "prix_vente_catalogue",
            ]
        )

    codes: list[str] = []
    for raw in invoice_df["codes"].tolist():
        if isinstance(raw, str):
            normalized = raw.strip()
            if normalized:
                codes.append(normalized)
        elif isinstance(raw, Iterable):
            for part in raw:
                part_str = str(part or "").strip()
                if part_str:
                    codes.append(part_str)

    unique_codes = sorted({code.lower() for code in codes if code})
    if not unique_codes:
        return pd.DataFrame(
            columns=[
                "code",
                "produit_id",
                "produit_nom",
                "categorie",
                "prix_achat_catalogue",
                "prix_vente_catalogue",
            ]
        )

    placeholders = ", ".join(f"LOWER(:code{i})" for i in range(len(unique_codes)))
    params = {f"code{i}": code for i, code in enumerate(unique_codes)}

    sql = f"""
        SELECT
            LOWER(pb.code) AS code,
            p.id AS produit_id,
            p.nom AS produit_nom,
            p.categorie,
            COALESCE(p.prix_achat, 0) AS prix_achat_catalogue,
            COALESCE(p.prix_vente, 0) AS prix_vente_catalogue
        FROM produits_barcodes pb
        JOIN produits p ON p.id = pb.produit_id
        WHERE LOWER(pb.code) IN ({placeholders})
    """

    try:
        df = query_df(sql, params=params)
    except Exception:
        return pd.DataFrame(
            columns=[
                "code",
                "produit_id",
                "produit_nom",
                "categorie",
                "prix_achat_catalogue",
                "prix_vente_catalogue",
            ]
        )

    if "code" in df.columns:
        df["code"] = df["code"].astype(str).str.lower()
    return df


def register_invoice_reception(
    invoice_df: pd.DataFrame,
    *,
    username: str,
    supplier: str | None = None,
    movement_type: str = "ENTREE",
    reception_date: datetime | None = None,
) -> dict[str, object]:
    """Crée des mouvements d'entrée à partir d'une réception de facture."""

    summary = {
        "rows_received": int(len(invoice_df)) if isinstance(invoice_df, pd.DataFrame) else 0,
        "movements_created": 0,
        "quantity_total": 0.0,
        "errors": [],
    }

    if not isinstance(invoice_df, pd.DataFrame) or invoice_df.empty:
        return summary

    safe_type = (movement_type or "ENTREE").upper()
    if safe_type not in {"ENTREE", "TRANSFERT"}:
        safe_type = "ENTREE"

    label_parts = [supplier.strip() for supplier in [supplier] if isinstance(supplier, str) and supplier.strip()]
    if username:
        label_parts.append(f"traité par {username}")
    source_label = " · ".join(label_parts) or "Réception facture"

    payloads: list[dict[str, object]] = []

    for row in invoice_df.itertuples():
        product_id = getattr(row, "produit_id", None)
        quantity = getattr(row, "quantite_recue", None)
        if quantity is None:
            quantity = getattr(row, "qte_init", None)

        normalised_qty = _normalise_quantity(quantity)
        if product_id in (None, "") or normalised_qty <= 0:
            summary["errors"].append(
                f"Ligne {getattr(row, 'Index', '?') + 1 if hasattr(row, 'Index') else '?'} invalide (produit ou quantité)"
            )
            continue

        payloads.append(
            {
                "pid": int(product_id),
                "qty": float(normalised_qty),
                "source": source_label,
                "type": safe_type,
                "date_mvt": reception_date,
            }
        )

    if not payloads:
        return summary

    insert_sql = text(
        """
        INSERT INTO mouvements_stock (produit_id, type, quantite, source, date_mvt)
        VALUES (:pid, :type, :qty, :source, COALESCE(:date_mvt, now()))
        """
    )

    eng = get_engine()
    try:
        with eng.begin() as conn:
            conn.execute(insert_sql, payloads)
    except sa_exc.IntegrityError as exc:
        summary["errors"].append(f"Erreur d'intégrité lors de l'enregistrement: {exc.orig}")
        return summary
    except Exception as exc:  # pragma: no cover - sécurité runtime
        summary["errors"].append(str(exc))
        return summary

    summary["movements_created"] = len(payloads)
    summary["quantity_total"] = float(sum(item["qty"] for item in payloads))
    return summary

# Ajoutez d'autres fonctions de service ici (ex: adjust_stock, create_product_with_barcode)
