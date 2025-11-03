import { Link } from 'react-router-dom';
import JourneyTimeline from '../components/JourneyTimeline.jsx';
import SavedViewsPanel from '../components/SavedViewsPanel.jsx';

const FEED_STEPS = [
  {
    id: 'landing',
    title: 'Accueil personnalisé',
    description:
      'Un flux dynamique combine tendances globales et recommandations calculées selon l\'historique de visionnage.',
    meta: 'Inspiré de YouTube : mosaïque de contenus et actions rapides.',
    to: '/dashboard',
    ctaLabel: 'Ouvrir le tableau de bord',
  },
  {
    id: 'watch',
    title: 'Consommer un contenu',
    description:
      'Lecture instantanée, transcription générée par FastAPI et suggestions contextuelles pour poursuivre la session.',
    meta: 'Disponible sur mobile et desktop.',
    to: '/catalogue?search=video',
  },
  {
    id: 'interact',
    title: 'Interagir et enregistrer',
    description:
      'Ajoutez aux favoris, créez une playlist métier ou programmez un rappel via les notifications.',
    to: '/favoris',
  },
  {
    id: 'analyze',
    title: 'Analyser les performances',
    description:
      'Suivez le temps de visionnage, l\'engagement et les tendances par thématique dans vos rapports personnalisés.',
    meta: 'Cartes KPI et filtres temporels avancés.',
    to: '/explorer/rapports',
    badge: { label: 'Bêta', variant: 'beta' },
  },
];

const FEED_COLLECTIONS = [
  {
    id: 'reco',
    title: 'Recommandé pour vous',
    description: 'Une sélection basée sur vos listes de lecture et l\'activité récente de votre équipe.',
    to: '/notifications',
  },
  {
    id: 'trending',
    title: 'Tendances régionales',
    description: 'Les contenus plébiscités cette semaine dans votre zone commerciale.',
    to: '/catalogue?search=top',
  },
  {
    id: 'playlists',
    title: 'Playlists métiers',
    description: 'Des parcours pré-configurés pour former les équipes en magasin ou en centrale.',
    to: '/promotions',
  },
];

export default function ContentHubPage() {
  return (
    <div className="page">
      <header className="page-header">
        <div>
          <p className="page-eyebrow">Parcours</p>
          <h1>Studio de contenus façon YouTube</h1>
          <p className="page-description">
            Diffusez des vidéos de formation ou des briefs commerciaux avec un suivi précis de la consommation.
          </p>
        </div>
        <SavedViewsPanel
          title="Vues médias"
          description="Épinglez vos playlists et rapports de performance."
          slot="journey-content"
          allowManage
        />
      </header>

      <JourneyTimeline
        eyebrow="Workflow"
        title="Un hub média en quatre temps"
        description="Du flux personnalisé à l\'analyse, chaque étape reste dans votre SPA React."
        steps={FEED_STEPS}
      />

      <section className="card journey-insights">
        <h2>Collections dynamiques</h2>
        <p>
          Créez des sélections automatiques alimentées par les données FastAPI : algorithmes maison ou règles
          métiers simples selon vos besoins.
        </p>
        <div className="grid three-columns">
          {FEED_COLLECTIONS.map((collection) => (
            <Link key={collection.id} to={collection.to} className="journey-card-link">
              <div className="journey-card-heading">
                <span>{collection.title}</span>
              </div>
              <p>{collection.description}</p>
            </Link>
          ))}
        </div>
      </section>
    </div>
  );
}
