import { useEffect, useState } from 'react';
import { useAuth } from '../auth/AuthContext.jsx';

export default function LoginModal() {
  const { isLoginOpen, closeLoginModal, login, isAuthenticating, authError } = useAuth();
  const [form, setForm] = useState({ username: '', password: '' });
  const [localError, setLocalError] = useState(null);

  useEffect(() => {
    if (!isLoginOpen) {
      setForm({ username: '', password: '' });
      setLocalError(null);
      return undefined;
    }

    const handleKeyDown = (event) => {
      if (event.key === 'Escape') {
        closeLoginModal();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isLoginOpen, closeLoginModal]);

  if (!isLoginOpen) {
    return null;
  }

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!form.username.trim() || !form.password) {
      setLocalError('Veuillez saisir votre identifiant et votre mot de passe.');
      return;
    }
    setLocalError(null);
    try {
      await login({ username: form.username.trim(), password: form.password });
    } catch (error) {
      if (!authError) {
        setLocalError("Impossible de vous connecter, veuillez réessayer.");
      }
    }
  };

  return (
    <div className="modal-backdrop" role="presentation" onClick={closeLoginModal}>
      <div
        className="modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="login-title"
        onClick={(event) => event.stopPropagation()}
      >
        <button type="button" className="modal-close" aria-label="Fermer" onClick={closeLoginModal}>
          ×
        </button>
        <h2 id="login-title">Connexion sécurisée</h2>
        <p>Authentifiez-vous pour accéder aux fonctionnalités d&apos;administration.</p>
        {localError && <p className="modal-error">{localError}</p>}
        {authError && <p className="modal-error">{authError}</p>}
        <form onSubmit={handleSubmit} className="modal-form">
          <label htmlFor="login-username">Identifiant</label>
          <input
            id="login-username"
            type="text"
            autoComplete="username"
            value={form.username}
            onChange={(event) => setForm((prev) => ({ ...prev, username: event.target.value }))}
            autoFocus
          />
          <label htmlFor="login-password">Mot de passe</label>
          <input
            id="login-password"
            type="password"
            autoComplete="current-password"
            value={form.password}
            onChange={(event) => setForm((prev) => ({ ...prev, password: event.target.value }))}
          />
          <button type="submit" className="modal-submit" disabled={isAuthenticating}>
            {isAuthenticating ? 'Connexion…' : 'Se connecter'}
          </button>
        </form>
      </div>
    </div>
  );
}
