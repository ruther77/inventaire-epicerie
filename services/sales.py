from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import logging
import os
from typing import Callable, Iterable

from sqlalchemy import exc as sa_exc
from sqlalchemy import text
from sqlalchemy.engine import Engine

from telemetry import get_tracer, instrument_sqlalchemy_engine


logger = logging.getLogger(__name__)


@dataclass
class SaleDatabaseProfile:
    """Represents the database-specific behaviours required by the sale flow."""

    dialect: str
    has_stock_trigger: bool
    stock_lock_sql: str
    manual_stock_update_sql: str

    @property
    def requires_manual_stock_update(self) -> bool:
        return not self.has_stock_trigger


@dataclass
class SaleService:
    """Encapsulates the business rules for recording a sale transaction."""

    engine_factory: Callable[[], Engine]
    tracer_name: str = "services.sales"
    _tracer: object = field(init=False, repr=False)
    _db_profile: SaleDatabaseProfile = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._tracer = get_tracer(self.tracer_name)
        self._db_profile = self._initialise_database_profile()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def process_sale_transaction(
        self, cart: Iterable[dict], username: str | None
    ) -> tuple[bool, str | None, dict[str, bytes] | None]:
        """Persist a sale, decrement stock and return an optional receipt."""

        items = list(cart or [])
        with self._tracer.start_as_current_span("process_sale_transaction") as span:
            span.set_attribute("sale.username", username or "")
            span.set_attribute("sale.cart_length", len(items))

            if not items:
                span.set_attribute("sale.status", "empty_cart")
                return False, "Le panier est vide, aucune vente n'a été effectuée.", None

            aggregated = self._aggregate_cart(items)
            if not aggregated:
                span.set_attribute("sale.status", "empty_after_normalization")
                return False, "Toutes les lignes du panier ont une quantité nulle.", None

            engine = self.engine_factory()
            instrument_sqlalchemy_engine(engine)

            try:
                with engine.begin() as conn:
                    missing_products: list[int] = []
                    insufficient: list[str] = []

                    for pid, item in aggregated.items():
                        with self._tracer.start_as_current_span("sale.check_stock") as check_span:
                            check_span.set_attribute("sale.product_id", pid)
                            stock_row = conn.execute(
                                text(self._db_profile.stock_lock_sql),
                                {"pid": pid},
                            ).fetchone()

                            if stock_row is None:
                                missing_products.append(pid)
                                check_span.set_attribute("sale.stock_status", "missing")
                                continue

                            current_stock = Decimal(str(stock_row[0] or 0))
                            check_span.set_attribute("sale.stock_current", float(current_stock))
                            check_span.set_attribute("sale.stock_requested", float(item["qty"]))

                            if current_stock < item["qty"]:
                                insufficient.append(
                                    f"{item['label']} (stock {current_stock} < vente {item['qty']})"
                                )
                                check_span.set_attribute("sale.stock_status", "insufficient")
                            else:
                                check_span.set_attribute("sale.stock_status", "ok")

                    if missing_products:
                        span.set_attribute("sale.status", "missing_products")
                        span.set_attribute("sale.missing_count", len(missing_products))
                        return (
                            False,
                            f"Produits introuvables: {', '.join(map(str, missing_products))}.",
                            None,
                        )

                    if insufficient:
                        span.set_attribute("sale.status", "insufficient_stock")
                        span.set_attribute("sale.insufficient_count", len(insufficient))
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

                    if self._db_profile.requires_manual_stock_update:
                        update_statement = text(
                            self._db_profile.manual_stock_update_sql
                        )
                        for payload in movements_payload:
                            conn.execute(
                                update_statement,
                                payload,
                            )

                receipt = self._build_sale_receipt(aggregated, username)
                span.set_attribute("sale.status", "success")
                return True, None, receipt

            except sa_exc.IntegrityError as exc:
                logger.exception("Integrity error while processing sale", exc_info=exc)
                span.record_exception(exc)
                span.set_attribute("sale.status", "integrity_error")
                return (
                    False,
                    f"Erreur d'intégrité lors de l'enregistrement de la vente: {exc.orig}",
                    None,
                )
            except Exception as exc:  # pragma: no cover - defensive
                logger.exception("Unexpected error during sale transaction", exc_info=exc)
                span.record_exception(exc)
                span.set_attribute("sale.status", "unexpected_error")
                return False, f"Erreur inattendue lors de la vente: {exc}", None

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _aggregate_cart(self, items: Iterable[dict]) -> dict[int, dict[str, Decimal | str]]:
        aggregated: dict[int, dict[str, Decimal | str]] = defaultdict(
            lambda: {
                "qty": Decimal("0"),
                "label": None,
                "unit_price": Decimal("0"),
                "tva_rate": Decimal("0"),
            }
        )

        with self._tracer.start_as_current_span("sale.aggregate_cart") as aggregate_span:
            for raw_item in items:
                try:
                    pid = int(raw_item["id"])
                except (KeyError, TypeError, ValueError):
                    aggregate_span.set_attribute("sale.aggregate_error", "invalid_product_id")
                    return {}

                qty = normalise_quantity(raw_item.get("qty"))
                if qty <= 0:
                    continue

                aggregated_item = aggregated[pid]
                aggregated_item["qty"] = aggregated_item["qty"] + qty
                aggregated_item["label"] = raw_item.get("nom") or f"Produit {pid}"

                unit_price = as_decimal(raw_item.get("prix_vente"))
                tva_rate = as_decimal(raw_item.get("tva"))

                if aggregated_item["unit_price"] == 0 and unit_price > 0:
                    aggregated_item["unit_price"] = unit_price

                if aggregated_item["tva_rate"] == 0 and tva_rate >= 0:
                    aggregated_item["tva_rate"] = tva_rate

            aggregate_span.set_attribute("sale.distinct_products", len(aggregated))

        return aggregated

    def _build_sale_receipt(
        self, aggregated: dict[int, dict[str, Decimal | str]], username: str | None
    ) -> dict[str, bytes]:
        timestamp = datetime.now()
        with self._tracer.start_as_current_span("sale.build_receipt"):
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
                unit_price = as_decimal(item.get("unit_price"), "0")
                tva_rate = as_decimal(item.get("tva_rate"), "0")

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

                unit_display = (
                    (line_total / qty).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                    if qty
                    else Decimal("0")
                )
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

    # ------------------------------------------------------------------
    # Database configuration helpers
    # ------------------------------------------------------------------
    def _initialise_database_profile(self) -> SaleDatabaseProfile:
        """Inspect the configured engine and determine DB-specific behaviour."""

        try:
            engine = self.engine_factory()
        except Exception as exc:  # pragma: no cover - defensive
            logger.exception("Unable to create engine for sale service", exc_info=exc)
            return self._default_db_profile("unknown")

        dialect = (engine.dialect.name or "unknown").lower()
        feature_flag = os.getenv("SALE_DISABLE_STOCK_TRIGGER", "").lower() in {
            "1",
            "true",
            "yes",
        }

        has_stock_trigger = False
        if not feature_flag:
            has_stock_trigger = self._verify_stock_trigger(engine, dialect)
        else:
            logger.info(
                "Stock trigger usage disabled via SALE_DISABLE_STOCK_TRIGGER feature flag"
            )

        stock_lock_sql = self._determine_stock_lock_sql(engine)
        manual_update_sql = self._determine_manual_update_sql()

        logger.info(
            "SaleService database profile initialised", extra={
                "dialect": dialect,
                "has_stock_trigger": has_stock_trigger,
                "stock_lock_sql": stock_lock_sql,
                "manual_update_sql": manual_update_sql,
            }
        )

        return SaleDatabaseProfile(
            dialect=dialect,
            has_stock_trigger=has_stock_trigger,
            stock_lock_sql=stock_lock_sql,
            manual_stock_update_sql=manual_update_sql,
        )

    def _verify_stock_trigger(self, engine: Engine, dialect: str) -> bool:
        if dialect != "postgresql":
            return False

        trigger_query = text(
            """
            SELECT EXISTS (
                SELECT 1
                FROM pg_trigger
                WHERE tgname = 'trg_update_stock_actuel'
                  AND tgrelid = 'mouvements_stock'::regclass
            )
            """
        )

        try:
            with engine.connect() as conn:
                return bool(conn.execute(trigger_query).scalar())
        except sa_exc.SQLAlchemyError as exc:
            logger.warning(
                "Unable to verify PostgreSQL stock trigger, falling back to manual updates",
                exc_info=exc,
            )
            return False

    def _determine_stock_lock_sql(self, engine: Engine) -> str:
        supports_for_update = bool(getattr(engine.dialect, "supports_for_update", False))
        if supports_for_update:
            return "SELECT stock_actuel FROM produits WHERE id = :pid FOR UPDATE"
        return "SELECT stock_actuel FROM produits WHERE id = :pid"

    def _determine_manual_update_sql(self) -> str:
        return (
            "UPDATE produits "
            "SET stock_actuel = stock_actuel - :qty, "
            "updated_at = CURRENT_TIMESTAMP "
            "WHERE id = :pid"
        )

    def _default_db_profile(self, dialect: str) -> SaleDatabaseProfile:
        return SaleDatabaseProfile(
            dialect=dialect,
            has_stock_trigger=False,
            stock_lock_sql="SELECT stock_actuel FROM produits WHERE id = :pid",
            manual_stock_update_sql=self._determine_manual_update_sql(),
        )


# ---------------------------------------------------------------------------
# Utility helpers shared with inventory_service legacy entrypoints
# ---------------------------------------------------------------------------

def as_decimal(value, default: str = "0") -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal(default)


def normalise_quantity(value) -> Decimal:
    try:
        qty = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal("0")

    if qty.is_nan() or qty <= 0:
        return Decimal("0")

    return qty


def _render_receipt_pdf(lines: list[str]) -> bytes:
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


__all__ = ["SaleService", "as_decimal", "normalise_quantity"]
