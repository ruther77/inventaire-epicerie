import { Link } from 'react-router-dom';
import JourneyTimeline from '../components/JourneyTimeline.jsx';
import SavedViewsPanel from '../components/SavedViewsPanel.jsx';

const TIMELINE_STEPS = [
  {
    id: 'catalog',
    title: 'Découvrir le catalogue',
    description:
      'Recherche plein texte, filtres intelligents et vues sauvegardées pour préparer la prochaine commande.',
    meta: 'Inspiré d\'Amazon : accès rapide aux meilleures ventes et promotions.',
    to: '/catalogue',
    ctaLabel: 'Parcourir le catalogue',
    badge: { label: 'Nouveau', variant: 'new' },
  },
  {
    id: 'product-detail',
    title: 'Consulter une fiche produit',
    description:
      'Photos, prix d\'achat et de vente, historique des mouvements : toutes les informations pour décider.',
    meta: 'Recommandations dynamiques et disponibilité multi-entrepôts.',
    to: '/catalogue?search=primeur',
  },
  {
    id: 'cart',
    title: 'Ajouter au panier et simuler un panier moyen',
    description:
      'Ajoutez plusieurs articles, ajustez les quantités et conservez le panier pour une reprise plus tard.',
    meta: 'Synchronisé sur tous les appareils et sessions.',
    to: '/panier',
  },
  {
    id: 'checkout',
    title: 'Valider et suivre la commande',
    description:
      'Création assistée d\'une commande, suivi des statuts et relances automatisées par e-mail.',
    meta: 'Notifications en temps réel pour l\'équipe commerciale.',
    to: '/commandes',
  },
  {
    id: 'aftercare',
    title: 'Fidéliser via le compte client',
    description:
      'Favoris, listes d\'achats récurrents et alertes personnalisées pour rester au plus proche des besoins.',
    meta: 'Centre de préférences et recommandations alimentées par la donnée.',
    to: '/compte',
  },
];

const EXPERIENCE_BLOCKS = [
  {
    id: 'personnalisation',
    title: 'Personnalisation',
    description:
      'Segmentez vos clients par habitudes d\'achat et proposez des assortiments pertinents à chaque connexion.',
    to: '/favoris',
  },
  {
    id: 'service',
    title: 'Service client',
    description:
      'Centralisez les demandes, suivez les tickets et mesurez la satisfaction après chaque livraison.',
    to: '/aide',
  },
  {
    id: 'analyse',
    title: 'Analyse des ventes',
    description:
      'Accédez à un tableau de bord dédié pour piloter vos marges et détecter les ruptures.',
    to: '/dashboard',
    badge: { label: 'Bêta', variant: 'beta' },
  },
];

export default function CustomerJourneyPage() {
  return (
    <div className="page">
      <header className="page-header">
        <div>
          <p className="page-eyebrow">Parcours</p>
          <h1>Parcours e-commerce inspiré d\'Amazon</h1>
          <p className="page-description">
            Rejouez un scénario complet : de la découverte produit à la fidélisation en passant par le suivi de
            commande, sans quitter l\'interface.
          </p>
        </div>
        <SavedViewsPanel
          title="Vos raccourcis"
          description="Épinglez les étapes clés de votre parcours commerce."
          slot="journey-commerce"
          allowManage
        />
      </header>

      <JourneyTimeline
        eyebrow="Étapes clés"
        title="Déroulé du parcours client"
        description="Chaque étape s\'appuie sur les modules existants de la plateforme pour offrir une expérience cohérente."
        steps={TIMELINE_STEPS}
        footnote="Tous les écrans sont accessibles depuis la barre de navigation et conservent le contexte utilisateur."
      />

      <section className="card journey-insights">
        <h2>Expérience unifiée</h2>
        <p>
          Combinez les briques Inventaire, Commandes et CRM pour proposer un parcours autonome où chaque action
          déclenche la suivante.
        </p>
        <div className="grid three-columns">
          {EXPERIENCE_BLOCKS.map((block) => (
            <Link key={block.id} to={block.to} className="journey-card-link">
              <div className="journey-card-heading">
                <span>{block.title}</span>
                {block.badge && (
                  <span className={`badge badge-${block.badge.variant}`}>{block.badge.label}</span>
                )}
              </div>
              <p>{block.description}</p>
            </Link>
          ))}
        </div>
      </section>
    </div>
  );
}
