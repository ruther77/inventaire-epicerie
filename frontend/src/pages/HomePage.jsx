import { useEffect, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import SavedViewsPanel from '../components/SavedViewsPanel.jsx';
import { useSavedViews } from '../contexts/SavedViewsContext.jsx';

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
    id: 'approvisionnements',
    label: 'Gérer les approvisionnements',
    description: 'Consignez les réceptions et préparez vos achats fournisseurs.',
    to: '/approvisionnements',
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
  {
    id: 'clients',
    label: 'Clients et fournisseurs',
    description: 'Centralisez les coordonnées de vos interlocuteurs commerciaux.',
    to: '/clients',
  },
];

export default function HomePage() {
  const navigate = useNavigate();
  const [query, setQuery] = useState('');
  const [feedback, setFeedback] = useState(null);
  const dismissTimeout = useRef(null);
  const { saveView } = useSavedViews();

  const handleSubmit = (event) => {
    event.preventDefault();
    navigate(`/catalogue?search=${encodeURIComponent(query.trim())}`);
  };

  const handlePinJourney = (journey) => {
    saveView('home', {
      id: `journey-${journey.id}`,
      label: journey.label,
      description: journey.description,
      to: journey.to,
      badge: journey.badge,
    });
    setFeedback(`« ${journey.label} » ajouté à vos raccourcis.`);
  };

  useEffect(() => {
    if (!feedback || typeof window === 'undefined') {
      return undefined;
    }

    if (dismissTimeout.current) {
      window.clearTimeout(dismissTimeout.current);
    }

    dismissTimeout.current = window.setTimeout(() => {
      setFeedback(null);
      dismissTimeout.current = null;
    }, 3000);

    return () => {
      if (dismissTimeout.current) {
        window.clearTimeout(dismissTimeout.current);
        dismissTimeout.current = null;
      }
    };
  }, [feedback]);

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
          slot="home"
          allowManage
        />
      </section>
      <section className="landing-journeys">
        <h2>Choisissez un parcours</h2>
        {feedback && <p className="journey-feedback">{feedback}</p>}
        <div className="journey-grid">
          {JOURNEYS.map((journey) => (
            <article key={journey.id} className="journey-card">
              <Link to={journey.to} className="journey-card-link">
                <div className="journey-heading">
                  <span>{journey.label}</span>
                  {journey.badge && (
                    <span className={`badge badge-${journey.badge.variant}`}>{journey.badge.label}</span>
                  )}
                </div>
                <p>{journey.description}</p>
              </Link>
              <button type="button" className="journey-pin" onClick={() => handlePinJourney(journey)}>
                Épingler ce parcours
              </button>
            </article>
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
