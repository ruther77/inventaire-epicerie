const NOTIFICATIONS = [
  { id: 1, title: 'Stock faible', description: 'Le stock des pommes Golden est passé sous le seuil critique.' },
  { id: 2, title: 'Commande expédiée', description: 'La commande CMD-2024-002 a été expédiée.' },
];

export default function NotificationsPage() {
  return (
    <div className="page">
      <header className="page-header">
        <div>
          <p className="page-eyebrow">Compte</p>
          <h1>Notifications</h1>
          <p className="page-description">
            Restez informé des événements importants liés à votre activité.
          </p>
        </div>
        <div className="page-badges">
          <span className="badge badge-new">Nouveau</span>
        </div>
      </header>
      <section className="card">
        <h2>Dernières alertes</h2>
        <ul className="notifications-list">
          {NOTIFICATIONS.map((item) => (
            <li key={item.id}>
              <strong>{item.title}</strong>
              <p>{item.description}</p>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
