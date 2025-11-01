# Personas, parcours cibles et wireframes

## Personas priorisés

### 1. Sofia, responsable de rayon
- **Objectifs** : fiabiliser l'inventaire, commander les ruptures rapidement, suivre les performances par catégorie.
- **Freins actuels** : navigation éclatée entre inventaire et commandes, fiches produit peu renseignées, manque de feedback sur les actions.
- **Attentes** : tableaux filtrables, indicateurs de stock en temps réel, possibilité d'épingler des listes.

### 2. Karim, préparateur de commandes
- **Objectifs** : consulter les paniers clients, préparer les colis sans erreur, signaler les substitutions.
- **Freins actuels** : pas de résumé panier accessible, boutons peu lisibles sur mobile, actions multi-étapes.
- **Attentes** : interface épurée, regroupement des tâches du jour, mode mobile/lecteur de codes-barres.

### 3. Lila, cliente fidélisée
- **Objectifs** : retrouver ses produits favoris, profiter des promos, suivre ses commandes.
- **Freins actuels** : CTA en anglais, manque d'historique détaillé, carrousels difficiles à manipuler sur smartphone.
- **Attentes** : recommandations personnalisées, parcours panier simplifié, suivi en temps réel.

## Parcours cibles

| Persona | Parcours clé | Étapes | Points de contrôle UX |
|---------|--------------|--------|------------------------|
| Sofia | Gestion inventaire | (1) Accès tableau inventaire → (2) Filtre par rupture → (3) Création commande fournisseur | Affichage densifié, filtres persistants, export CSV rapide |
| Karim | Préparation commandes | (1) Connexion → (2) Liste commandes du jour → (3) Consultation panier → (4) Validation préparation | Boutons tactiles > 44px, code couleur statut, mode hors-ligne |
| Lila | Achat express | (1) Recherche → (2) Ajout panier → (3) Vérification panier → (4) Paiement | Moteur suggéré, confirmation visuelle, étapes claires |

## Wireframes haute-fidélité

Les wireframes ont été réalisés dans Figma (fichier `Inventaire-Epicerie v2`) et couvrent les écrans suivants :

1. **Inventaire (desktop)** :
   - Barre supérieure avec recherche, filtres sauvegardés et indicateur de rupture.
   - Tableau avec colonnes personnalisables (stock actuel, seuil, prochaine livraison) et badges d'état.
   - Panneau latéral "Détails" affichant graphique d'historique et actions rapides (commander, ajuster stock).

2. **Panier (desktop & mobile)** :
   - Résumé sticky avec total et CTA "Valider ma commande".
   - Liste d'articles regroupée par catégorie, affichant disponibilité et alternatives.
   - Bannière promotionnelle contextuelle liée aux favoris de l'utilisateur.

3. **Administration (desktop)** :
   - Dashboard modulaire : indicateurs (CA, taux rupture, satisfaction) + cartes actions (Importer catalogue, Exporter ventes).
   - Tableau "Tâches" issu du support client, priorisé par SLA.

> **Accès** : https://www.figma.com/file/XXXXX/Inventaire-Epicerie-v2 (placer dans l'espace de travail Equipe Retail).

Chaque wireframe s'appuie sur le design system décrit dans `design-system.md` et expose les états hover/focus, versions dark mode et coupes responsives (≥1440px, 1024px, 768px, 375px).
