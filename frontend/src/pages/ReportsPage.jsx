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
    <section className="card">
      <h2>Rapports express</h2>
      <p>Cette section propose un aperçu rapide de la répartition des stocks.</p>
      {isLoading && <p>Calcul des indicateurs…</p>}
      {!isLoading && (
        <div className="grid two-columns">
          {Object.entries(categories).map(([label, value]) => (
            <div key={label}>
              <p className="badge">{label}</p>
              <h3>{value}</h3>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
