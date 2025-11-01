# Inventaire Mobile (Android)

Cette application Android en Kotlin permet de consommer l'API FastAPI existante afin de consulter l'inventaire depuis un smartphone.

## Fonctionnalités

- Écran de connexion avec authentification via `/auth/login`.
- Récupération de la liste des produits actifs via `/products`.
- Rafraîchissement manuel de l'inventaire et déconnexion.
- Interface Jetpack Compose respectant la charte "Atlas" (palette verte) et adaptée aux écrans tactiles.

## Pré-requis

- Android Studio Flamingo ou plus récent.
- JDK 17.
- Une instance de l'API FastAPI disponible (par défaut `http://10.0.2.2:8000`).

## Lancement

1. Ouvrir le dossier `mobile/android` dans Android Studio.
2. Si nécessaire, exécuter la tâche `gradle wrapper` (`gradle wrapper --gradle-version 8.2.1`) afin de générer les scripts `./gradlew`.
3. Démarrer l'API (`make api` ou `uvicorn api_server:app --reload`).
4. Lancer l'application sur un émulateur ou un appareil physique. L'adresse `10.0.2.2` correspond au `localhost` de la machine hôte pour les émulateurs Android.

Pour utiliser un serveur distant, modifier `ApiConfig.DEFAULT_BASE_URL` dans `app/src/main/java/com/inventaire/mobile/data/InventoryRepository.kt`.
