import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { fetchProducts } from '../api/client.js';
import SavedViewsPanel from '../components/SavedViewsPanel.jsx';

const SAVED_SEARCHES = [
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
];

export default function CatalogPage() {
  const { data: products = [], isLoading, isError } = useQuery({
    queryKey: ['products'],
    queryFn: fetchProducts,
  });
  const [search, setSearch] = useState('');
  const [onlyPromo, setOnlyPromo] = useState(false);

  const filtered = useMemo(() => {
    const query = search.trim().toLowerCase();
    return products.filter((product) => {
      if (onlyPromo && !product.est_promotionnel) {
        return false;
      }
      if (!query) {
        return true;
      }
      return [product.nom, product.categorie]
        .filter(Boolean)
        .some((value) => value.toLowerCase().includes(query));
    });
  }, [products, search, onlyPromo]);

  return (
    <div className="page">
      <header className="page-header">
        <div>
          <p className="page-eyebrow">Catalogue</p>
          <h1>Catalogue & approvisionnement</h1>
          <p className="page-description">
            Visualisez vos produits, filtrez par catégorie et préparez vos commandes en quelques instants.
          </p>
          <div className="page-badges">
            <span className="badge badge-new">Nouveau</span>
            <span className="badge badge-promo">Promo</span>
          </div>
        </div>
        <SavedViewsPanel
          title="Vues sauvegardées"
          description="Personnalisez vos filtres, nous mémorisons vos préférences."
          views={SAVED_SEARCHES}
        />
      </header>
      <section className="card">
        <div className="catalog-toolbar">
          <label className="catalog-search" htmlFor="catalog-search-input">
            <span className="visually-hidden">Rechercher un produit</span>
            <input
              id="catalog-search-input"
              type="search"
              placeholder="Rechercher un produit ou une catégorie"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
            />
          </label>
          <label className="catalog-filter">
            <input
              type="checkbox"
              checked={onlyPromo}
              onChange={(event) => setOnlyPromo(event.target.checked)}
            />
            <span>Voir uniquement les promos</span>
          </label>
          <div className="catalog-saved-hint">Astuce : épinglez vos filtres pour les retrouver ici.</div>
        </div>
        {isLoading && <p>Chargement du catalogue…</p>}
        {isError && <p>Impossible de récupérer le catalogue produits.</p>}
        {!isLoading && !isError && (
          <div className="table-wrapper">
            <table className="catalog-table">
              <thead>
                <tr>
                  <th>Produit</th>
                  <th>Catégorie</th>
                  <th>Prix de vente</th>
                  <th>Stock</th>
                  <th>Promotion</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((product) => (
                  <tr key={product.id}>
                    <td>{product.nom}</td>
                    <td>{product.categorie ?? 'N/A'}</td>
                    <td>{product.prix_vente.toFixed(2)} €</td>
                    <td>{product.stock_actuel ?? 0}</td>
                    <td>
                      {product.est_promotionnel ? (
                        <span className="badge badge-promo">Promo</span>
                      ) : (
                        <span className="badge">—</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
