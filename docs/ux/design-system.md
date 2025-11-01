# Design system « Atlas »

Ce design system unifie les interfaces PHP historiques et la SPA `frontend/`. Il repose sur une palette accessible, une typographie "Inter"/"Manrope" et des composants modulaires.

## Fondations

### Couleurs

| Token | Hex | Usage |
|-------|-----|-------|
| `--atlas-bg` | `#f5f7fb` | Fond applicatif clair |
| `--atlas-surface` | `#ffffff` | Cartes, panneaux |
| `--atlas-surface-alt` | `#eef2ff` | Surfaces secondaires |
| `--atlas-text` | `#0f172a` | Texte principal |
| `--atlas-muted` | `#475569` | Texte secondaire |
| `--atlas-primary` | `#4f46e5` | Actions principales |
| `--atlas-primary-strong` | `#4338ca` | Hover/Focus |
| `--atlas-accent` | `#f97316` | Notifications, badges |
| `--atlas-success` | `#0ea5e9` | Statuts positifs |
| `--atlas-warning` | `#facc15` | Alertes |
| `--atlas-danger` | `#ef4444` | Erreurs |

Contraste AA vérifié (≥ 4.5:1) pour les couples texte/fond critiques (primaires et muted). Les variantes dark mode sont définies dans `Customer/style.css` et `frontend/src/design-system/design-system.css`.

### Typographie et grille

- Police par défaut : `Inter`, `font-size` de base 16px.
- Titres : `Manrope` 600. Échelle modulaire 1.125.
- Grille responsive : conteneur max 1200px, gouttière 24px, breakpoints 768px / 1024px / 1280px.

### Icônes

- Pack `bootstrap-icons` pour la cohérence multi-plateforme.
- Taille standard 18px (16px sur mobile).

## Composants

### Boutons

- Styles `primary`, `secondary`, `ghost` définis via classes `.atlas-btn` et modificateurs (`[data-variant="secondary"]`).
- Focus visible (`outline: 2px solid rgba(79, 70, 229, 0.45)`), padding vertical 12px.

### Cartes

- `.atlas-card` : bord arrondi 18px, ombre douce `0 18px 42px rgba(15, 23, 42, 0.08)`.
- Variantes `data-tone="highlight"`, `data-tone="neutral"` utilisées pour les panels du home.【F:home.php†L17-L116】

### Grilles produits

- Grille flex-wrap avec cartes `home-product-card` et `product-item` harmonisées, utilisables sur home, panier et fiche produit associée.【F:home.php†L85-L115】【F:single-product.php†L113-L160】

### Formulaires

- Champs `.atlas-field` avec label externe, placeholder indicatif.
- `:focus-visible` couleur primaire.

### Navigation

- `workspace-header` sépare clairement raccourcis, navigation contextuelle et utilitaires. L'ajout des états actifs (`aria-current`) est prévu lors de l'étape routeur afin d'assurer un suivi cohérent sur toutes les vues.【F:header.php†L235-L336】

## Implémentation

- **PHP** : `Customer/style.css` expose les variables `--atlas-*`, refactorise les composants (héros, cartes, onglets).【F:Customer/style.css†L1-L120】【F:Customer/style.css†L1407-L1536】
- **SPA** : les tokens sont synchronisés dans `frontend/src/design-system/design-system.css` avec un mapping 1:1.【F:frontend/src/design-system/design-system.css†L1-L63】
- **Accessibilité** : tous les composants interactifs ont des styles `:focus-visible`, tailles minimales 44px, et transitions neutralisées via `prefers-reduced-motion`.【F:Customer/style.css†L120-L170】【F:Customer/style.css†L1475-L1529】

## Gouvernance

- Documentation centralisée dans Storybook (`frontend/src/design-system/components.jsx`).
- Processus : création Figma → synchronisation tokens (JSON) → mise à jour CSS/React → revue UX.
- Tests : audit mensuel contrastes (axe DevTools) + revue accessibilité (WCAG 2.1 AA) + tests utilisateurs rapides (5 personnes / trimestre).
