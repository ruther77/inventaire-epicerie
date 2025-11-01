# Plan de qualification (accessibilité, performance, retours utilisateurs)

## Accessibilité (WCAG 2.1 AA)

1. **Audit automatisé** :
   - Lighthouse (mode accessibility) sur home, fiche produit, panier.
   - axe DevTools pour vérifier `aria-*`, rôles, contraste.
2. **Tests manuels** :
   - Navigation clavier (Tab, Shift+Tab, Enter, Space) sur tous les composants interactifs.
   - Lecture NVDA/VoiceOver des pages clés (vérifier ordres de lecture, labels).
   - Vérification `prefers-reduced-motion` et zoom 200%.

## Performance

1. **Mesures Lighthouse** : objectif ≥ 90 en Performance sur mobile.
2. **WebPageTest** : scénario ajout panier → validation (TTI < 3s sur 4G).
3. **Optimisations ciblées** : lazy-loading images, remplacement carrousels Slick par `scroll-snap`, minification CSS (Vite/Tailwind).

## Tests utilisateurs

1. **Protocole** : 5 participants (2 responsables rayon, 2 préparateurs, 1 client fidelisé) – sessions modérées de 30 min.
2. **Scénarios** :
   - Ajouter un produit depuis le home et le retrouver dans le panier.
   - Marquer un article en rupture depuis l'écran inventaire.
   - Consulter l'historique de commandes.
3. **Collecte** : grille SUS, notation parcours (1-5), verbatim.
4. **Synthèse** : restitution en atelier de 45 min avec priorisation (méthode MoSCoW).

## Validation avant mise en production

- ✅ Check-list accessibilité signée (Product designer + Dev référent).
- ✅ Rapport Lighthouse & WebPageTest partagés dans Notion.
- ✅ Retours utilisateurs intégrés (issues GitHub tag `ux-feedback`).
- ✅ Feature flags activés pour lancer une bêta fermée 2 semaines.
