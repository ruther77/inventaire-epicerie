import { useMemo, useState } from 'react';

const MOCK_ORDERS = [
  { id: 'CMD-2024-001', status: 'Préparation', customer: 'Épicerie du centre', amount: 245.6 },
  { id: 'CMD-2024-002', status: 'Expédiée', customer: 'Primeurs & Co', amount: 98.4 },
  { id: 'CMD-2024-003', status: 'Brouillon', customer: 'Restaurant Piment Rouge', amount: 312.2 },
];

const STATUS_BADGES = {
  Préparation: { label: 'En cours', variant: 'warning' },
  Expédiée: { label: 'Expédiée', variant: 'success' },
  Brouillon: { label: 'À finaliser', variant: 'new' },
};

export default function OrdersPage() {
  const [query, setQuery] = useState('');

  const orders = useMemo(() => {
    const value = query.trim().toLowerCase();
    if (!value) {
      return MOCK_ORDERS;
    }
    return MOCK_ORDERS.filter((order) =>
      [order.id, order.customer, order.status].some((field) => field.toLowerCase().includes(value)),
    );
  }, [query]);

  return (
    <div className="page">
      <header className="page-header">
        <div>
          <p className="page-eyebrow">Parcours</p>
          <h1>Commandes</h1>
          <p className="page-description">
            Visualisez l&apos;avancement des commandes et reprenez exactement où vous en étiez.
          </p>
        </div>
        <div className="page-badges">
          <span className="badge badge-count">{orders.length}</span>
        </div>
      </header>
      <section className="card">
        <div className="orders-toolbar">
          <label htmlFor="orders-search" className="visually-hidden">
            Rechercher une commande
          </label>
          <input
            id="orders-search"
            type="search"
            placeholder="Rechercher par client, numéro ou statut"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
        </div>
        <div className="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>Commande</th>
                <th>Client</th>
                <th>Montant</th>
                <th>Statut</th>
              </tr>
            </thead>
            <tbody>
              {orders.map((order) => (
                <tr key={order.id}>
                  <td>{order.id}</td>
                  <td>{order.customer}</td>
                  <td>{order.amount.toFixed(2)} €</td>
                  <td>
                    <span className={`badge badge-${STATUS_BADGES[order.status]?.variant ?? 'neutral'}`}>
                      {STATUS_BADGES[order.status]?.label ?? order.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
