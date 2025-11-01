import { useMemo } from "react";

const FEATURES = [
  {
    title: "Centralisez votre catalogue",
    description:
      "Synchronisez vos fournisseurs, mettez à jour les prix en temps réel et construisez des assortiments sur-mesure.",
  },
  {
    title: "Accélérez la préparation des commandes",
    description:
      "Retrouvez les listes intelligentes, vos favoris et l'historique des achats pour gagner du temps au quotidien.",
  },
  {
    title: "Pilotez vos performances",
    description:
      "Suivez vos indicateurs clés, analysez les ventes et identifiez les opportunités de promotion.",
  },
];

const TIMELINE_STEPS = [
  {
    title: "Créez votre compte",
    description:
      "Activez votre espace sécurisé et invitez votre équipe pour collaborer sur le même environnement de travail.",
  },
  {
    title: "Connectez vos données",
    description: "Importez vos catalogues fournisseurs, vos commandes et vos stocks en quelques clics.",
  },
  {
    title: "Lancez-vous !",
    description: "Accédez au tableau de bord et commencez à piloter vos opérations en magasin.",
  },
];

const PARTNERS = ["Carrefour Market", "U Express", "Grand Frais", "Bio C Bon"];

export default function LandingPage() {
  const currentYear = useMemo(() => new Date().getFullYear(), []);

  return (
    <div className="landing-page">
      <header className="landing-hero">
        <div className="landing-hero__content">
          <p className="landing-eyebrow">Plateforme retail augmentée</p>
          <h1>Inventaire Épicerie accompagne vos équipes magasin au quotidien.</h1>
          <p className="landing-description">
            De la gestion du catalogue à la commande, en passant par la mise en avant des promotions, tout est pensé
            pour simplifier vos opérations et booster votre marge.
          </p>
          <div className="landing-actions">
            <a className="landing-cta" href="/app/">
              Accéder à l'application
            </a>
            <a className="landing-secondary" href="#features">
              Découvrir les fonctionnalités
            </a>
          </div>
        </div>
        <div className="landing-hero__card">
          <p className="landing-card__title">Vos chiffres clés en un coup d'œil</p>
          <ul>
            <li>
              <span className="landing-card__metric">-18%</span>
              <span className="landing-card__label">Temps passé à préparer les commandes</span>
            </li>
            <li>
              <span className="landing-card__metric">+12%</span>
              <span className="landing-card__label">Marge moyenne sur les rayons frais</span>
            </li>
            <li>
              <span className="landing-card__metric">24h</span>
              <span className="landing-card__label">Pour déployer Inventaire Épicerie en magasin</span>
            </li>
          </ul>
        </div>
      </header>

      <main>
        <section id="features" className="landing-section">
          <h2>Une plateforme conçue pour la distribution alimentaire</h2>
          <div className="landing-features">
            {FEATURES.map((feature) => (
              <article key={feature.title} className="landing-feature">
                <h3>{feature.title}</h3>
                <p>{feature.description}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="landing-section landing-section--highlight">
          <div className="landing-section__content">
            <h2>Connectez vos outils existants</h2>
            <p>
              Inventaire Épicerie s'intègre avec vos ERP, solutions de caisse et outils de BI. Notre équipe vous
              accompagne pour activer les imports automatiques et sécuriser vos échanges de données.
            </p>
            <div className="landing-partners">
              {PARTNERS.map((partner) => (
                <span key={partner}>{partner}</span>
              ))}
            </div>
          </div>
        </section>

        <section className="landing-section">
          <h2>Déploiement express</h2>
          <ol className="landing-timeline">
            {TIMELINE_STEPS.map((step) => (
              <li key={step.title}>
                <h3>{step.title}</h3>
                <p>{step.description}</p>
              </li>
            ))}
          </ol>
        </section>

        <section className="landing-section landing-section--cta">
          <div>
            <h2>Prêt à transformer vos opérations magasin ?</h2>
            <p>Créez votre compte en ligne et commencez à piloter vos assortiments en toute autonomie.</p>
          </div>
          <a className="landing-cta" href="/app/auth/signup">
            Créer un compte
          </a>
        </section>
      </main>

      <footer className="landing-footer">
        <p>
          © {currentYear} Inventaire Épicerie · <a href="mailto:contact@inventaire-epicerie.fr">Contact</a> ·
          <a href="/app/aide">Centre d'aide</a>
        </p>
      </footer>
    </div>
  );
}
