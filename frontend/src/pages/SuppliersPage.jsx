import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { createSupplier, deleteSupplier, fetchSuppliers, updateSupplier } from '../api/client.js';

const EMPTY_FORM = {
  nom: '',
  telephone: '',
  email: '',
  adresse: '',
};

export default function SuppliersPage() {
  const queryClient = useQueryClient();
  const { data: suppliers = [], isLoading, isError } = useQuery({
    queryKey: ['suppliers'],
    queryFn: fetchSuppliers,
  });

  const [form, setForm] = useState(EMPTY_FORM);
  const [editingId, setEditingId] = useState(null);

  const createMutation = useMutation({
    mutationFn: createSupplier,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['suppliers'] });
      setForm(EMPTY_FORM);
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, payload }) => updateSupplier(id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['suppliers'] });
      setEditingId(null);
      setForm(EMPTY_FORM);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: deleteSupplier,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['suppliers'] });
    },
  });

  const handleSubmit = (event) => {
    event.preventDefault();
    const trimmedName = form.nom.trim();
    if (!trimmedName) {
      return;
    }
    const payload = {
      nom: trimmedName,
      telephone: form.telephone.trim() || undefined,
      email: form.email.trim() || undefined,
      adresse: form.adresse.trim() || undefined,
    };
    if (editingId) {
      updateMutation.mutate({ id: editingId, payload });
    } else {
      createMutation.mutate(payload);
    }
  };

  const handleEdit = (supplier) => {
    setEditingId(supplier.id);
    setForm({
      nom: supplier.nom,
      telephone: supplier.telephone ?? '',
      email: supplier.email ?? '',
      adresse: supplier.adresse ?? '',
    });
  };

  const handleCancel = () => {
    setEditingId(null);
    setForm(EMPTY_FORM);
  };

  return (
    <div className="page">
      <header className="page-header">
        <div>
          <p className="page-eyebrow">Relations</p>
          <h1>Fournisseurs</h1>
          <p className="page-description">
            Gérez vos fournisseurs pour accélérer les approvisionnements et centraliser les contacts clés.
          </p>
        </div>
      </header>
      <section className="card">
        <h2>{editingId ? 'Modifier un fournisseur' : 'Ajouter un fournisseur'}</h2>
        <form className="grid two-columns" onSubmit={handleSubmit}>
          <label htmlFor="supplier-name">Nom</label>
          <input
            id="supplier-name"
            type="text"
            value={form.nom}
            onChange={(event) => setForm((prev) => ({ ...prev, nom: event.target.value }))}
            required
          />
          <label htmlFor="supplier-phone">Téléphone</label>
          <input
            id="supplier-phone"
            type="text"
            value={form.telephone}
            onChange={(event) => setForm((prev) => ({ ...prev, telephone: event.target.value }))}
          />
          <label htmlFor="supplier-email">E-mail</label>
          <input
            id="supplier-email"
            type="email"
            value={form.email}
            onChange={(event) => setForm((prev) => ({ ...prev, email: event.target.value }))}
          />
          <label htmlFor="supplier-address">Adresse</label>
          <textarea
            id="supplier-address"
            value={form.adresse}
            onChange={(event) => setForm((prev) => ({ ...prev, adresse: event.target.value }))}
          />
          <div className="form-actions">
            <button type="submit" disabled={createMutation.isLoading || updateMutation.isLoading}>
              {editingId ? 'Enregistrer' : 'Créer'}
            </button>
            {editingId && (
              <button type="button" className="secondary" onClick={handleCancel}>
                Annuler
              </button>
            )}
          </div>
        </form>
      </section>
      <section className="card">
        <h2>Répertoire fournisseurs</h2>
        {isLoading && <p>Chargement des fournisseurs…</p>}
        {isError && <p>Impossible de récupérer les fournisseurs.</p>}
        {!isLoading && !isError && (
          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>Nom</th>
                  <th>Téléphone</th>
                  <th>E-mail</th>
                  <th>Adresse</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {suppliers.map((supplier) => (
                  <tr key={supplier.id}>
                    <td>{supplier.nom}</td>
                    <td>{supplier.telephone ?? '—'}</td>
                    <td>{supplier.email ?? '—'}</td>
                    <td>{supplier.adresse ?? '—'}</td>
                    <td className="table-actions">
                      <button type="button" onClick={() => handleEdit(supplier)}>
                        Modifier
                      </button>
                      <button
                        type="button"
                        className="danger"
                        onClick={() => deleteMutation.mutate(supplier.id)}
                        disabled={deleteMutation.isLoading}
                      >
                        Supprimer
                      </button>
                    </td>
                  </tr>
                ))}
                {suppliers.length === 0 && (
                  <tr>
                    <td colSpan={5}>Aucun fournisseur enregistré pour le moment.</td>
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
