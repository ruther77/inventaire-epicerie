# api_server.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from db_manager import exec_sql # Assurez-vous que cette fonction est dans db_manager.py
from sqlalchemy import text # N'oubliez pas l'import de text
import os
from dotenv import load_dotenv

# Charger les variables d'environnement si besoin (pour l'URL de la BDD locale)
load_dotenv() 

class StockUpdate(BaseModel):
    product_id: int
    quantity: float
    type: str  # 'ENTREE' ou 'SORTIE'
    source: str = "External API"

app = FastAPI(title="Inventaire API")

@app.post("/stock/update")
def update_stock_external(update: StockUpdate):
    """
    Endpoint pour mettre à jour le stock depuis une source externe.
    Gère les contraintes de quantité et de type.
    """
    if update.type not in ['ENTREE', 'SORTIE']:
        raise HTTPException(status_code=400, detail="Le type doit être 'ENTREE' ou 'SORTIE'.")
    if update.quantity <= 0:
        raise HTTPException(status_code=400, detail="La quantité doit être strictement positive.")
        
    try:
        sql = text("""
            INSERT INTO mouvements_stock (produit_id, type, quantite, source)
            VALUES (:pid, :mvt_type, :qty, :src)
        """)
        
        # Le produit doit exister, sinon une erreur de clé étrangère est levée
        exec_sql(sql.bindparams(
            pid=update.product_id, 
            mvt_type=update.type, 
            qty=update.quantity, 
            src=update.source
        ))
        
        return {"status": "success", "message": f"Mouvement de {update.type} enregistré pour produit {update.product_id}"}
        
    except Exception as e:
        # Gérer l'erreur de produit non trouvé (Foreign Key) ou autre erreur BDD
        print(f"Erreur BDD: {e}")
        raise HTTPException(status_code=500, detail=f"Échec de l'opération BDD. Le produit_id existe-t-il? {e}")

# COMMANDE POUR LANCER L'API : uvicorn api_server:app --reload --port 8000

