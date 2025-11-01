# Règles métier pour les expériences différenciées

Ce document décrit des propositions de règles métier permettant de décliner des expériences distinctes selon les rôles utilisateurs au sein de la plateforme Inventaire-Épicerie. Elles s'appuient sur l'infrastructure existante d'authentification JWT et de gestion des rôles.

## Rôle Administrateur
- **Gestion du catalogue** : création, modification, publication et dépublication de fiches produits, y compris l'import en masse et la mise à jour des stocks.
- **Modération des contenus** : validation et suppression de contenus générés par les utilisateurs (avis, questions, listes publiques), avec journalisation des décisions.
- **Supervision des médias** : contrôle des assets multimédias (images, vidéos, fiches techniques) et définition des normes de qualité.
- **Pilotage promotionnel** : configuration des campagnes commerciales (promotions, bundles, codes promo) et simulation des impacts sur le panier.
- **Administration des comptes** : gestion des droits des autres utilisateurs, suspension de comptes et suivi des logs d'accès sensibles.

## Rôle Gestionnaire Catalogue
- **Curation avancée** : proposition d'assortiments thématiques, ordonnancement des catégories, mise en avant d'offres sponsorisées.
- **Qualité des données** : validation de la cohérence des attributs produits (allergènes, composition, dimensions) et déclenchement d'alertes en cas d'anomalies.
- **Workflow média** : upload et association des médias aux fiches produits avec contrôle du respect des droits d'utilisation.

## Rôle Support/Modérateur
- **Traitement des signalements** : revue des contenus rapportés par les utilisateurs, décision de publication ou retrait, et notification des parties prenantes.
- **Gestion des litiges** : interface pour suivre les litiges liés aux commandes, remboursements et retours.
- **Communication proactive** : envoi de messages ciblés (emails, notifications) pour informer les utilisateurs des décisions prises.

## Rôle Utilisateur Standard
- **Parcours front-office** : navigation dans le catalogue, gestion du panier, passage de commande et suivi de livraison.
- **Contenus communautaires** : possibilité de laisser des avis, poser des questions, créer des listes partagées sous réserve de modération.
- **Personnalisation** : accès à des recommandations basées sur l'historique, sauvegarde de recherches et abonnements à des alertes.

## Rôle Créateur/Partenaire
- **Portail de contribution** : upload de produits ou contenus sponsorisés soumis à validation par l'équipe interne.
- **Tableau de bord de performance** : consultation des statistiques de vues, clics et conversions sur leurs contenus.
- **Outils marketing** : configuration de campagnes ciblées, codes promotionnels dédiés et suivi des paiements.

## Règles transverses
- **Traçabilité** : chaque action sensible déclenche un enregistrement horodaté associé à l'identité de l'utilisateur et à son rôle.
- **Approche progressive** : l'accès à certaines fonctionnalités avancées peut nécessiter une validation manuelle ou le respect de critères (ancienneté, conformité).
- **Expérience adaptée** : les interfaces présentent uniquement les modules pertinents pour le rôle actif, afin de limiter la complexité perçue.

Ces règles peuvent servir de base pour rapprocher l'expérience d'une plateforme de type YouTube (modération, publication de contenus) ou Amazon (gestion de catalogues riches, partenariats marchands).
