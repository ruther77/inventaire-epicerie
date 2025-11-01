export default function LegacyToolsPage() {
  const legacyUrl = import.meta.env.VITE_LEGACY_TOOLS_URL ?? '';
  const isEnabled = legacyUrl.trim().length > 0;

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
        {!isEnabled && (
          <p>
            Les outils historiques sont désactivés. Configurez <code>VITE_LEGACY_TOOLS_URL</code> pour les
            rendre accessibles dans un environnement sécurisé.
          </p>
        )}
        {isEnabled && (
          <>
            <p>
              Certaines fonctionnalités (extraction de facture, audit d&apos;inventaire…) restent gérées par
              l&apos;ancienne interface Streamlit pendant la période de migration. Accédez-y directement via
              l&apos;iframe sécurisée ci-dessous.
            </p>
            <iframe
              className="legacy-app"
              title="Application Streamlit historique"
              src={legacyUrl}
              allow="camera; microphone"
              sandbox="allow-same-origin allow-scripts allow-forms"
            />
          </>
        )}
      </section>
    </div>
  );
}
