# inventory_service.py
from data_repository import exec_sql, query_df # Assumer que db_manager.py est renommé ou importé
from sqlalchemy import text, exc as sa_exc

def process_sale_transaction(cart: list, username: str) -> bool:
    """
    Traite une transaction de vente complète en utilisant l'exécution en lot.
    Retourne True si la transaction est réussie, False sinon.
    """
    if not cart:
        return False

    # 1. Préparation de la liste des mouvements
    movements_list = []
    for item in cart:
        # Stocke le mouvement pour l'exécution en lot (executemany)
        movements_list.append({
            'pid': item['id'], 
            'type': 'SORTIE', 
            'qty': item['qty'], 
            'user': username
        })

    # 2. Requête SQL (elle doit inclure les placeholders nommés)
    sql_mvt = """
        INSERT INTO mouvements_stock (produit_id, type, quantite, source)
        VALUES (:pid, :type, :qty, :user)
    """

    try:
        # 3. Exécution en lot (une seule commande BDD)
        # exec_sql utilise désormais l'exécution en lot car movements_list est une liste
        exec_sql(sql_mvt, movements_list)
        return True
    
    except sa_exc.IntegrityError as e:
        # Erreur spécifique BDD (ex: contrainte de stock négatif si vous ajoutez un CHECK)
        print(f"Erreur d'intégrité BDD lors de la vente: {e}")
        return False
    except Exception as e:
        # Autres erreurs de connexion/transaction
        print(f"Erreur transactionnelle lors de la vente: {e}")
        return False

# Ajoutez d'autres fonctions de service ici (ex: adjust_stock, create_product_with_barcode)
