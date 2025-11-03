import { useState } from 'react';
import { useNavigate, useLocation, Link } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext.jsx';

export default function LoginPage() {
  const { login, authError, isAuthenticating } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [form, setForm] = useState({ username: '', password: '' });
  const [localError, setLocalError] = useState(null);

  const handleSubmit = async (event) => {
    event.preventDefault();
    setLocalError(null);
    if (!form.username.trim() || !form.password) {
      setLocalError('Veuillez renseigner vos identifiants.');
      return;
    }
    try {
      await login({ username: form.username.trim(), password: form.password });
      const redirectTo = location.state?.from ?? '/dashboard';
      navigate(redirectTo, { replace: true });
    } catch (error) {
      if (!authError) {
        setLocalError("Impossible de vous connecter.");
      }
    }
  };

  return (
    <div className="page auth-page">
      <header className="page-header">
        <div>
          <p className="page-eyebrow">Authentification</p>
          <h1>Connexion</h1>
          <p className="page-description">
            Accédez à votre espace personnel et retrouvez vos vues sauvegardées.
          </p>
        </div>
      </header>
      <section className="card auth-card">
        <form className="auth-form" onSubmit={handleSubmit}>
          <label htmlFor="login-username">Identifiant</label>
          <input
            id="login-username"
            type="text"
            autoComplete="username"
            value={form.username}
            onChange={(event) => setForm((prev) => ({ ...prev, username: event.target.value }))}
          />
          <label htmlFor="login-password">Mot de passe</label>
          <input
            id="login-password"
            type="password"
            autoComplete="current-password"
            value={form.password}
            onChange={(event) => setForm((prev) => ({ ...prev, password: event.target.value }))}
          />
          {(localError || authError) && (
            <p className="form-error">{localError ?? authError}</p>
          )}
          <button type="submit" disabled={isAuthenticating}>
            {isAuthenticating ? 'Connexion…' : 'Se connecter'}
          </button>
        </form>
        <p className="auth-switch">
          Pas encore de compte ? <Link to="/auth/signup">Créer un compte</Link>
        </p>
      </section>
    </div>
  );
}
