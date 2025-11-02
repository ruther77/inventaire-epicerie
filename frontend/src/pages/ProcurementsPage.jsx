import { useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  createProcurement,
  fetchProcurements,
  fetchProducts,
  fetchSuppliers,
  updateProcurement,
} from '../api/client.js';

const STATUSES = ['Reçu', 'En attente', 'Planifié'];

export default function ProcurementsPage() {
  const queryClient = useQueryClient();
  const { data: procurements = [], isLoading, isError } = useQuery({
    queryKey: ['procurements'],
    queryFn: fetchProcurements,
  });
  const { data: suppliers = [] } = useQuery({ queryKey: ['suppliers'], queryFn: fetchSuppliers });
  const { data: products = [] } = useQuery({ queryKey: ['products'], queryFn: fetchProducts });

  const [numero, setNumero] = useState('');
  const [fournisseurId, setFournisseurId] = useState('');
  const [statut, setStatut] = useState(STATUSES[0]);
  const [lineForm, setLineForm] = useState({ produitId: '', quantite: 1, prixUnitaire: '' });
  const [lines, setLines] = useState([]);

  const createMutation = useMutation({
    mutationFn: createProcurement,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['procurements'] });
      setNumero('');
      setFournisseurId('');
      setStatut(STATUSES[0]);
      setLines([]);
      setLineForm({ produitId: '', quantite: 1, prixUnitaire: '' });
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, payload }) => updateProcurement(id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['procurements'] });
    },
  });

  const handleAddLine = () => {
    if (!lineForm.produitId) {
      return;
    }
    const product = products.find((item) => String(item.id) === lineForm.produitId);
    const quantity = Number(lineForm.quantite) || 0;
    const unitPrice = Number(lineForm.prixUnitaire) || 0;
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
      },
    ]);
    setLineForm({ produitId: '', quantite: 1, prixUnitaire: '' });
  };

  const handleRemoveLine = (index) => {
    setLines((prev) => prev.filter((_, idx) => idx !== index));
  };

  const estimatedTotal = useMemo(
    () => lines.reduce((sum, line) => sum + line.quantite * line.prixUnitaire, 0),
    [lines],
  );

  const handleSubmit = (event) => {
    event.preventDefault();
    if (!numero.trim() || lines.length === 0) {
      return;
    }
    const payload = {
      numero: numero.trim(),
      fournisseur_id: fournisseurId ? Number(fournisseurId) : undefined,
      statut,
      lignes: lines.map((line) => ({
        produit_id: line.produitId,
        quantite: line.quantite,
        prix_unitaire: line.prixUnitaire,
      })),
    };
    createMutation.mutate(payload);
  };

  const handleStatusChange = (procurement, nextStatus) => {
    updateMutation.mutate({ id: procurement.id, payload: { statut: nextStatus } });
  };

  return (
    <div className="page">
      <header className="page-header">
        <div>
          <p className="page-eyebrow">Achats</p>
          <h1>Approvisionnements</h1>
          <p className="page-description">
            Tracez les livraisons fournisseurs, anticipez les réceptions et conservez vos preuves d&apos;achat.
          </p>
        </div>
      </header>
      <section className="card">
        <h2>Enregistrer un approvisionnement</h2>
        <form className="grid two-columns" onSubmit={handleSubmit}>
          <label htmlFor="procurement-number">Numéro</label>
          <input
            id="procurement-number"
            type="text"
            value={numero}
            onChange={(event) => setNumero(event.target.value)}
            required
          />
          <label htmlFor="procurement-supplier">Fournisseur</label>
          <select
            id="procurement-supplier"
            value={fournisseurId}
            onChange={(event) => setFournisseurId(event.target.value)}
          >
            <option value="">Sans fournisseur</option>
            {suppliers.map((supplier) => (
              <option key={supplier.id} value={supplier.id}>
                {supplier.nom}
              </option>
            ))}
          </select>
          <label htmlFor="procurement-status">Statut</label>
          <select
            id="procurement-status"
            value={statut}
            onChange={(event) => setStatut(event.target.value)}
          >
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
                    product && product.prix_achat != null
                      ? String(product.prix_achat)
                      : prev.prixUnitaire,
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
              placeholder="Prix unitaire"
              value={lineForm.prixUnitaire}
              onChange={(event) => setLineForm((prev) => ({ ...prev, prixUnitaire: event.target.value }))}
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
                        × {line.quantite} · {line.prixUnitaire.toFixed(2)} €
                      </span>
                    </div>
                    <button type="button" className="secondary" onClick={() => handleRemoveLine(index)}>
                      Retirer
                    </button>
                  </li>
                ))}
              </ul>
              <p>Total estimé : {estimatedTotal.toFixed(2)} €</p>
            </div>
          )}
          <div className="form-actions">
            <button type="submit" disabled={createMutation.isLoading || lines.length === 0}>
              Enregistrer l&apos;approvisionnement
            </button>
          </div>
        </form>
      </section>
      <section className="card">
        <h2>Historique des approvisionnements</h2>
        {isLoading && <p>Chargement des approvisionnements…</p>}
        {isError && <p>Impossible de récupérer les approvisionnements.</p>}
        {!isLoading && !isError && (
          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>Numéro</th>
                  <th>Fournisseur</th>
                  <th>Date</th>
                  <th>Montant</th>
                  <th>Statut</th>
                </tr>
              </thead>
              <tbody>
                {procurements.map((procurement) => (
                  <tr key={procurement.id}>
                    <td>{procurement.numero}</td>
                    <td>{procurement.fournisseur_nom ?? '—'}</td>
                    <td>{new Date(procurement.date_appro).toLocaleDateString()}</td>
                    <td>{procurement.total_ht.toFixed(2)} €</td>
                    <td>
                      <select
                        value={procurement.statut}
                        onChange={(event) => handleStatusChange(procurement, event.target.value)}
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
                {procurements.length === 0 && (
                  <tr>
                    <td colSpan={5}>Aucun approvisionnement enregistré pour le moment.</td>
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
