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
      <section className="card">
        <h2>Gestion des utilisateurs</h2>
        <p>Vous devez disposer des droits administrateur pour accéder à cette section.</p>
      </section>
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
    <section className="card">
      <h2>Comptes utilisateurs</h2>
      <p>Pilotez les accès à la plateforme, créez de nouveaux comptes ou réinitialisez des mots de passe.</p>

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
            Mot de passe {editingId ? '(laisser vide pour conserver)' : ''}
            <input
              type="password"
              value={form.password}
              onChange={(event) => setForm((prev) => ({ ...prev, password: event.target.value }))}
            />
          </label>
          <label>
            Confirmation du mot de passe
            <input
              type="password"
              value={form.confirmPassword}
              onChange={(event) => setForm((prev) => ({ ...prev, confirmPassword: event.target.value }))}
            />
          </label>
          <label className="checkbox-field">
            <input
              type="checkbox"
              checked={form.is_active}
              onChange={(event) => setForm((prev) => ({ ...prev, is_active: event.target.checked }))}
            />
            Compte actif
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

      <div className="table-wrapper">
        {usersQuery.isLoading && <p>Chargement des comptes…</p>}
        {usersQuery.isError && <p>Impossible de récupérer les utilisateurs.</p>}
        {!usersQuery.isLoading && !usersQuery.isError && (
          <table>
            <thead>
              <tr>
                <th>Identifiant</th>
                <th>Nom complet</th>
                <th>E-mail</th>
                <th>Rôle</th>
                <th>Statut</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {users.length === 0 ? (
                <tr>
                  <td colSpan={6}>Aucun compte pour le moment. Créez votre premier utilisateur.</td>
                </tr>
              ) : (
                users.map((account) => (
                  <tr key={account.id}>
                    <td>{account.username}</td>
                    <td>{account.full_name ?? '—'}</td>
                    <td>{account.email ?? '—'}</td>
                    <td>
                      <span className={`badge role-${account.role}`}>
                        {account.role === 'admin' ? 'Administrateur' : 'Utilisateur'}
                      </span>
                    </td>
                    <td>
                      <span className={`status ${account.is_active ? 'status-active' : 'status-disabled'}`}>
                        {account.is_active ? 'Actif' : 'Désactivé'}
                      </span>
                    </td>
                    <td className="actions">
                      <button type="button" onClick={() => startEdit(account)} disabled={busy}>
                        Modifier
                      </button>
                      <button
                        type="button"
                        className="danger"
                        onClick={() => handleDelete(account.id, account.username)}
                        disabled={busy || account.id === user.id}
                      >
                        Supprimer
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        )}
      </div>
    </section>
  );
}
