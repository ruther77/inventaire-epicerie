.PHONY: up down rebuild logs psql shell fmt lint test precommit-install

up: ## démarrer tous les services
	docker compose --env-file .env up -d

down: ## arrêter et supprimer (conteneurs/volumes)
	docker compose --env-file .env down -v

rebuild: ## rebuild clean
	docker compose --env-file .env build --no-cache
	docker compose --env-file .env up -d

logs: ## suivre les logs de l'app
	docker compose logs -f app

psql: ## console postgres
	docker compose exec db psql -U postgres -d epicerie

shell: ## shell dans le conteneur app
	docker compose exec app bash || docker compose exec app sh

fmt: ## format (black + ruff --fix)
	docker compose run --rm app bash -lc "python -m pip install -q black ruff && black . && ruff check . --fix || true"

lint: ## lint (ruff)
	docker compose run --rm app bash -lc "python -m pip install -q ruff && ruff check ."

test: ## placeholder tests
	@echo 'Aucun test défini pour le moment.'

precommit-install:
	python -m pip install -q pre-commit
	pre-commit install

# ----- Production helpers -----
prod-up: ## lancer le stack de prod (derrière Caddy)
	docker compose --env-file .env.prod -f docker-compose.prod.yml up -d

prod-down: ## arrêter et supprimer la prod
	docker compose --env-file .env.prod -f docker-compose.prod.yml down -v

prod-rebuild: ## rebuild + up (prod)
	docker compose --env-file .env.prod -f docker-compose.prod.yml build --no-cache
	docker compose --env-file .env.prod -f docker-compose.prod.yml up -d


# ... (Contenu existant) ...

import-data: ## Importer les produits (utilise Produit.csv par défaut)
	@echo "Lancement de l'importation de Produit.csv avec prix d'achat par défaut de 0.5..."
	docker compose exec app python3 products_loader.py Produit.csv
	@echo "Importation terminée. Redémarrez le conteneur 'app' ou videz le cache Streamlit si l'affichage n'est pas à jour."
