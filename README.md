# inventaire-epicerie

Application Streamlit pour la gestion d'inventaire d'une épicerie, avec
chargement des produits depuis des fichiers CSV, suivi des ventes et tableau de
bord interactif.

## État du projet

* **Tests automatisés :** `pytest` couvre les services d'accès aux données, le
  chargeur de produits, les extracteurs de factures ainsi que les conversions
  utilitaires utilisées par l'application principale.
* **Interface :** la feuille de style `style.css` applique une palette plus
  douce et chaleureuse à l'ensemble des composants Streamlit.

Pour vérifier localement que tout fonctionne, exécutez simplement :

```bash
pytest
```

## Démarrer l'application

### Avec Docker (recommandé)

1. Créez un fichier `.env` à partir de `env.prod.example` en adaptant les
   valeurs si nécessaire.
2. Lancez la stack :

   ```bash
   make up
   ```

3. Dès que les conteneurs sont démarrés, ouvrez un navigateur sur
   <http://localhost:8501> pour accéder à l'application Streamlit. La base
   PostgreSQL est exposée sur le port 5432 (définis dans `docker-compose.yml`).
4. Pour arrêter et nettoyer les conteneurs :

   ```bash
   make down
   ```

### En local (hors Docker)

1. Créez et activez un environnement virtuel Python 3.11.
2. Installez les dépendances :

   ```bash
   pip install -r requirements.txt
   ```

3. Exportez les variables d'environnement nécessaires (voir `env.prod.example`
   pour la liste complète) ou créez un fichier `.streamlit/secrets.toml`.
4. Démarrez l'application puis ouvrez votre navigateur sur
   <http://localhost:8501> :

   ```bash
   streamlit run app.py
   ```

### Importer des produits

Un Makefile facilite l'import CSV :

```bash
make import-data
```

Par défaut, le fichier `Produit.csv` sera chargé et les codes barres seront
enregistrés. Redémarrez ensuite l'application ou videz le cache Streamlit pour
voir les nouveaux produits.
