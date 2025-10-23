# ==========================
#  Makefile - Inventaire Épicerie
# ==========================

APP_NAME = inventaire
DOCKER_COMPOSE = docker compose

# ==========================
# Commandes principales
# ==========================

# ⚙️ Démarrer les conteneurs (app + db)
up:
	$(DOCKER_COMPOSE) up -d

# 🛑 Arrêter les conteneurs
down:
	$(DOCKER_COMPOSE) down

# 🔁 Restart rapide sans rebuild
restart:
	$(DOCKER_COMPOSE) restart

# 🧹 Supprimer tout (conteneurs, volumes, images non utilisées)
clean:
	$(DOCKER_COMPOSE) down -v --remove-orphans
	docker system prune -f

# 🧩 Rebuild complet de l'environnement (images + dépendances)
build:
	$(DOCKER_COMPOSE) build --no-cache

# 🔄 Refresh complet : rebuild + recréation DB + lancement app
refresh: clean build up
	@echo "✅ Environnement Docker entièrement reconstruit."

# 🧰 Initialisation manuelle de la base (si besoin)
init-db:
	@echo "🚀 Initialisation de la base PostgreSQL..."
	@docker exec -i inventaire-db psql -U postgres -d epicerie < ./db/init.sql
	@echo "✅ Base de données mise à jour."

# 📋 Logs temps réel
logs:
	$(DOCKER_COMPOSE) logs -f

# 📋 Logs app uniquement
logs-app:
	$(DOCKER_COMPOSE) logs -f app

# 📋 Logs db uniquement
logs-db:
	$(DOCKER_COMPOSE) logs -f db

# 🧪 Lancer le conteneur Streamlit localement (hors Docker)
run-local:
	streamlit run app/app.py

# ==========================
# Utilitaires
# ==========================

# 🔍 Vérifier l'état des conteneurs
status:
	$(DOCKER_COMPOSE) ps

# 🔍 Liste des tables dans la DB
tables:
	@docker exec inventaire-db psql -U postgres -d epicerie -c "\dt"

# 🔍 Liste des vues dans la DB
views:
	@docker exec inventaire-db psql -U postgres -d epicerie -c "\dv"

# 📦 Backup base de données
backup-db:
	@mkdir -p backups
	@docker exec inventaire-db pg_dump -U postgres -d epicerie > backups/backup_$$(date +%F_%H-%M).sql
	@echo "💾 Sauvegarde créée dans ./backups/"

# ♻️ Restaurer une sauvegarde
restore-db:
	@if [ -z "$(file)" ]; then echo "❌ Utilisation : make restore-db file=backups/nom_dump.sql"; exit 1; fi
	@docker exec -i inventaire-db psql -U postgres -d epicerie < $(file)
	@echo "✅ Base restaurée à partir de $(file)"

# 🧪 Test connexion DB
test-db:
	@docker exec inventaire-db psql -U postgres -d epicerie -c "SELECT version();"
