import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { fetchProducts } from '../api/client.js';

export default function InventoryPage() {
  const { data: products = [], isLoading, isError } = useQuery({
    queryKey: ['products'],
    queryFn: fetchProducts,
  });
  const [search, setSearch] = useState('');

  const filtered = useMemo(() => {
    const query = search.trim().toLowerCase();
    if (!query) {
      return products;
    }
    return products.filter((product) =>
      [product.nom, product.categorie]
        .filter(Boolean)
        .some((value) => value.toLowerCase().includes(query)),
    );
  }, [products, search]);

  return (
    <section className="card">
      <h2>Catalogue & Approvisionnement</h2>
      <p>Consultez le catalogue et filtrez les produits en quelques secondes.</p>
      <input
        type="search"
        placeholder="Rechercher un produit ou une catégorie"
        value={search}
        onChange={(event) => setSearch(event.target.value)}
      />
      {isLoading && <p>Chargement du catalogue…</p>}
      {isError && <p>Impossible de récupérer le catalogue produits.</p>}
      {!isLoading && !isError && (
        <div className="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>Produit</th>
                <th>Catégorie</th>
                <th>Prix de vente</th>
                <th>Stock</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((product) => (
                <tr key={product.id}>
                  <td>{product.nom}</td>
                  <td>{product.categorie ?? 'N/A'}</td>
                  <td>{product.prix_vente.toFixed(2)} €</td>
                  <td>{product.stock_actuel ?? 0}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
