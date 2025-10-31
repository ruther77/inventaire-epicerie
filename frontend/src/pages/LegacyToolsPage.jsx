export default function LegacyToolsPage() {
  return (
    <div className="page">
      <header className="page-header">
        <div>
          <p className="page-eyebrow">Explorer</p>
          <h1>Outils Streamlit</h1>
          <p className="page-description">
            Les applications historiques restent disponibles le temps de la migration.
          </p>
        </div>
      </header>
      <section className="card">
        <h2>Accès direct</h2>
        <p>
          Certaines fonctionnalités (extraction de facture, audit d&apos;inventaire…) restent gérées par
          l&apos;ancienne interface Streamlit pendant la période de migration. Accédez-y directement via l&apos;iframe
          ci-dessous.
        </p>
        <iframe
          className="legacy-app"
          title="Application Streamlit historique"
          src="http://localhost:8501"
          allow="camera; microphone"
        />
      </section>
    </div>
  );
}
