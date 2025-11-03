import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  createUserAccount,
  deleteUserAccount,
  fetchUsers,
  updateUserAccount,
} from '../api/client.js';
import { useAuth } from '../auth/AuthContext.jsx';

const EMPTY_FORM = {
  username: '',
  email: '',
  full_name: '',
  role: 'standard',
  password: '',
  confirmPassword: '',
  is_active: true,
};

export default function UserManagementPage() {
  const { user } = useAuth();
  const canManage = user?.role === 'admin';
  const queryClient = useQueryClient();
  const [form, setForm] = useState(EMPTY_FORM);
  const [editingId, setEditingId] = useState(null);
  const [feedback, setFeedback] = useState(null);

  const usersQuery = useQuery({
    queryKey: ['users'],
    queryFn: fetchUsers,
    enabled: canManage,
  });

  const resetForm = () => {
    setForm(EMPTY_FORM);
    setEditingId(null);
  };

  const handleApiError = (error, fallbackMessage) => {
    const detail = error?.response?.data?.detail ?? fallbackMessage;
    setFeedback({ type: 'error', message: detail });
  };

  const createMutation = useMutation({
    mutationFn: createUserAccount,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] });
      setFeedback({ type: 'success', message: 'Utilisateur créé avec succès.' });
      resetForm();
    },
    onError: (error) => handleApiError(error, "Impossible de créer l'utilisateur."),
  });

  const updateMutation = useMutation({
    mutationFn: ({ userId, payload }) => updateUserAccount(userId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] });
      setFeedback({ type: 'success', message: 'Profil mis à jour.' });
      resetForm();
    },
    onError: (error) => handleApiError(error, 'La mise à jour a échoué.'),
  });

  const deleteMutation = useMutation({
    mutationFn: deleteUserAccount,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] });
      setFeedback({ type: 'success', message: 'Compte supprimé.' });
    },
    onError: (error) => handleApiError(error, 'Impossible de supprimer ce compte.'),
  });

  const busy = createMutation.isPending || updateMutation.isPending || deleteMutation.isPending;

  if (!canManage) {
    return (
      <div className="page">
        <header className="page-header">
          <div>
            <p className="page-eyebrow">Administration</p>
            <h1>Gestion des utilisateurs</h1>
            <p className="page-description">
              Connectez-vous avec un compte administrateur pour accéder aux paramètres avancés.
            </p>
          </div>
          <div className="page-badges">
            <span className="badge badge-warning">Restreint</span>
          </div>
        </header>
        <section className="card">
          <p>Vous devez disposer des droits administrateur pour accéder à cette section.</p>
        </section>
      </div>
    );
  }

  const handleSubmit = (event) => {
    event.preventDefault();
    setFeedback(null);

    if (!form.username.trim() && !editingId) {
      setFeedback({ type: 'error', message: "Le nom d'utilisateur est obligatoire." });
      return;
    }

    if (!editingId && !form.password) {
      setFeedback({ type: 'error', message: 'Un mot de passe est requis pour créer un compte.' });
      return;
    }

    if (form.password && form.password !== form.confirmPassword) {
      setFeedback({ type: 'error', message: 'La confirmation du mot de passe ne correspond pas.' });
      return;
    }

    if (editingId) {
      const payload = {
        email: form.email || null,
        full_name: form.full_name || null,
        role: form.role,
        is_active: form.is_active,
      };
      if (form.password) {
        payload.password = form.password;
      }
      updateMutation.mutate({ userId: editingId, payload });
    } else {
      const payload = {
        username: form.username.trim(),
        email: form.email || null,
        full_name: form.full_name || null,
        role: form.role,
        password: form.password,
        is_active: form.is_active,
      };
      createMutation.mutate(payload);
    }
  };

  const startEdit = (account) => {
    setEditingId(account.id);
    setFeedback(null);
    setForm({
      username: account.username,
      email: account.email ?? '',
      full_name: account.full_name ?? '',
      role: account.role,
      password: '',
      confirmPassword: '',
      is_active: account.is_active,
    });
  };

  const handleDelete = (accountId, accountName) => {
    if (window.confirm(`Supprimer le compte « ${accountName} » ?`)) {
      deleteMutation.mutate(accountId);
    }
  };

  const users = usersQuery.data ?? [];

  return (
    <div className="page">
      <header className="page-header">
        <div>
          <p className="page-eyebrow">Administration</p>
          <h1>Gestion des utilisateurs</h1>
          <p className="page-description">
            Pilotez les accès à la plateforme, créez de nouveaux comptes ou réinitialisez des mots de passe.
          </p>
        </div>
        <div className="page-badges">
          <span className="badge badge-warning">Critique</span>
        </div>
      </header>
      <section className="card">
        {feedback && (
          <div className={`alert ${feedback.type === 'error' ? 'alert-error' : 'alert-success'}`}>
            {feedback.message}
          </div>
        )}

        <form className="user-form" onSubmit={handleSubmit}>
          <div className="grid two-columns">
            <label>
              Identifiant
              <input
                type="text"
                value={form.username}
                onChange={(event) => setForm((prev) => ({ ...prev, username: event.target.value }))}
                placeholder="ex: gestionnaire"
                disabled={Boolean(editingId)}
              />
            </label>
            <label>
              Adresse e-mail
              <input
                type="email"
                value={form.email}
                onChange={(event) => setForm((prev) => ({ ...prev, email: event.target.value }))}
                placeholder="contact@exemple.fr"
              />
            </label>
            <label>
              Nom complet
              <input
                type="text"
                value={form.full_name}
                onChange={(event) => setForm((prev) => ({ ...prev, full_name: event.target.value }))}
                placeholder="Prénom Nom"
              />
            </label>
            <label>
              Rôle
              <select
                value={form.role}
                onChange={(event) => setForm((prev) => ({ ...prev, role: event.target.value }))}
              >
                <option value="standard">Utilisateur</option>
                <option value="admin">Administrateur</option>
              </select>
            </label>
            <label>
              Mot de passe
              <input
                type="password"
                value={form.password}
                onChange={(event) => setForm((prev) => ({ ...prev, password: event.target.value }))}
                placeholder={editingId ? 'Laisser vide pour ne pas changer' : 'Définir un mot de passe'}
              />
            </label>
            <label>
              Confirmation
              <input
                type="password"
                value={form.confirmPassword}
                onChange={(event) =>
                  setForm((prev) => ({ ...prev, confirmPassword: event.target.value }))
                }
              />
            </label>
            <label className="checkbox">
              <input
                type="checkbox"
                checked={form.is_active}
                onChange={(event) => setForm((prev) => ({ ...prev, is_active: event.target.checked }))}
              />
              <span>Compte actif</span>
            </label>
          </div>
          <div className="form-actions">
            <button type="submit" disabled={busy}>
              {editingId ? 'Mettre à jour' : 'Créer le compte'}
            </button>
            {editingId && (
              <button type="button" className="secondary" onClick={resetForm} disabled={busy}>
                Annuler la modification
              </button>
            )}
          </div>
        </form>

        <h3>Comptes existants</h3>
        {usersQuery.isLoading ? (
          <p>Chargement des comptes…</p>
        ) : (
          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>Identifiant</th>
                  <th>Email</th>
                  <th>Nom complet</th>
                  <th>Rôle</th>
                  <th>Statut</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {users.map((account) => (
                  <tr key={account.id}>
                    <td>{account.username}</td>
                    <td>{account.email ?? '—'}</td>
                    <td>{account.full_name ?? '—'}</td>
                    <td>{account.role === 'admin' ? 'Administrateur' : 'Utilisateur'}</td>
                    <td>
                      <span className={`status-pill ${account.is_active ? 'status-active' : 'status-inactive'}`}>
                        {account.is_active ? 'Actif' : 'Inactif'}
                      </span>
                    </td>
                    <td className="user-actions">
                      <button type="button" onClick={() => startEdit(account)} disabled={busy}>
                        Modifier
                      </button>
                      <button
                        type="button"
                        className="danger"
                        onClick={() => handleDelete(account.id, account.username)}
                        disabled={busy}
                      >
                        Supprimer
                      </button>
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
