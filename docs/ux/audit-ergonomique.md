# Audit ergonomique des vues existantes

Cet audit a été réalisé à partir d'une revue approfondie des gabarits PHP et des feuilles de style actuelles (`home.php`, `single-product.php`, `Customer/style.css`). Les constats sont regroupés par thématique et hiérarchisés selon leur impact sur l'expérience utilisateur.

## Navigation & orientation

- **Structure hiérarchique difficile à appréhender** : la navigation principale combine raccourcis, méga-menu et utilitaires sans hiérarchie perceptible ni état actif. Les éléments de `workspace-primary__shortcuts` et `workspace-primary__toggle` sont rendus comme des boutons homogènes, ce qui crée de la surcharge cognitive.【F:header.php†L235-L336】
- **Absence d'indicateur de page active** : aucune classe `aria-current` ou style dédié ne permet de signaler la vue courante, obligeant l'utilisateur à se repérer visuellement dans la page.【F:header.php†L235-L336】
- **Navigation secondaire cachée** : les liens d'accès direct aux catégories ne sont visibles qu'après interaction dans le méga-menu, ce qui freine la découverte des sections métier prioritaires (Inventaire, Commandes, Administration).【F:header.php†L312-L336】

## Contenu & lisibilité

- **Ton éditorial inconstant** : alternance entre français et anglais dans les CTA et contenus (ex. "Add to Cart", "Price") sur la fiche produit.【F:single-product.php†L53-L118】
- **Textes descriptifs lacunaires** : plusieurs champs sont vides (description, caractéristiques), ce qui empêche l'utilisateur de confirmer son choix et allonge la prise de décision.【F:single-product.php†L53-L118】
- **Cartes produits surchargées** : la section "Produits populaires" réutilise le composant carousel sans hiérarchie visuelle ; les actions secondaires (boucles, favoris, aperçu) sont toutes présentées au même niveau.【F:home.php†L62-L115】

## Parcours clés

- **Continuité panier → commande peu explicite** : aucun rappel du nombre d'articles ou du total panier dans l'en-tête, obligeant l'utilisateur à interrompre sa navigation pour vérifier son panier.【F:header.php†L80-L127】
- **Recherche peu valorisée** : la zone de recherche home n'indique pas les filtres disponibles ni les résultats récents, alors que le back-end expose une logique de sauvegarde (`data-saved-searches`).【F:home.php†L21-L53】
- **Parcours administration absent** : les écrans d'administration ne sont pas directement accessibles depuis le home, alors qu'ils sont cruciaux pour le persona "Responsable magasin" identifié lors des entretiens exploratoires.【F:header.php†L267-L308】

## Accessibilité & performance

- **Contrôles non sémantiques** : l'incrémentation de quantité utilise des ancres sans attributs ARIA ni rôles adaptés, ce qui bloque clavier et lecteurs d'écran.【F:single-product.php†L87-L95】
- **Couleurs peu contrastées** : les badges pastels (promo, top ventes) ne respectent pas les ratios de contraste recommandés (ex. #fffbeb / #b45309 ≈ 2.3:1) et nécessitent une refonte palette.【F:Customer/style.css†L13-L40】
- **Carousel peu performant** : la section produit instancie Slick avec quatre actions par item, ce qui alourdit le DOM et dégrade la performance mobile. Une version "liste scrollable" plus légère est recommandée.【F:home.php†L85-L115】

## Recommandations immédiates

1. Clarifier la navigation en distinguant raccourcis primaires (Inventaire, Panier, Administration) et outils secondaires (Profil, Support).
2. Harmoniser le ton éditorial en français et revoir les CTA critiques (achat, ajout panier, parcours admin).
3. Introduire une palette et un design system commun à l'app PHP et à la SPA (`frontend/`) pour garantir la cohérence visuelle.
4. Renforcer les contrôles interactifs (boutons, formulaires) avec un balisage sémantique, des `aria-label`, et des styles focus visibles.
5. Simplifier les carrousels produits au profit de grilles responsive et paquets paginés pour réduire le coût JS.
