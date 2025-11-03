import { useMemo } from "react";

const HERO_METRICS = [
  { value: "120K", label: "Références synchronisées" },
  { value: "< 24h", label: "Pour être opérationnel" },
  { value: "+18%", label: "Gain de productivité moyen" },
];

const FEATURE_GROUPS = [
  {
    title: "Catalogue unifié",
    description:
      "Pilotez vos fiches produits, gérez les déclinaisons et automatisez la mise à jour des tarifs en quelques clics.",
    tags: ["Données fiables", "Visuels enrichis", "Alertes ruptures"],
  },
  {
    title: "Approvisionnement assisté",
    description:
      "Anticipez la demande grâce aux prévisions, consolidez vos commandes et suivez les réceptions en temps réel.",
    tags: ["Prévisions IA", "Listes intelligentes", "Plans de commandes"],
  },
  {
    title: "Pilotage 360°",
    description:
      "Suivez vos marges, vos écarts d'inventaire et la performance des opérations marketing sur un tableau de bord unique.",
    tags: ["Tableaux de bord", "Alertes automatiques", "Exports BI"],
  },
];

const TIMELINE_STEPS = [
  {
    title: "Onboarding express",
    description:
      "Nous importons vos historiques et configurons vos règles métiers pour que vos équipes retrouvent leurs repères.",
  },
  {
    title: "Connexion des flux",
    description:
      "ERP, caisse, facturation... nous activons les intégrations nécessaires et sécurisons les échanges de données.",
  },
  {
    title: "Accompagnement terrain",
    description:
      "Formations ciblées, coaching magasin et support premium pour garantir l'adoption par toutes vos équipes.",
  },
];

const INTEGRATIONS = ["Cegid", "Generix", "Octave", "Microsoft Dynamics", "CashMag", "Power BI"];

const TESTIMONIALS = [
  {
    quote:
      "Inventaire Épicerie nous fait gagner près d'une demi-journée par semaine sur la préparation des commandes tout en réduisant les ruptures.",
    author: "Sonia, directrice U Express Lyon",
  },
  {
    quote:
      "La vue consolidée des marges et des écarts nous permet de piloter finement nos opérations promotionnelles.",
    author: "Yanis, responsable exploitation Carrefour Market",
  },
];

const CTA_CARDS = [
  {
    title: "Demander une démo",
    description: "Bénéficiez d'une présentation personnalisée avec nos experts retail.",
    actionLabel: "Prendre rendez-vous",
    href: "mailto:contact@inventaire-epicerie.fr",
  },
  {
    title: "Essayer gratuitement",
    description: "Activez un espace test et explorez nos outils pendant 14 jours.",
    actionLabel: "Créer mon compte",
    href: "/app/auth/signup",
  },
];

export default function LandingPage() {
  const currentYear = useMemo(() => new Date().getFullYear(), []);

  return (
    <div className="landing-page">
      <header className="landing-hero">
        <div className="landing-hero__background" aria-hidden="true" />
        <div className="landing-hero__content">
          <p className="landing-eyebrow">Suite SaaS pour les épiceries & réseaux de magasins</p>
          <h1>Un cockpit moderne pour orchestrer vos opérations retail.</h1>
          <p className="landing-description">
            Inventaire Épicerie connecte vos équipes terrain, vos fournisseurs et vos outils métiers pour offrir une
            visibilité temps réel sur le stock, les ventes et la rentabilité.
          </p>
          <div className="landing-actions">
            <a className="landing-cta" href="/app/">
              Accéder à l'application
            </a>
            <a className="landing-secondary" href="#features">
              Explorer les modules
            </a>
          </div>
          <dl className="landing-metrics">
            {HERO_METRICS.map((metric) => (
              <div key={metric.label}>
                <dt>{metric.label}</dt>
                <dd>{metric.value}</dd>
              </div>
            ))}
          </dl>
        </div>

        <aside className="landing-hero__panel">
          <h2>Pilotez la performance de votre magasin</h2>
          <ul className="landing-hero__list">
            <li>
              <span className="landing-card__metric">98%</span>
              <span className="landing-card__label">de fiabilité sur les stocks valorisés</span>
            </li>
            <li>
              <span className="landing-card__metric">x3</span>
              <span className="landing-card__label">plus de campagnes promotionnelles analysées</span>
            </li>
            <li>
              <span className="landing-card__metric">7j/7</span>
              <span className="landing-card__label">support opérationnel basé en France</span>
            </li>
          </ul>
        </aside>
      </header>

      <main>
        <section id="features" className="landing-section landing-section--grid">
          <div className="landing-section__heading">
            <h2>Une plateforme modulaire qui évolue avec vos besoins</h2>
            <p>
              Nos modules couvrent l'ensemble du cycle retail : sourcing, mise en avant, vente et pilotage. Composez votre
              stack selon vos priorités.
            </p>
          </div>
          <div className="landing-feature-grid">
            {FEATURE_GROUPS.map((feature) => (
              <article key={feature.title} className="landing-feature">
                <h3>{feature.title}</h3>
                <p>{feature.description}</p>
                <ul className="landing-feature__tags">
                  {feature.tags.map((tag) => (
                    <li key={tag}>{tag}</li>
                  ))}
                </ul>
              </article>
            ))}
          </div>
        </section>

        <section className="landing-section landing-section--integrations">
          <div className="landing-section__heading">
            <h2>Compatible avec vos outils existants</h2>
            <p>
              API ouvertes, webhooks, connecteurs natifs et import automatiques : Inventaire Épicerie s'imbrique dans votre
              écosystème sans perturber vos habitudes.
            </p>
          </div>
          <div className="landing-partners">
            {INTEGRATIONS.map((name) => (
              <span key={name}>{name}</span>
            ))}
          </div>
        </section>

        <section className="landing-section landing-section--timeline">
          <div className="landing-section__heading">
            <h2>Un déploiement orchestré en trois étapes</h2>
            <p>Notre équipe Customer Success vous accompagne du cadrage initial à l'adoption complète en magasin.</p>
          </div>
          <ol className="landing-timeline">
            {TIMELINE_STEPS.map((step, index) => (
              <li key={step.title}>
                <span className="landing-timeline__index">{index + 1}</span>
                <div>
                  <h3>{step.title}</h3>
                  <p>{step.description}</p>
                </div>
              </li>
            ))}
          </ol>
        </section>

        <section className="landing-section landing-section--testimonials">
          <div className="landing-section__heading">
            <h2>Ils parlent de nous</h2>
            <p>Réseaux d'épiceries, franchises et magasins indépendants nous font confiance chaque jour.</p>
          </div>
          <div className="landing-testimonials">
            {TESTIMONIALS.map((testimonial) => (
              <figure key={testimonial.author}>
                <blockquote>“{testimonial.quote}”</blockquote>
                <figcaption>{testimonial.author}</figcaption>
              </figure>
            ))}
          </div>
        </section>

        <section className="landing-section landing-section--cta">
          {CTA_CARDS.map((card) => (
            <article key={card.title} className="landing-cta-card">
              <h3>{card.title}</h3>
              <p>{card.description}</p>
              <a className="landing-cta" href={card.href}>
                {card.actionLabel}
              </a>
            </article>
          ))}
        </section>
      </main>

      <footer className="landing-footer">
        <p>
          © {currentYear} Inventaire Épicerie · <a href="mailto:contact@inventaire-epicerie.fr">Contact</a> ·{' '}
          <a href="/app/aide">Centre d'aide</a>
        </p>
      </footer>
    </div>
  );
}
