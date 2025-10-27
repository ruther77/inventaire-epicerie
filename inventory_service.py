# inventory_service.py
from collections import defaultdict
from decimal import Decimal, InvalidOperation

from data_repository import get_engine
from sqlalchemy import text, exc as sa_exc

def _normalise_quantity(value) -> Decimal:
    """Convertit n'importe quelle quantité en Decimal positif."""
    try:
        qty = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal("0")

    if qty.is_nan() or qty <= 0:
        return Decimal("0")

    return qty


def process_sale_transaction(cart: list, username: str) -> tuple[bool, str | None]:
    """Enregistre une vente en décrémentant le stock et en traçant les mouvements.

    Args:
        cart: liste d'articles issus du panier (doit contenir au moins les clés ``id`` et ``qty``).
        username: nom d'utilisateur Streamlit effectuant la vente.

    Returns:
        Tuple (succès, message). En cas d'échec, le message contient le motif.
    """
    if not cart:
        return False, "Le panier est vide, aucune vente n'a été effectuée."

    aggregated: dict[int, dict[str, Decimal | str]] = defaultdict(lambda: {"qty": Decimal("0"), "label": None})

    for raw_item in cart:
        try:
            pid = int(raw_item["id"])
        except (KeyError, TypeError, ValueError):
            return False, "Un article du panier est invalide (identifiant manquant)."

        qty = _normalise_quantity(raw_item.get("qty"))
        if qty <= 0:
            continue

        aggregated_item = aggregated[pid]
        aggregated_item["qty"] = aggregated_item["qty"] + qty
        aggregated_item["label"] = raw_item.get("nom") or f"Produit {pid}"

    if not aggregated:
        return False, "Toutes les lignes du panier ont une quantité nulle."

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
                return False, f"Produits introuvables: {', '.join(map(str, missing_products))}."

            if insufficient:
                return (
                    False,
                    "Stock insuffisant: " + ", ".join(insufficient),
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

        return True, None

    except sa_exc.IntegrityError as exc:
        return False, f"Erreur d'intégrité lors de l'enregistrement de la vente: {exc.orig}"
    except Exception as exc:  # pragma: no cover - sécurité supplémentaire pour la session Streamlit
        return False, f"Erreur inattendue lors de la vente: {exc}"

# Ajoutez d'autres fonctions de service ici (ex: adjust_stock, create_product_with_barcode)
