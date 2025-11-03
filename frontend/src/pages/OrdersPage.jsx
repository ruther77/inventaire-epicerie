import { useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  createOrder,
  fetchClients,
  fetchOrders,
  fetchProducts,
  updateOrder,
} from '../api/client.js';

const STATUSES = ['Brouillon', 'Préparation', 'Expédiée'];

export default function OrdersPage() {
  const queryClient = useQueryClient();
  const { data: orders = [], isLoading, isError } = useQuery({
    queryKey: ['orders'],
    queryFn: fetchOrders,
  });
  const { data: clients = [] } = useQuery({ queryKey: ['clients'], queryFn: fetchClients });
  const { data: products = [] } = useQuery({ queryKey: ['products'], queryFn: fetchProducts });

  const [numero, setNumero] = useState('');
  const [clientId, setClientId] = useState('');
  const [date, setDate] = useState('');
  const [statut, setStatut] = useState(STATUSES[0]);
  const [query, setQuery] = useState('');
  const [lineForm, setLineForm] = useState({ produitId: '', quantite: 1, prixUnitaire: '', tva: '' });
  const [lines, setLines] = useState([]);

  const createMutation = useMutation({
    mutationFn: createOrder,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['orders'] });
      setNumero('');
      setClientId('');
      setDate('');
      setStatut(STATUSES[0]);
      setLines([]);
      setLineForm({ produitId: '', quantite: 1, prixUnitaire: '', tva: '' });
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, payload }) => updateOrder(id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['orders'] });
    },
  });

  const handleAddLine = () => {
    if (!lineForm.produitId) {
      return;
    }
    const product = products.find((item) => String(item.id) === lineForm.produitId);
    const quantity = Number(lineForm.quantite) || 0;
    const unitPrice = Number(lineForm.prixUnitaire) || 0;
    const tva = Number(lineForm.tva) || 0;
    if (quantity <= 0) {
      return;
    }
    setLines((prev) => [
      ...prev,
      {
        produitId: Number(lineForm.produitId),
        produitNom: product?.nom ?? `Produit ${lineForm.produitId}`,
        quantite: quantity,
        prixUnitaire: unitPrice,
        tva,
      },
    ]);
    setLineForm({ produitId: '', quantite: 1, prixUnitaire: '', tva: '' });
  };

  const handleRemoveLine = (index) => {
    setLines((prev) => prev.filter((_, idx) => idx !== index));
  };

  const totals = useMemo(() => {
    return lines.reduce(
      (acc, line) => {
        const total = line.quantite * line.prixUnitaire;
        return {
          ht: acc.ht + total,
          ttc: acc.ttc + total * (1 + line.tva / 100),
        };
      },
      { ht: 0, ttc: 0 },
    );
  }, [lines]);

  const filteredOrders = useMemo(() => {
    const value = query.trim().toLowerCase();
    if (!value) {
      return orders;
    }
    return orders.filter((order) => {
      const fields = [order.numero, order.client_nom ?? '', order.statut];
      return fields.some((field) => field.toLowerCase().includes(value));
    });
  }, [orders, query]);

  const handleSubmit = (event) => {
    event.preventDefault();
    if (!numero.trim() || lines.length === 0) {
      return;
    }
    const payload = {
      numero: numero.trim(),
      client_id: clientId ? Number(clientId) : undefined,
      statut,
      date_commande: date ? new Date(`${date}T00:00:00`) : undefined,
      lignes: lines.map((line) => ({
        produit_id: line.produitId,
        quantite: line.quantite,
        prix_unitaire: line.prixUnitaire,
        tva: line.tva,
      })),
    };
    createMutation.mutate(payload);
  };

  const handleStatusChange = (order, nextStatus) => {
    updateMutation.mutate({ id: order.id, payload: { statut: nextStatus } });
  };

  return (
    <div className="page">
      <header className="page-header">
        <div>
          <p className="page-eyebrow">Commandes</p>
          <h1>Commandes clients</h1>
          <p className="page-description">
            Suivez les ventes, préparez les documents de livraison et gardez une trace des montants facturés.
          </p>
        </div>
      </header>
      <section className="card">
        <h2>Créer une commande</h2>
        <form className="grid two-columns" onSubmit={handleSubmit}>
          <label htmlFor="order-number">Numéro</label>
          <input
            id="order-number"
            type="text"
            value={numero}
            onChange={(event) => setNumero(event.target.value)}
            required
          />
          <label htmlFor="order-client">Client</label>
          <select id="order-client" value={clientId} onChange={(event) => setClientId(event.target.value)}>
            <option value="">Sans client</option>
            {clients.map((client) => (
              <option key={client.id} value={client.id}>
                {client.nom}
              </option>
            ))}
          </select>
          <label htmlFor="order-date">Date</label>
          <input id="order-date" type="date" value={date} onChange={(event) => setDate(event.target.value)} />
          <label htmlFor="order-status">Statut</label>
          <select id="order-status" value={statut} onChange={(event) => setStatut(event.target.value)}>
            {STATUSES.map((status) => (
              <option key={status} value={status}>
                {status}
              </option>
            ))}
          </select>
          <div className="line-builder">
            <h3>Ajouter un produit</h3>
            <select
              value={lineForm.produitId}
              onChange={(event) => {
                const value = event.target.value;
                const product = products.find((item) => String(item.id) === value);
                setLineForm((prev) => ({
                  ...prev,
                  produitId: value,
                  prixUnitaire:
                    product && product.prix_vente != null
                      ? String(product.prix_vente)
                      : prev.prixUnitaire,
                  tva: product && product.tva != null ? String(product.tva) : prev.tva,
                }));
              }}
            >
              <option value="">Sélectionner un produit…</option>
              {products.map((product) => (
                <option key={product.id} value={product.id}>
                  {product.nom}
                </option>
              ))}
            </select>
            <input
              type="number"
              min="0"
              step="0.01"
              value={lineForm.quantite}
              onChange={(event) => setLineForm((prev) => ({ ...prev, quantite: event.target.value }))}
            />
            <input
              type="number"
              min="0"
              step="0.01"
              placeholder="Prix"
              value={lineForm.prixUnitaire}
              onChange={(event) => setLineForm((prev) => ({ ...prev, prixUnitaire: event.target.value }))}
            />
            <input
              type="number"
              min="0"
              step="0.01"
              placeholder="TVA %"
              value={lineForm.tva}
              onChange={(event) => setLineForm((prev) => ({ ...prev, tva: event.target.value }))}
            />
            <button type="button" onClick={handleAddLine}>
              Ajouter
            </button>
          </div>
          {lines.length > 0 && (
            <div className="line-list">
              <ul>
                {lines.map((line, index) => (
                  <li key={`${line.produitId}-${index}`}>
                    <div>
                      <strong>{line.produitNom}</strong>
                      <span>
                        {' '}
                        × {line.quantite} · {line.prixUnitaire.toFixed(2)} € (TVA {line.tva}%)
                      </span>
                    </div>
                    <button type="button" className="secondary" onClick={() => handleRemoveLine(index)}>
                      Retirer
                    </button>
                  </li>
                ))}
              </ul>
              <p>
                Total HT : {totals.ht.toFixed(2)} € — Total TTC : {totals.ttc.toFixed(2)} €
              </p>
            </div>
          )}
          <div className="form-actions">
            <button type="submit" disabled={createMutation.isLoading || lines.length === 0}>
              Enregistrer la commande
            </button>
          </div>
        </form>
      </section>
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
        {isLoading && <p>Chargement des commandes…</p>}
        {isError && <p>Impossible de récupérer les commandes.</p>}
        {!isLoading && !isError && (
          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>Commande</th>
                  <th>Client</th>
                  <th>Date</th>
                  <th>Total TTC</th>
                  <th>Statut</th>
                </tr>
              </thead>
              <tbody>
                {filteredOrders.map((order) => (
                  <tr key={order.id}>
                    <td>{order.numero}</td>
                    <td>{order.client_nom ?? '—'}</td>
                    <td>{new Date(order.date_commande).toLocaleDateString()}</td>
                    <td>{order.total_ttc.toFixed(2)} €</td>
                    <td>
                      <select
                        value={order.statut}
                        onChange={(event) => handleStatusChange(order, event.target.value)}
                      >
                        {STATUSES.map((status) => (
                          <option key={status} value={status}>
                            {status}
                          </option>
                        ))}
                      </select>
                    </td>
                  </tr>
                ))}
                {filteredOrders.length === 0 && (
                  <tr>
                    <td colSpan={5}>Aucune commande correspondant à votre recherche.</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
