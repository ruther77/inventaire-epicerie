import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  createCategory,
  deleteCategory,
  fetchCategories,
  updateCategory,
} from '../api/client.js';

const EMPTY_FORM = { nom: '', description: '' };

export default function CategoriesPage() {
  const queryClient = useQueryClient();
  const { data: categories = [], isLoading, isError } = useQuery({
    queryKey: ['categories'],
    queryFn: fetchCategories,
  });

  const [form, setForm] = useState(EMPTY_FORM);
  const [editingId, setEditingId] = useState(null);

  const createMutation = useMutation({
    mutationFn: createCategory,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['categories'] });
      setForm(EMPTY_FORM);
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, payload }) => updateCategory(id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['categories'] });
      setForm(EMPTY_FORM);
      setEditingId(null);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: deleteCategory,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['categories'] });
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
      description: form.description.trim() ? form.description.trim() : undefined,
    };
    if (editingId) {
      updateMutation.mutate({ id: editingId, payload });
    } else {
      createMutation.mutate(payload);
    }
  };

  const handleEdit = (category) => {
    setEditingId(category.id);
    setForm({ nom: category.nom, description: category.description ?? '' });
  };

  const handleCancel = () => {
    setEditingId(null);
    setForm(EMPTY_FORM);
  };

  return (
    <div className="page">
      <header className="page-header">
        <div>
          <p className="page-eyebrow">Catalogue</p>
          <h1>Catégories de produits</h1>
          <p className="page-description">
            Créez, renommez ou supprimez vos catégories pour faciliter le classement des produits.
          </p>
        </div>
      </header>
      <section className="card">
        <h2>{editingId ? 'Modifier la catégorie' : 'Ajouter une catégorie'}</h2>
        <form className="grid two-columns" onSubmit={handleSubmit}>
          <label htmlFor="category-name">Nom</label>
          <input
            id="category-name"
            type="text"
            value={form.nom}
            onChange={(event) => setForm((prev) => ({ ...prev, nom: event.target.value }))}
            required
          />
          <label htmlFor="category-description">Description</label>
          <textarea
            id="category-description"
            value={form.description}
            onChange={(event) => setForm((prev) => ({ ...prev, description: event.target.value }))}
          />
          <div className="form-actions">
            <button type="submit" disabled={createMutation.isLoading || updateMutation.isLoading}>
              {editingId ? 'Enregistrer les modifications' : 'Créer la catégorie'}
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
        <h2>Catégories existantes</h2>
        {isLoading && <p>Chargement des catégories…</p>}
        {isError && <p>Impossible de récupérer les catégories.</p>}
        {!isLoading && !isError && (
          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>Nom</th>
                  <th>Description</th>
                  <th>Produits associés</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {categories.map((category) => (
                  <tr key={category.id}>
                    <td>{category.nom}</td>
                    <td>{category.description ?? '—'}</td>
                    <td>{category.produits_count}</td>
                    <td className="table-actions">
                      <button type="button" onClick={() => handleEdit(category)}>
                        Modifier
                      </button>
                      <button
                        type="button"
                        className="danger"
                        onClick={() => deleteMutation.mutate(category.id)}
                        disabled={deleteMutation.isLoading}
                      >
                        Supprimer
                      </button>
                    </td>
                  </tr>
                ))}
                {categories.length === 0 && (
                  <tr>
                    <td colSpan={4}>Aucune catégorie enregistrée pour le moment.</td>
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
