import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { createClient, deleteClient, fetchClients, updateClient } from '../api/client.js';

const EMPTY_FORM = {
  nom: '',
  telephone: '',
  email: '',
  adresse: '',
};

export default function ClientsPage() {
  const queryClient = useQueryClient();
  const { data: clients = [], isLoading, isError } = useQuery({
    queryKey: ['clients'],
    queryFn: fetchClients,
  });

  const [form, setForm] = useState(EMPTY_FORM);
  const [editingId, setEditingId] = useState(null);

  const createMutation = useMutation({
    mutationFn: createClient,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['clients'] });
      setForm(EMPTY_FORM);
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, payload }) => updateClient(id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['clients'] });
      setEditingId(null);
      setForm(EMPTY_FORM);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: deleteClient,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['clients'] });
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

  const handleEdit = (client) => {
    setEditingId(client.id);
    setForm({
      nom: client.nom,
      telephone: client.telephone ?? '',
      email: client.email ?? '',
      adresse: client.adresse ?? '',
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
          <h1>Clients</h1>
          <p className="page-description">
            Centralisez les coordonnées de vos clients pour accélérer la création des commandes.
          </p>
        </div>
      </header>
      <section className="card">
        <h2>{editingId ? 'Modifier un client' : 'Ajouter un client'}</h2>
        <form className="grid two-columns" onSubmit={handleSubmit}>
          <label htmlFor="client-name">Nom</label>
          <input
            id="client-name"
            type="text"
            value={form.nom}
            onChange={(event) => setForm((prev) => ({ ...prev, nom: event.target.value }))}
            required
          />
          <label htmlFor="client-phone">Téléphone</label>
          <input
            id="client-phone"
            type="text"
            value={form.telephone}
            onChange={(event) => setForm((prev) => ({ ...prev, telephone: event.target.value }))}
          />
          <label htmlFor="client-email">E-mail</label>
          <input
            id="client-email"
            type="email"
            value={form.email}
            onChange={(event) => setForm((prev) => ({ ...prev, email: event.target.value }))}
          />
          <label htmlFor="client-address">Adresse</label>
          <textarea
            id="client-address"
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
        <h2>Répertoire clients</h2>
        {isLoading && <p>Chargement des clients…</p>}
        {isError && <p>Impossible de récupérer les clients.</p>}
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
                {clients.map((client) => (
                  <tr key={client.id}>
                    <td>{client.nom}</td>
                    <td>{client.telephone ?? '—'}</td>
                    <td>{client.email ?? '—'}</td>
                    <td>{client.adresse ?? '—'}</td>
                    <td className="table-actions">
                      <button type="button" onClick={() => handleEdit(client)}>
                        Modifier
                      </button>
                      <button
                        type="button"
                        className="danger"
                        onClick={() => deleteMutation.mutate(client.id)}
                        disabled={deleteMutation.isLoading}
                      >
                        Supprimer
                      </button>
                    </td>
                  </tr>
                ))}
                {clients.length === 0 && (
                  <tr>
                    <td colSpan={5}>Aucun client enregistré pour le moment.</td>
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
