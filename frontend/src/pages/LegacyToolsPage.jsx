export default function LegacyToolsPage() {
  return (
    <section className="card">
      <h2>Outils Streamlit existants</h2>
      <p>
        Certaines fonctionnalités (extraction de facture, audit d'inventaire…) restent gérées par l'ancienne
        interface Streamlit pendant la période de migration. Accédez-y directement via l'iframe ci-dessous.
      </p>
      <iframe
        className="legacy-app"
        title="Application Streamlit historique"
        src="http://localhost:8501"
        allow="camera; microphone"
      />
    </section>
  );
}
