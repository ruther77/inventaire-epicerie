"""Services utilitaires pour la gestion des produits et codes-barres."""

from __future__ import annotations

import re
from typing import Any, Iterable, Mapping

from sqlalchemy import text

from data_repository import get_engine
import products_loader


class ProductServiceError(Exception):
    """Exception de base pour les opérations sur les produits."""


class InvalidBarcodeError(ProductServiceError):
    """Levée lorsqu'un code-barres est absent ou mal formé."""


class ProductNotFoundError(ProductServiceError):
    """Levée lorsqu'un produit n'est pas trouvé en base."""


_ALLOWED_NUMERIC_COLUMNS = {"prix_vente", "prix_achat", "tva", "seuil_alerte"}
_ALLOWED_TEXT_COLUMNS = {"nom", "categorie"}
_ALLOWED_BOOL_COLUMNS = {"actif"}
_BARCODE_STATUS_MAP = {"added": "added", "skipped": "skipped", "conflict": "conflicts"}


def _canonicalize_barcode(code: str | None) -> str | None:
    if code is None:
        return None
    cleaned = re.sub(r"\s+", "", str(code)).strip()
    return cleaned or None


def parse_barcode_input(raw_codes: str | Iterable[str] | None) -> list[str]:
    """Normalise une entrée utilisateur en liste de codes-barres uniques."""

    if raw_codes is None:
        return []

    if isinstance(raw_codes, str):
        parts = re.split(r"[;,\n]+", raw_codes)
    else:
        parts = list(raw_codes)

    results: list[str] = []
    seen: set[str] = set()

    for part in parts:
        canonical = _canonicalize_barcode(part)
        if not canonical:
            continue
        key = canonical.lower()
        if key in seen:
            continue
        seen.add(key)
        results.append(canonical)

    return results


def _coerce_numeric(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError) as exc:  # pragma: no cover - message enrichi pour l'appelant
        raise ValueError(f"Valeur numérique invalide: {value!r}") from exc


def _coerce_text(value: Any, *, field: str) -> str:
    cleaned = str(value or "").strip()
    if not cleaned:
        raise ValueError(f"La colonne '{field}' ne peut pas être vide.")
    return cleaned


def _coerce_bool(value: Any) -> bool | None:
    if value in (None, ""):
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "1", "oui", "on", "actif", "yes"}:
            return True
        if lowered in {"false", "0", "non", "off", "inactif", "no"}:
            return False
    raise ValueError(f"Valeur booléenne invalide: {value!r}")


def update_catalog_entry(
    product_id: int,
    field_changes: Mapping[str, Any] | None,
    barcode_field: str | Iterable[str] | None = None,
) -> dict[str, Any]:
    """Applique les modifications du tableau catalogue à un produit donné."""

    try:
        pid = int(product_id)
    except (TypeError, ValueError) as exc:
        raise ValueError("Identifiant de produit invalide.") from exc

    sanitized_updates: dict[str, Any] = {}
    if field_changes:
        for column, value in field_changes.items():
            if column in _ALLOWED_NUMERIC_COLUMNS:
                sanitized_updates[column] = _coerce_numeric(value)
            elif column in _ALLOWED_TEXT_COLUMNS:
                sanitized_updates[column] = _coerce_text(value, field=column)
            elif column in _ALLOWED_BOOL_COLUMNS:
                sanitized_updates[column] = _coerce_bool(value)

    engine = get_engine()
    with engine.begin() as conn:
        exists = conn.execute(
            text("SELECT 1 FROM produits WHERE id = :pid"),
            {"pid": pid},
        ).scalar()
        if not exists:
            raise ProductNotFoundError(f"Produit ID {pid} introuvable.")

        fields_updated = 0
        if sanitized_updates:
            set_clause = ", ".join(f"{col} = :{col}" for col in sanitized_updates)
            params = dict(sanitized_updates)
            params["pid"] = pid
            conn.execute(
                text(f"UPDATE produits SET {set_clause} WHERE id = :pid"),
                params,
            )
            fields_updated = len(sanitized_updates)

        barcode_summary = {"added": 0, "removed": 0, "skipped": 0, "conflicts": 0}

        if barcode_field is not None:
            desired_codes = parse_barcode_input(barcode_field)
            existing_rows = conn.execute(
                text("SELECT code FROM produits_barcodes WHERE produit_id = :pid"),
                {"pid": pid},
            ).fetchall()
            existing_map = {
                _canonicalize_barcode(row[0] if isinstance(row, tuple) else row.code): (
                    row[0] if isinstance(row, tuple) else row.code
                )
                for row in existing_rows
            }
            existing_keys = {code for code in existing_map.keys() if code}
            desired_keys = {code for code in desired_codes if code}

            to_remove = existing_keys - desired_keys
            to_add = desired_keys - existing_keys

            for canonical in to_remove:
                stored_code = existing_map.get(canonical)
                if not stored_code:
                    continue
                conn.execute(
                    text(
                        "DELETE FROM produits_barcodes "
                        "WHERE produit_id = :pid AND lower(code) = lower(:code)"
                    ),
                    {"pid": pid, "code": stored_code},
                )
                barcode_summary["removed"] += 1

            for code in desired_codes:
                if code not in to_add:
                    continue
                status = products_loader.insert_or_update_barcode(conn, pid, code)
                summary_key = _BARCODE_STATUS_MAP.get(status)
                if summary_key:
                    barcode_summary[summary_key] += 1

        return {
            "fields_updated": fields_updated,
            "barcodes": barcode_summary,
        }


def delete_product_by_barcode(raw_code: str | None) -> dict[str, Any]:
    """Supprime un code-barres (ou le produit entier s'il est unique)."""

    canonical = _canonicalize_barcode(raw_code)
    if not canonical or len(canonical) < 8:
        raise InvalidBarcodeError("Code-barres manquant ou trop court.")

    engine = get_engine()
    with engine.begin() as conn:
        row = conn.execute(
            text(
                """
                SELECT pb.produit_id, p.nom,
                       (
                           SELECT COUNT(*)
                           FROM produits_barcodes
                           WHERE produit_id = pb.produit_id
                       ) AS code_count
                FROM produits_barcodes pb
                JOIN produits p ON p.id = pb.produit_id
                WHERE lower(pb.code) = lower(:code)
                LIMIT 1
                """
            ),
            {"code": canonical},
        ).fetchone()

        if row is None:
            raise ProductNotFoundError(
                f"Aucun produit associé au code-barres {canonical}."
            )

        product_id = int(row.produit_id if hasattr(row, "produit_id") else row[0])
        product_name = row.nom if hasattr(row, "nom") else row[1]
        code_count = int(row.code_count if hasattr(row, "code_count") else row[2])

        if code_count > 1:
            conn.execute(
                text(
                    "DELETE FROM produits_barcodes "
                    "WHERE produit_id = :pid AND lower(code) = lower(:code)"
                ),
                {"pid": product_id, "code": canonical},
            )
            return {
                "action": "barcode_removed",
                "product_id": product_id,
                "product_name": product_name,
                "removed_code": canonical,
                "remaining_barcodes": code_count - 1,
            }

        conn.execute(
            text("DELETE FROM produits WHERE id = :pid"),
            {"pid": product_id},
        )
        return {
            "action": "product_deleted",
            "product_id": product_id,
            "product_name": product_name,
            "removed_code": canonical,
            "remaining_barcodes": 0,
        }

