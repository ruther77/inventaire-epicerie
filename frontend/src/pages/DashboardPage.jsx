import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { fetchInventorySummary } from '../api/client.js';
import SavedViewsPanel from '../components/SavedViewsPanel.jsx';

const DASHBOARD_CARDS = [
  {
    id: 'inventaire',
    label: 'Inventaire',
    description: 'Analysez vos niveaux de stock et préparez les réapprovisionnements.',
    to: '/catalogue',
  },
  {
    id: 'commandes',
    label: 'Commandes',
    description: 'Suivez la préparation et la livraison des commandes clients.',
    to: '/commandes',
  },
  {
    id: 'analyses',
    label: 'Analyses',
    description: 'Consultez les rapports de performance et les tendances de ventes.',
    to: '/explorer/rapports',
    badge: { label: 'Bêta', variant: 'beta' },
  },
];

export default function DashboardPage() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['inventory-summary'],
    queryFn: fetchInventorySummary,
  });

  return (
    <div className="page">
      <header className="page-header">
        <div>
          <p className="page-eyebrow">Centre de contrôle</p>
          <h1>Tableau de bord</h1>
          <p className="page-description">
            Ouvrez les vues métiers dont vous avez besoin sans surcharger votre navigation.
          </p>
        </div>
        <SavedViewsPanel
          title="Vos configurations"
          description="Les cartes que vous avez épinglées pour retrouver votre contexte en un clin d'œil."
          slot="dashboard"
          allowManage
        />
      </header>
      <section className="card metric-grid">
        <h2>Indicateurs clés</h2>
        <div className="grid three-columns">
          <div className="metric-card">
            <p className="badge">Valeur d'achat</p>
            <h3>
              {isLoading ? '…' : isError ? '—' : `${(data?.total_purchase_value ?? 0).toFixed(2)} €`}
            </h3>
          </div>
          <div className="metric-card">
            <p className="badge">Valeur de vente</p>
            <h3>
              {isLoading ? '…' : isError ? '—' : `${(data?.total_sale_value ?? 0).toFixed(2)} €`}
            </h3>
          </div>
          <div className="metric-card">
            <p className="badge">État</p>
            <h3 className="status-ok">{isError ? 'Erreur' : 'À jour'}</h3>
          </div>
        </div>
      </section>
      <section className="card">
        <h2>Accès rapides</h2>
        <div className="grid three-columns">
          {DASHBOARD_CARDS.map((card) => (
            <Link key={card.id} to={card.to} className="dashboard-card">
              <div className="dashboard-card-heading">
                <span>{card.label}</span>
                {card.badge && <span className={`badge badge-${card.badge.variant}`}>{card.badge.label}</span>}
              </div>
              <p>{card.description}</p>
            </Link>
          ))}
        </div>
      </section>
    </div>
  );
}
