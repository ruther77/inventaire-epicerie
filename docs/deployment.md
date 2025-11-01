# Guide de déploiement

Ce document décrit la procédure standardisée pour construire et publier la
plateforme Inventaire Épicerie sur un hébergeur (VPS, PaaS ou Kubernetes).

## 1. Pré-requis

- Docker et Docker Compose v2
- Accès à un registre d'images (GHCR, ECR, etc.)
- Variables d'environnement renseignées dans un fichier `.env` basé sur
  `env.prod.example`
- Base PostgreSQL provisionnée (gérée par Compose ou service managé)

## 2. Construction des images

```bash
docker compose -f docker-compose.prod.yml build
```

L'image résultante `inventaire-app:latest` contient l'application Streamlit,
le backend FastAPI et les tâches périodiques (mode `worker`). Le processus
lancé est déterminé par la variable `APP_PROCESS`.

## 3. Publication dans un registre (optionnel)

```bash
docker tag inventaire-app:latest ghcr.io/ORG/inventaire-app:$(git rev-parse --short HEAD)
docker push ghcr.io/ORG/inventaire-app:$(git rev-parse --short HEAD)
```

## 4. Lancement de la stack

```bash
cp env.prod.example .env
# Adapter ensuite les secrets et URLs
vi .env

docker compose -f docker-compose.prod.yml up -d
```

## 5. Vérifications post-déploiement

1. API : `curl https://api.example.com/health`
2. Streamlit : ouvrir `https://app.example.com`
3. SPA : `https://spa.example.com` (port 4173 en local)
4. Base de données : `psql $DATABASE_URL`

## 6. Intégration continue

Le workflow GitHub Actions `.github/workflows/ci.yml` exécute :

- `pytest` sur les services Python (connexion PostgreSQL éphémère)
- `npm install` + `npm run build` sur le front Vite

Il garantit que la stack reste déployable avant fusion.

## 7. Maintenance

- **Sauvegardes** : le conteneur `backup` du Compose principal reste valable et
  peut être activé en production si nécessaire.
- **Montée de version** : reconstruire l'image, pousser puis relancer le service
  avec `docker compose up -d --force-recreate`.

Pour aller plus loin, vous pouvez brancher la commande `docker compose` sur un
runner CI/CD (GitHub Actions, GitLab CI, etc.) ou traduire la stack en chart
Helm/Kustomize pour Kubernetes.
