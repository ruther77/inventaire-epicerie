# inventory_service.py
from collections import defaultdict
from decimal import Decimal, InvalidOperation
from typing import Iterable

from data_repository import get_engine
from sqlalchemy import text, exc as sa_exc


def _normalise_quantity(raw_qty) -> Decimal:
    """Convertit n'importe quelle valeur numérique en Decimal positif."""
    if raw_qty is None:
        return Decimal("0")

    if isinstance(raw_qty, Decimal):
        return raw_qty

    try:
        return Decimal(str(raw_qty))
    except (InvalidOperation, ValueError, TypeError):
        return Decimal("0")


def _aggregate_cart(cart: Iterable[dict]) -> dict[int, Decimal]:
    """Fusionne les lignes de panier par produit et retourne {produit_id: quantite}."""
    aggregated: dict[int, Decimal] = defaultdict(lambda: Decimal("0"))

    for item in cart:
        try:
            pid = int(item.get("id"))
        except (TypeError, ValueError):
            continue

        qty = _normalise_quantity(item.get("qty"))
        if qty <= 0:
            continue

        aggregated[pid] += qty

    return {pid: qty for pid, qty in aggregated.items() if qty > 0}


def process_sale_transaction(cart: list, username: str) -> tuple[bool, str]:
    """Valide le panier, débite le stock et journalise les sorties."""

    aggregated_cart = _aggregate_cart(cart)
    if not aggregated_cart:
        return False, "Aucun article valide dans le panier."

    user_label = username or "inconnu"

    try:
        eng = get_engine()
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

            for pid, qty in aggregated_cart.items():
                stock_row = conn.execute(
                    text("SELECT stock_actuel FROM produits WHERE id = :pid FOR UPDATE"),
                    {"pid": pid},
                ).fetchone()

                if stock_row is None:
                    raise ValueError(f"Produit introuvable (id={pid})")

                current_stock = _normalise_quantity(stock_row[0])
                if current_stock < qty:
                    raise ValueError(
                        f"Stock insuffisant pour le produit {pid}: {current_stock} < {qty}"
                    )

                if not has_stock_trigger:
                    conn.execute(
                        text(
                            """
                            UPDATE produits
                            SET stock_actuel = stock_actuel - :qty,
                                updated_at = now()
                            WHERE id = :pid
                            """
                        ),
                        {"pid": pid, "qty": qty},
                    )

                conn.execute(
                    text(
                        """
                        INSERT INTO mouvements_stock (produit_id, type, quantite, source)
                        VALUES (:pid, 'SORTIE', :qty, :source)
                        """
                    ),
                    {
                        "pid": pid,
                        "qty": qty,
                        "source": f"Vente par {user_label}",
                    },
                )

        return True, f"{len(aggregated_cart)} mouvement(s) enregistré(s)."

    except (sa_exc.IntegrityError, ValueError) as e:
        return False, str(e)
    except Exception as e:
        return False, f"Erreur transactionnelle lors de la vente: {e}"

# Ajoutez d'autres fonctions de service ici (ex: adjust_stock, create_product_with_barcode)
