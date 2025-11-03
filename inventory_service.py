from __future__ import annotations

import logging
import math
from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Iterable, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - typing only
    import pandas as pd

from data_repository import get_engine, query_df
from sqlalchemy import exc as sa_exc, text

from domain.preferences import (
    get_saved_views_service as domain_get_saved_views_service,
    set_saved_views_service as domain_set_saved_views_service,
)
from domain.sales import (
    get_sale_service as domain_get_sale_service,
    process_sale_transaction as domain_process_sale_transaction,
    set_sale_service as domain_set_sale_service,
)
from domain import update_catalog_entry
from services import SaleService, SavedViewsService, as_decimal, normalise_quantity
from telemetry import get_tracer


logger = logging.getLogger(__name__)
tracer = get_tracer(__name__)


def get_sale_service() -> SaleService:
    return domain_get_sale_service()


def set_sale_service(service: SaleService | None) -> None:
    domain_set_sale_service(service)


def get_saved_views_service() -> SavedViewsService:
    return domain_get_saved_views_service()


def set_saved_views_service(service: SavedViewsService | None) -> None:
    domain_set_saved_views_service(service)


def process_sale_transaction(cart: list, username: str) -> tuple[bool, str | None, dict[str, bytes] | None]:
    """Delegate sale processing to the shared domain service."""

    return domain_process_sale_transaction(cart, username)

# ---------------------------------------------------------------------------
#  Pipelines de factures → commandes
# ---------------------------------------------------------------------------


def _require_pandas():
    """Import pandas on demand so that optional features degrade gracefully."""

    try:
        import pandas as pd  # type: ignore
    except ModuleNotFoundError as exc:  # pragma: no cover - environment guard
        message = (
            "pandas is required for invoice import features. "
            "Install it with `pip install pandas` or include it in your environment."
        )
        logger.error(message)
        raise ModuleNotFoundError(message) from exc

    return pd


def match_invoice_products(invoice_df: "pd.DataFrame") -> "pd.DataFrame":
    """Associe les lignes d'une facture aux produits du catalogue via code-barres."""

    empty_columns = [
        "code",
        "produit_id",
        "produit_nom",
        "categorie",
        "prix_achat_catalogue",
        "prix_vente_catalogue",
    ]

    pd = _require_pandas()

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
    invoice_df: "pd.DataFrame",
    *,
    username: str,
    supplier: str | None = None,
    movement_type: str = "ENTREE",
    reception_date: datetime | None = None,
) -> dict[str, object]:
    """Crée des mouvements d'entrée à partir d'une réception de facture."""

    pd = _require_pandas()

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


