import { useAuth } from '../auth/AuthContext.jsx';
import SavedViewsPanel from '../components/SavedViewsPanel.jsx';

export default function AccountPage() {
  const { user } = useAuth();

  return (
    <div className="page">
      <header className="page-header">
        <div>
          <p className="page-eyebrow">Compte</p>
          <h1>Espace personnel</h1>
          <p className="page-description">
            Regroupez vos préférences, vos favoris et vos notifications dans un même endroit.
          </p>
        </div>
        <SavedViewsPanel
          title="Vos accès"
          description="Conservez vos raccourcis personnels après chaque connexion."
          slot="account"
          allowManage
        />
      </header>
      <section className="card">
        <h2>Profil</h2>
        {user ? (
          <ul className="profile-details">
            <li>
              <span>Nom complet</span>
              <strong>{user.full_name ?? '—'}</strong>
            </li>
            <li>
              <span>Identifiant</span>
              <strong>{user.username}</strong>
            </li>
            <li>
              <span>Rôle</span>
              <strong>{user.role === 'admin' ? 'Administrateur' : 'Utilisateur'}</strong>
            </li>
          </ul>
        ) : (
          <p>Connectez-vous pour personnaliser votre espace.</p>
        )}
      </section>
    </div>
  );
}
