# inventory_service.py
from data_repository import get_engine
from sqlalchemy import text, exc as sa_exc

def process_sale_transaction(cart: list, username: str) -> bool:
    """
    Traite une transaction de vente complète en utilisant l'exécution en lot.
    Retourne True si la transaction est réussie, False sinon.
    """
    if not cart:
        return False

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

            for item in cart:
                qty = float(item.get('qty', 0) or 0)
                if qty <= 0:
                    continue

                pid = int(item['id'])

                stock_row = conn.execute(
                    text("SELECT stock_actuel FROM produits WHERE id = :pid FOR UPDATE"),
                    {"pid": pid},
                ).fetchone()

                if stock_row is None:
                    raise ValueError(f"Produit introuvable (id={pid})")

                current_stock = float(stock_row[0] or 0)
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
                    {"pid": pid, "qty": qty, "source": f"Vente par {username}"},
                )

        return True

    except (sa_exc.IntegrityError, ValueError) as e:
        print(f"Erreur d'intégrité BDD lors de la vente: {e}")
        return False
    except Exception as e:
        print(f"Erreur transactionnelle lors de la vente: {e}")
        return False

# Ajoutez d'autres fonctions de service ici (ex: adjust_stock, create_product_with_barcode)
