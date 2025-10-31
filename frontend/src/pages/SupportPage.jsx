const SUPPORT_SHORTCUTS = [
  { id: 'guide', label: 'Guide de prise en main', description: 'Retrouvez les étapes clés de configuration.', to: '#' },
  { id: 'faq', label: 'FAQ', description: 'Consultez les réponses aux questions fréquentes.', to: '#' },
  { id: 'contact', label: 'Contacter le support', description: 'Envoyez un message à notre équipe.', to: 'mailto:support@inventaire.fr' },
];

export default function SupportPage() {
  return (
    <div className="page">
      <header className="page-header">
        <div>
          <p className="page-eyebrow">Aide</p>
          <h1>Centre d&apos;aide</h1>
          <p className="page-description">
            Des repères contextuels pour vous guider et vous accompagner dans vos démarches.
          </p>
        </div>
      </header>
      <section className="card">
        <h2>Ressources</h2>
        <ul className="support-list">
          {SUPPORT_SHORTCUTS.map((item) => (
            <li key={item.id}>
              <a href={item.to} className="support-link">
                <span>{item.label}</span>
                <p>{item.description}</p>
              </a>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
