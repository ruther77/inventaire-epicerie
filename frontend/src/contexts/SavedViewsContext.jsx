import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';
import PropTypes from 'prop-types';

const STORAGE_KEY = 'inventaire-saved-views';

const DEFAULT_VIEWS = {
  home: [
    {
      id: 'low-stock',
      label: 'Stock faible',
      description: 'Produits à recharger en priorité cette semaine.',
      to: '/catalogue?filter=low-stock',
      badge: { label: 'À surveiller', variant: 'warning' },
    },
    {
      id: 'week-orders',
      label: 'Commandes de la semaine',
      description: 'Suivi des ventes réalisées sur les 7 derniers jours.',
      to: '/commandes?range=7d',
    },
    {
      id: 'promo-basket',
      label: 'Panier promo',
      description: 'Sélection produits saisonniers pour mise en avant.',
      to: '/promotions',
      badge: { label: 'Nouveau', variant: 'new' },
    },
  ],
  dashboard: [
    {
      id: 'custom-layout',
      label: 'Disposition personnalisée',
      description: 'Votre configuration enregistrée pour le suivi hebdomadaire.',
      to: '/dashboard?layout=custom',
    },
    {
      id: 'alerts',
      label: 'Alertes critiques',
      description: "Derniers seuils d'alerte configurés sur l'inventaire.",
      to: '/notifications',
      badge: { label: '3', variant: 'count' },
    },
  ],
  catalogue: [
    {
      id: 'favorites',
      label: 'Produits favoris',
      description: 'Vos références épinglées, prêtes à commander.',
      to: '/favoris',
    },
    {
      id: 'promo',
      label: 'Promotions en cours',
      description: 'Articles remisés pour dynamiser vos ventes.',
      to: '/promotions',
      badge: { label: 'Promo', variant: 'promo' },
    },
  ],
  account: [
    {
      id: 'profile',
      label: 'Profil',
      description: 'Mettre à jour vos informations personnelles et professionnelles.',
      to: '/parametres',
    },
    {
      id: 'favorites',
      label: 'Favoris',
      description: 'Retrouvez les références que vous avez épinglées.',
      to: '/favoris',
    },
  ],
};

const SavedViewsContext = createContext(undefined);

const slugify = (value) =>
  String(value ?? '')
    .normalize('NFD')
    .replace(/\p{Diacritic}/gu, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/(^-|-$)/g, '')
    .slice(0, 64);

const ensureId = (view) => {
  if (view.id) {
    return String(view.id);
  }
  if (view.to) {
    return slugify(view.to);
  }
  if (view.label) {
    return slugify(view.label);
  }
  return `view-${Date.now()}`;
};

const normaliseView = (view) => ({
  ...view,
  id: ensureId(view),
});

const normaliseCollection = (collection) =>
  Object.entries(collection ?? {}).reduce((accumulator, [slot, list]) => {
    if (!Array.isArray(list)) {
      return accumulator;
    }
    accumulator[slot] = list.map((item) => normaliseView(item));
    return accumulator;
  }, {});

const getInitialViews = () => {
  const defaults = normaliseCollection(DEFAULT_VIEWS);

  if (typeof window === 'undefined') {
    return defaults;
  }

  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      return defaults;
    }
    const parsed = JSON.parse(raw);
    const merged = { ...defaults };
    Object.entries(normaliseCollection(parsed)).forEach(([slot, list]) => {
      merged[slot] = list;
    });
    return merged;
  } catch (error) {
    console.warn('Impossible de restaurer les vues sauvegardées', error);
    return defaults;
  }
};

export function SavedViewsProvider({ children }) {
  const [views, setViews] = useState(getInitialViews);
  const persistTimeout = useRef(null);

  useEffect(() => {
    if (typeof window === 'undefined') {
      return undefined;
    }

    if (persistTimeout.current) {
      window.clearTimeout(persistTimeout.current);
    }

    persistTimeout.current = window.setTimeout(() => {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(views));
      persistTimeout.current = null;
    }, 150);

    return () => {
      if (persistTimeout.current) {
        window.clearTimeout(persistTimeout.current);
        persistTimeout.current = null;
      }
    };
  }, [views]);

  const getViews = useCallback((slot) => views[slot] ?? [], [views]);

  const saveView = useCallback((slot, view) => {
    if (!slot || !view) {
      return;
    }
    const candidate = normaliseView(view);
    setViews((previous) => {
      const currentSlot = previous[slot] ?? [];
      const existingIndex = currentSlot.findIndex(
        (item) => item.id === candidate.id || (candidate.to && item.to === candidate.to),
      );
      let updatedSlot;
      if (existingIndex >= 0) {
        updatedSlot = currentSlot.map((item, index) => (index === existingIndex ? { ...item, ...candidate } : item));
      } else {
        updatedSlot = [...currentSlot, candidate];
      }
      return {
        ...previous,
        [slot]: updatedSlot,
      };
    });
  }, []);

  const removeView = useCallback((slot, viewId) => {
    if (!slot || !viewId) {
      return;
    }
    setViews((previous) => {
      const currentSlot = previous[slot] ?? [];
      const updatedSlot = currentSlot.filter((item) => item.id !== viewId);
      if (updatedSlot.length === currentSlot.length) {
        return previous;
      }
      return {
        ...previous,
        [slot]: updatedSlot,
      };
    });
  }, []);

  const value = useMemo(
    () => ({
      views,
      getViews,
      saveView,
      removeView,
    }),
    [views, getViews, saveView, removeView],
  );

  return <SavedViewsContext.Provider value={value}>{children}</SavedViewsContext.Provider>;
}

SavedViewsProvider.propTypes = {
  children: PropTypes.node.isRequired,
};

export function useSavedViews() {
  const context = useContext(SavedViewsContext);
  if (!context) {
    throw new Error('useSavedViews doit être utilisé dans un SavedViewsProvider');
  }
  return context;
}
