import { useQuery } from '@tanstack/react-query';
import { fetchInventorySummary } from '../api/client.js';

export default function HomePage() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['inventory-summary'],
    queryFn: fetchInventorySummary,
  });

  return (
    <section className="card">
      <h2>Vue d'ensemble</h2>
      <p>Cette page consolide les principaux indicateurs de votre épicerie.</p>
      {isLoading && <p>Chargement des métriques…</p>}
      {isError && <p>Impossible de récupérer le résumé d'inventaire.</p>}
      {data && (
        <div className="grid two-columns">
          <div>
            <p className="badge">Valeur totale d'achat</p>
            <h3>{data.total_purchase_value.toFixed(2)} €</h3>
          </div>
          <div>
            <p className="badge">Valeur totale de vente</p>
            <h3>{data.total_sale_value.toFixed(2)} €</h3>
          </div>
        </div>
      )}
    </section>
  );
}
