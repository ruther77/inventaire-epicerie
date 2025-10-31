# inventaire-epicerie

Application Streamlit pour la gestion d'inventaire d'une épicerie, avec
chargement des produits depuis des fichiers CSV, suivi des ventes et tableau de
bord interactif. Une API FastAPI et une interface React monopage complètent
désormais l'application historique pour amorcer la migration vers une SPA.

## État du projet

* **Tests automatisés :** `pytest` couvre les services d'accès aux données, le
  chargeur de produits, les extracteurs de factures ainsi que les conversions
  utilitaires utilisées par l'application principale.
* **Interface :** la feuille de style `style.css` applique une palette plus
  douce et chaleureuse à l'ensemble des composants Streamlit, et le fichier
  `.streamlit/config.toml` force l'utilisation du thème clair sur tous les
  environnements d'exécution.
* **SPA React :** le dossier `frontend/` contient une application Vite + React
  avec un router, un PoS minimal et une page dédiée aux outils Streamlit
  conservés temporairement via une iframe.
* **API REST :** `backend/main.py` expose un service FastAPI (`/health`,
  `/products`, `/inventory/summary`, `/pos/checkout`, `/products/{id}`) qui
  encapsule la logique métier existante.
* **Workflows avancés :** les onglets _Plan d'approvisionnement dynamique_,
  _Audit & résolution d'écarts_, _Factures → Commandes_, _Qualité catalogue &
  codes-barres_ et _Sauvegardes & reprise d'activité_ embarquent des vues
  orientées actions : calculs de couverture et propositions de commandes,
  assignation des écarts avec export CSV, rapprochement factures / réceptions,
  gouvernance des codes-barres et supervision des sauvegardes.

Pour vérifier localement que tout fonctionne, installez d'abord les
dépendances de développement puis lancez la suite de tests :

```bash
pip install -r requirements-dev.txt
pytest
```

## Démarrer l'application

### Vérifier votre version locale

Toutes les commandes `git` ci-dessous sont à exécuter dans un terminal ouvert
à la racine du dépôt cloné (le dossier `inventaire-epicerie`) **sans** les
préfixer par `docker`. Elles fonctionnent aussi bien sur l'hôte que dans un
shell ouvert via `make shell`.

1. Afficher la branche active et l'état des fichiers :

   ```bash
   git status -sb
   ```

2. Mettre à jour les références distantes puis comparer avec la branche
   distante suivie (ici `origin/work`) :

   ```bash
   git fetch origin
   git log --oneline HEAD..origin/work
   ```

3. Si vous souhaitez aligner votre copie locale sur la branche distante :

   ```bash
   git pull --ff-only
   ```

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
   L'API FastAPI écoute par défaut sur `http://localhost:8000` (commande
   `uvicorn backend.main:app --reload`), et le front-end React sur
   `http://localhost:5173` (`npm install && npm run dev` depuis `frontend/`).
4. Pour arrêter et nettoyer les conteneurs :

   ```bash
   make down
   ```

#### Mettre à jour le conteneur `app`

Lorsque vous modifiez le code Python ou les assets Streamlit, enregistrez vos
fichiers puis rechargez simplement la page : grâce au montage du dossier du
projet, la vue <http://localhost:8501> reflète immédiatement vos changements.

En revanche, les environnements sans montage (production, CI, export d'une
image) doivent être reconstruits pour embarquer les nouveaux fichiers :

```bash
make rebuild          # reconstruit l'image puis relance les services
docker compose up --build app  # alternative équivalente
```

Cela garantit que le conteneur dispose bien des utilitaires comme
`invoice_extractor.py` ou `cart_normalizer.py`, et évite tout décalage entre
l'affichage local et l'image exécutée en production.

### En local (hors Docker)

1. Créez et activez un environnement virtuel Python 3.11. Sur Debian/Ubuntu
   récents (PEP 668), évitez l'option `--break-system-packages` et préférez un
   environnement isolé :

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   ```

2. Installez les dépendances applicatives et de test :

   ```bash
   pip install -r requirements-dev.txt
   ```

   (Ce fichier inclut `requirements.txt` et ajoute les outils de test comme
   `pytest`.)

3. Exportez les variables d'environnement nécessaires (voir `env.prod.example`
   pour la liste complète) ou créez un fichier `.streamlit/secrets.toml`.
4. Démarrez l'application puis ouvrez votre navigateur sur
   <http://localhost:8501> :

   ```bash
   streamlit run app.py
   ```

5. Dans un autre terminal, démarrez l'API puis la SPA :

   ```bash
   uvicorn backend.main:app --reload --port 8000
   cd frontend && npm install && npm run dev
   ```

   La SPA est disponible sur <http://localhost:5173> et communique avec
   l'ancienne application via l'iframe « Outils Streamlit » tant que certaines
   fonctionnalités n'ont pas été portées.

### Importer des produits

Un Makefile facilite l'import CSV :

```bash
make import-data
```

Par défaut, le fichier `Produit.csv` sera chargé et les codes barres seront
enregistrés. Redémarrez ensuite l'application ou videz le cache Streamlit pour
voir les nouveaux produits.

### Sauvegardes PostgreSQL & onglet Maintenance

L'onglet **Maintenance (Admin)** de l'application affiche maintenant un
diagnostic des utilitaires PostgreSQL attendus (`pg_dump` et `psql`). Pour que
les boutons de sauvegarde/restauration fonctionnent :

1. Assurez-vous que le client PostgreSQL est installé sur la machine qui
   exécute Streamlit. Sous Debian/Ubuntu la commande suivante suffit en général
   (exécutez-la depuis l'hôte ou le conteneur concerné) :

   ```bash
   sudo apt-get update
   sudo apt-get install postgresql-client
   ```

   Dans certains environnements, des variables `http_proxy`/`https_proxy`
   héritées peuvent forcer l'utilisation d'un proxy inaccessible et provoquer
   des erreurs `403 Forbidden`. Relancez alors la commande en désactivant ces
   variables :

   ```bash
   sudo env -u http_proxy -u https_proxy apt-get update
   sudo env -u http_proxy -u https_proxy apt-get install postgresql-client
   ```

2. Vérifiez que l'utilisateur système qui exécute Streamlit dispose des
   binaires dans son `PATH`. Si ce n'est pas le cas, configurez explicitement
   les chemins via les variables d'environnement `PG_DUMP_PATH` et `PSQL_PATH`
   (par exemple `/usr/lib/postgresql/16/bin/pg_dump`).

3. Une fois les utilitaires détectés, l'onglet Maintenance expose :
   - le statut courant de chaque binaire (✅ disponible ou ❌ introuvable),
   - la liste des sauvegardes existantes avec téléchargement, restauration ou
     suppression,
   - des messages d'aide si un prérequis manque.

Le dossier de sauvegarde par défaut est `backups/` (ou `/app/backups` en
production). Adaptez la variable `BACKUP_DIR` si besoin pour pointer vers un
volume persistant.
