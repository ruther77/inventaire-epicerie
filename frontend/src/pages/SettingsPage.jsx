import { useState } from 'react';

export default function SettingsPage() {
  const [preferences, setPreferences] = useState({
    theme: 'system',
    alerts: true,
    digest: false,
  });

  return (
    <div className="page">
      <header className="page-header">
        <div>
          <p className="page-eyebrow">Compte</p>
          <h1>Paramètres</h1>
          <p className="page-description">
            Personnalisez votre expérience, votre affichage et les notifications reçues.
          </p>
        </div>
      </header>
      <section className="card">
        <h2>Préférences</h2>
        <form className="settings-form">
          <label>
            Thème
            <select
              value={preferences.theme}
              onChange={(event) => setPreferences((prev) => ({ ...prev, theme: event.target.value }))}
            >
              <option value="system">Automatique</option>
              <option value="light">Clair</option>
              <option value="dark">Sombre</option>
            </select>
          </label>
          <label className="checkbox">
            <input
              type="checkbox"
              checked={preferences.alerts}
              onChange={(event) => setPreferences((prev) => ({ ...prev, alerts: event.target.checked }))}
            />
            <span>Activer les alertes critiques</span>
          </label>
          <label className="checkbox">
            <input
              type="checkbox"
              checked={preferences.digest}
              onChange={(event) => setPreferences((prev) => ({ ...prev, digest: event.target.checked }))}
            />
            <span>Recevoir un récapitulatif hebdomadaire</span>
          </label>
        </form>
      </section>
    </div>
  );
}