def prepare_invoice_price_updates(
    invoice_df: "pd.DataFrame",
    *,
    min_margin: float = 0.4,
    delta_threshold: float = 0.1,
) -> dict[str, object]:
    """Return a plan describing catalogue price updates based on an invoice."""

    pd = _require_pandas()

    summary: dict[str, object] = {
        "line_count": 0,
        "matched_line_count": 0,
        "product_count": 0,
        "updates": [],
        "skipped": [],
        "errors": [],
    }

    if not isinstance(invoice_df, pd.DataFrame) or invoice_df.empty:
        return summary

    working_df = invoice_df.copy()
    summary["line_count"] = len(working_df)

    if "codes" not in working_df.columns:
        summary["errors"].append("Colonne 'codes' absente de la facture.")
        return summary

    working_df["_code_lower"] = (
        working_df["codes"].fillna("").astype(str).str.strip().str.lower()
    )
    working_df = working_df[working_df["_code_lower"] != ""]
    if working_df.empty:
        return summary

    try:
        matches_df = match_invoice_products(working_df)
    except Exception as exc:  # pragma: no cover - instrumentation/logging via tracer
        summary["errors"].append(str(exc))
        return summary

    if matches_df.empty:
        return summary

    matches_df = matches_df.copy()
    if "code" not in matches_df.columns:
        summary["errors"].append("Aucun code-barres n'a pu être rapproché.")
        return summary

    matches_df["code"] = matches_df["code"].astype(str).str.strip().str.lower()
    combined_df = working_df.merge(
        matches_df,
        left_on="_code_lower",
        right_on="code",
        how="left",
        suffixes=("", "_catalogue"),
    )

    matched_rows = combined_df[combined_df["produit_id"].notna()].copy()
    summary["matched_line_count"] = int(len(matched_rows))
    if matched_rows.empty:
        return summary

    matched_rows["produit_id"] = matched_rows["produit_id"].astype(int)
    product_ids = sorted(matched_rows["produit_id"].unique().tolist())
    summary["product_count"] = len(product_ids)
    if not product_ids:
        return summary

    placeholders = ", ".join(f":pid{i}" for i, _ in enumerate(product_ids))
    params = {f"pid{i}": pid for i, pid in enumerate(product_ids)}
    price_sql = (
        "SELECT id, COALESCE(prix_achat, 0) AS prix_achat, "
        "COALESCE(prix_vente, 0) AS prix_vente "
        "FROM produits WHERE id IN (" + placeholders + ")"
    )

    price_df = query_df(price_sql, params=params)
    price_map: dict[int, dict[str, float]] = {}
    for row in price_df.to_dict("records"):
        try:
            pid = int(row["id"])
        except (TypeError, ValueError):
            continue
        price_map[pid] = {
            "prix_achat": float(row.get("prix_achat", 0) or 0.0),
            "prix_vente": float(row.get("prix_vente", 0) or 0.0),
        }

    updates: list[dict[str, object]] = []
    skipped: list[dict[str, object]] = []

    quantity_columns = ("quantite_recue", "qte_init", "quantite", "qty")
    unit_price_columns = ("prix_achat_facture", "prix_achat", "prix_vente")
    total_columns = ("montant_total_facture", "montant", "total_ligne")

    for product_id, group in matched_rows.groupby("produit_id", sort=False):
        product_label = ""
        name_candidates = [
            group.get("produit_nom"),
            group.get("catalogue_nom"),
            group.get("nom"),
        ]
        for candidate in name_candidates:
            if candidate is None:
                continue
            if hasattr(candidate, "dropna"):
                cleaned = candidate.dropna()
                if cleaned.empty:
                    continue
                value = str(cleaned.iloc[0]).strip()
            else:
                value = str(candidate or "").strip()
            if value:
                product_label = value
                break

        codes = [str(code).strip() for code in group["codes"].tolist() if str(code).strip()]
        ean = ", ".join(sorted({code for code in codes if code}))

        quantity_series = None
        for column in quantity_columns:
            if column in group.columns:
                series = pd.to_numeric(group[column], errors="coerce").fillna(0.0)
                if series.any():
                    quantity_series = series
                    break
        if quantity_series is None:
            quantity_series = pd.Series([0.0] * len(group))

        total_series = None
        for column in total_columns:
            if column in group.columns:
                series = pd.to_numeric(group[column], errors="coerce").fillna(0.0)
                if series.any():
                    total_series = series
                    break

        unit_series = None
        for column in unit_price_columns:
            if column in group.columns:
                series = pd.to_numeric(group[column], errors="coerce").fillna(0.0)
                if series.any():
                    unit_series = series
                    break
        if unit_series is None:
            unit_series = pd.Series([0.0] * len(group))

        quantity_total = float(quantity_series.sum())
        amount_total = float(total_series.sum()) if total_series is not None else 0.0

        if quantity_total > 0 and amount_total > 0:
            invoice_unit_price = amount_total / quantity_total
        else:
            positive_units = unit_series[unit_series > 0]
            invoice_unit_price = float(positive_units.mean()) if not positive_units.empty else 0.0

        if invoice_unit_price <= 0:
            skipped.append(
                {
                    "product_id": product_id,
                    "product_name": product_label,
                    "ean": ean,
                    "reason": "Prix facture indisponible",
                }
            )
            continue

        current_prices = price_map.get(product_id, {"prix_achat": 0.0, "prix_vente": 0.0})
        current_purchase = float(current_prices.get("prix_achat", 0.0) or 0.0)
        current_sale = float(current_prices.get("prix_vente", 0.0) or 0.0)

        proposed_sale = round(invoice_unit_price * (1.0 + max(min_margin, 0.0)), 2)
        proposed_purchase = round(invoice_unit_price, 4)

        if current_sale <= 0:
            delta_ratio = float("inf")
        else:
            delta_ratio = abs(proposed_sale - current_sale) / max(current_sale, 1e-9)

        should_update = delta_ratio >= max(delta_threshold, 0.0) or current_sale <= 0

        entry = {
            "product_id": int(product_id),
            "product_name": product_label,
            "ean": ean,
            "invoice_unit_price": round(invoice_unit_price, 4),
            "proposed_sale_price": proposed_sale,
            "proposed_purchase_price": proposed_purchase,
            "current_purchase_price": round(current_purchase, 4),
            "current_sale_price": round(current_sale, 2),
            "delta_ratio": float(delta_ratio),
            "delta_percent": (float(delta_ratio) * 100.0 if math.isfinite(delta_ratio) else None),
            "quantity_total": quantity_total,
            "line_count": int(len(group)),
        }

        if should_update:
            updates.append(entry)
        else:
            entry_with_reason = dict(entry)
            entry_with_reason["reason"] = "Delta inférieur au seuil"
            skipped.append(entry_with_reason)

    summary["updates"] = updates
    summary["skipped"] = skipped
    summary["updates_count"] = len(updates)
    summary["skipped_count"] = len(skipped)
    return summary


def apply_invoice_price_updates(
    invoice_df: "pd.DataFrame",
    *,
    min_margin: float = 0.4,
    delta_threshold: float = 0.1,
) -> dict[str, object]:
    """Apply catalogue price updates computed from an invoice."""

    plan = prepare_invoice_price_updates(
        invoice_df,
        min_margin=min_margin,
        delta_threshold=delta_threshold,
    )

    updates = plan.get("updates", []) if isinstance(plan, dict) else []
    applied = 0
    errors: list[str] = []

    for entry in updates:
        product_id = entry.get("product_id")
        proposed_purchase = entry.get("proposed_purchase_price")
        proposed_sale = entry.get("proposed_sale_price")
        if product_id in (None, ""):
            continue
        if proposed_purchase in (None, "") or proposed_sale in (None, ""):
            continue
        try:
            update_catalog_entry(
                int(product_id),
                {
                    "prix_achat": float(proposed_purchase),
                    "prix_vente": float(proposed_sale),
                },
                None,
            )
            applied += 1
        except Exception as exc:  # pragma: no cover - surface détaillée pour l'UI
            errors.append(f"Produit {product_id}: {exc}")

    plan["applied_updates"] = applied
    plan["errors"] = list(plan.get("errors", [])) + errors
    return plan


# Ajoutez d'autres fonctions de service ici (ex: adjust_stock, create_product_with_barcode)
