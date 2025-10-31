import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import SavedViewsPanel from '../components/SavedViewsPanel.jsx';

const JOURNEYS = [
  {
    id: 'achat',
    label: 'Préparer un achat',
    description: 'Consultez le catalogue, comparez les prix et ajoutez au panier en un clic.',
    to: '/catalogue',
  },
  {
    id: 'commandes',
    label: 'Suivre les commandes',
    description: 'Visualisez l\'état des commandes clients, imprimez ou relancez en direct.',
    to: '/commandes',
  },
  {
    id: 'promotions',
    label: 'Explorer les promotions',
    description: 'Repérez les offres en cours et préparez vos campagnes commerciales.',
    to: '/promotions',
    badge: { label: 'Promo', variant: 'promo' },
  },
  {
    id: 'aide',
    label: 'Besoin d\'aide ?',
    description: 'Accédez aux guides express et contactez l\'équipe support.',
    to: '/aide',
  },
];

const SAVED_VIEWS = [
  {
    id: 'low-stock',
    label: 'Stock faible',
    description: 'Produits à recharger en priorité cette semaine.',
    to: '/catalogue?filter=low-stock',
    badge: { label: 'A surveiller', variant: 'warning' },
  },
  {
    id: 'week-orders',
    label: 'Commandes de la semaine',
    description: 'Suivi des ventes réalisées sur les 7 derniers jours.',
    to: '/commandes?range=7d',
  },
  {
    id: 'promo-basket',
    label: 'Panier promo',
    description: 'Sélection produits saisonniers pour mise en avant.',
    to: '/promotions',
    badge: { label: 'Nouveau', variant: 'new' },
  },
];

export default function HomePage() {
  const navigate = useNavigate();
  const [query, setQuery] = useState('');

  const handleSubmit = (event) => {
    event.preventDefault();
    navigate(`/catalogue?search=${encodeURIComponent(query.trim())}`);
  };

  return (
    <div className="landing">
      <section className="landing-hero card">
        <div>
          <p className="hero-eyebrow">Nouvelle expérience</p>
          <h1>Que souhaitez-vous faire aujourd\'hui ?</h1>
          <p className="hero-description">
            Retrouvez les parcours clés pour gérer votre activité : achats, suivi des commandes, promotions
            et assistance en quelques secondes.
          </p>
          <form className="hero-search" onSubmit={handleSubmit}>
            <label htmlFor="global-search" className="visually-hidden">
              Rechercher un produit, une commande ou une action
            </label>
            <input
              id="global-search"
              type="search"
              placeholder="Rechercher un produit, une commande ou une action"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
            />
            <button type="submit">Rechercher</button>
          </form>
        </div>
        <SavedViewsPanel
          title="Vos accès rapides"
          description="Retrouvez vos vues sauvegardées, épinglées sur tous vos appareils."
          views={SAVED_VIEWS}
        />
      </section>
      <section className="landing-journeys">
        <h2>Choisissez un parcours</h2>
        <div className="journey-grid">
          {JOURNEYS.map((journey) => (
            <Link key={journey.id} to={journey.to} className="journey-card">
              <div className="journey-heading">
                <span>{journey.label}</span>
                {journey.badge && <span className={`badge badge-${journey.badge.variant}`}>{journey.badge.label}</span>}
              </div>
              <p>{journey.description}</p>
            </Link>
          ))}
        </div>
      </section>
      <section className="landing-support card">
        <div>
          <h3>Centre de contrôle</h3>
          <p>
            Accédez au tableau de bord pour retrouver vos indicateurs clés et ouvrir les vues métiers lorsque
            vous en avez besoin.
          </p>
        </div>
        <Link to="/dashboard" className="button-link">
          Ouvrir le tableau de bord
        </Link>
      </section>
    </div>
  );
}
