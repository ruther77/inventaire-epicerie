import { useState } from 'react';
import { Link } from 'react-router-dom';

export default function SignupPage() {
  const [form, setForm] = useState({
    company: '',
    email: '',
    phone: '',
  });
  const [submitted, setSubmitted] = useState(false);

  const handleSubmit = (event) => {
    event.preventDefault();
    setSubmitted(true);
  };

  return (
    <div className="page auth-page">
      <header className="page-header">
        <div>
          <p className="page-eyebrow">Authentification</p>
          <h1>Créer un compte</h1>
          <p className="page-description">
            Centralisez vos données et bénéficiez de la personnalisation des parcours.
          </p>
        </div>
      </header>
      <section className="card auth-card">
        {submitted ? (
          <div className="signup-confirmation">
            <h2>Merci !</h2>
            <p>
              Nous vous recontacterons rapidement pour activer votre compte et configurer votre espace.
            </p>
            <Link to="/auth/login" className="button-link">
              Retourner à la connexion
            </Link>
          </div>
        ) : (
          <form className="auth-form" onSubmit={handleSubmit}>
            <label htmlFor="signup-company">Structure</label>
            <input
              id="signup-company"
              type="text"
              value={form.company}
              onChange={(event) => setForm((prev) => ({ ...prev, company: event.target.value }))}
            />
            <label htmlFor="signup-email">Adresse e-mail</label>
            <input
              id="signup-email"
              type="email"
              value={form.email}
              onChange={(event) => setForm((prev) => ({ ...prev, email: event.target.value }))}
            />
            <label htmlFor="signup-phone">Téléphone</label>
            <input
              id="signup-phone"
              type="tel"
              value={form.phone}
              onChange={(event) => setForm((prev) => ({ ...prev, phone: event.target.value }))}
            />
            <button type="submit">Envoyer ma demande</button>
          </form>
        )}
        <p className="auth-switch">
          Déjà un compte ? <Link to="/auth/login">Se connecter</Link>
        </p>
      </section>
    </div>
  );
}
