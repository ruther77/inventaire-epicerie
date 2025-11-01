from __future__ import annotations

import logging
from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Iterable

import pandas as pd

from data_repository import get_engine, query_df
from sqlalchemy import exc as sa_exc, text

from services import SaleService, SavedViewsService, as_decimal, normalise_quantity
from telemetry import get_tracer


logger = logging.getLogger(__name__)
tracer = get_tracer(__name__)
_sale_service: SaleService | None = None
_saved_views_service: SavedViewsService | None = None


def get_sale_service() -> SaleService:
    global _sale_service
    if _sale_service is None:
        _sale_service = SaleService(engine_factory=get_engine)
    return _sale_service


def set_sale_service(service: SaleService | None) -> None:
    global _sale_service
    _sale_service = service


def get_saved_views_service() -> SavedViewsService:
    global _saved_views_service
    if _saved_views_service is None:
        _saved_views_service = SavedViewsService(engine_factory=get_engine)
    return _saved_views_service


def set_saved_views_service(service: SavedViewsService | None) -> None:
    global _saved_views_service
    _saved_views_service = service


def process_sale_transaction(cart: list, username: str) -> tuple[bool, str | None, dict[str, bytes] | None]:
    """Delegate sale processing to the domain service."""

    return get_sale_service().process_sale_transaction(cart, username)

# ---------------------------------------------------------------------------
#  Pipelines de factures → commandes
# ---------------------------------------------------------------------------


def match_invoice_products(invoice_df: pd.DataFrame) -> pd.DataFrame:
    """Associe les lignes d'une facture aux produits du catalogue via code-barres."""

    empty_columns = [
        "code",
        "produit_id",
        "produit_nom",
        "categorie",
        "prix_achat_catalogue",
        "prix_vente_catalogue",
    ]

    with tracer.start_as_current_span("imports.match_invoice_products") as span:
        row_count = int(len(invoice_df)) if isinstance(invoice_df, pd.DataFrame) else 0
        span.set_attribute("imports.row_count", row_count)

        if not isinstance(invoice_df, pd.DataFrame) or invoice_df.empty:
            span.set_attribute("imports.status", "empty_input")
            return pd.DataFrame(columns=empty_columns)

        if "codes" not in invoice_df.columns:
            span.set_attribute("imports.status", "missing_codes_column")
            return pd.DataFrame(columns=empty_columns)

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
        span.set_attribute("imports.code_count", len(unique_codes))
        if not unique_codes:
            span.set_attribute("imports.status", "no_codes")
            return pd.DataFrame(columns=empty_columns)

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
        except Exception as exc:  # pragma: no cover - defensive logging
            span.record_exception(exc)
            span.set_attribute("imports.status", "query_failed")
            logger.exception(
                "match_invoice_products failed to fetch catalogue data",
                extra={
                    "code_count": len(unique_codes),
                    "sample_codes": unique_codes[:10],
                },
            )
            raise

        span.set_attribute("imports.status", "success")
        span.set_attribute("imports.results", int(len(df)))
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

    with tracer.start_as_current_span("imports.register_invoice_reception") as span:
        summary = {
            "rows_received": int(len(invoice_df)) if isinstance(invoice_df, pd.DataFrame) else 0,
            "movements_created": 0,
            "quantity_total": 0.0,
            "errors": [],
        }
        span.set_attribute("imports.rows_received", summary["rows_received"])

        if not isinstance(invoice_df, pd.DataFrame) or invoice_df.empty:
            span.set_attribute("imports.status", "empty_input")
            return summary

        safe_type = (movement_type or "ENTREE").upper()
        if safe_type not in {"ENTREE", "TRANSFERT"}:
            safe_type = "ENTREE"
        span.set_attribute("imports.movement_type", safe_type)

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

            normalised_qty = normalise_quantity(quantity)
            if product_id in (None, "") or normalised_qty <= 0:
                error_message = (
                    f"Ligne {getattr(row, 'Index', '?') + 1 if hasattr(row, 'Index') else '?'} invalide (produit ou quantité)"
                )
                summary["errors"].append(error_message)
                span.add_event("invalid_row", {"error": error_message})
                continue

            payloads.append(
                {
                    "pid": int(product_id),
                    "qty": normalised_qty,
                    "source": source_label,
                    "type": safe_type,
                    "date_mvt": reception_date,
                }
            )

        span.set_attribute("imports.payloads", len(payloads))
        if not payloads:
            span.set_attribute("imports.status", "no_payloads")
            return summary

        insert_sql = text(
            """
            INSERT INTO mouvements_stock (produit_id, type, quantite, source, date_mvt)
            VALUES (:pid, :type, :qty, :source, COALESCE(:date_mvt, now()))
            """
        )

        eng = get_engine()
        try:
            with tracer.start_as_current_span("imports.persist_movements"):
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

                    conn.execute(insert_sql, payloads)

                    if not has_stock_trigger:
                        update_sql = text(
                            """
                            UPDATE produits
                            SET stock_actuel = COALESCE(stock_actuel, 0) + :delta,
                                updated_at = now()
                            WHERE id = :pid
                            """
                        )

                        for payload in payloads:
                            movement_type = str(payload.get("type", "")).upper()
                            delta = payload["qty"]
                            if movement_type == "SORTIE":
                                delta = -delta

                            conn.execute(
                                update_sql,
                                {
                                    "pid": payload["pid"],
                                    "delta": delta,
                                },
                            )
        except sa_exc.IntegrityError as exc:
            span.record_exception(exc)
            span.set_attribute("imports.status", "integrity_error")
            summary["errors"].append(f"Erreur d'intégrité lors de l'enregistrement: {exc.orig}")
            return summary
        except Exception as exc:  # pragma: no cover - sécurité runtime
            span.record_exception(exc)
            span.set_attribute("imports.status", "unexpected_error")
            summary["errors"].append(str(exc))
            return summary

        summary["movements_created"] = len(payloads)
        summary["quantity_total"] = float(sum(item["qty"] for item in payloads))
        span.set_attribute("imports.status", "success")
        span.set_attribute("imports.movements_created", summary["movements_created"])
        span.set_attribute("imports.quantity_total", summary["quantity_total"])
        return summary

# Ajoutez d'autres fonctions de service ici (ex: adjust_stock, create_product_with_barcode)
