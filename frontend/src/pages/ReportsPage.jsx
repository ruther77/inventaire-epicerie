import { useQuery } from '@tanstack/react-query';
import { fetchProducts } from '../api/client.js';

export default function ReportsPage() {
  const { data: products = [], isLoading } = useQuery({
    queryKey: ['products'],
    queryFn: fetchProducts,
  });

  const categories = products.reduce((accumulator, product) => {
    const key = product.categorie ?? 'Non classé';
    accumulator[key] = (accumulator[key] ?? 0) + (product.stock_actuel ?? 0);
    return accumulator;
  }, {});

  return (
    <div className="page">
      <header className="page-header">
        <div>
          <p className="page-eyebrow">Explorer</p>
          <h1>Analyses & rapports</h1>
          <p className="page-description">
            Obtenez un aperçu instantané de la répartition des stocks par catégorie.
          </p>
          <div className="page-badges">
            <span className="badge badge-beta">Bêta</span>
          </div>
        </div>
      </header>
      <section className="card">
        <h2>Répartition des stocks</h2>
        {isLoading ? (
          <p>Calcul des indicateurs…</p>
        ) : (
          <div className="grid two-columns">
            {Object.entries(categories).map(([label, value]) => (
              <div key={label} className="report-card">
                <p className="badge">{label}</p>
                <h3>{value}</h3>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
