import PropTypes from 'prop-types';
import { Link } from 'react-router-dom';
import { Badge } from '../design-system/index.js';

export default function JourneyTimeline({ title, description, steps, eyebrow, footnote }) {
  return (
    <section className="card journey-timeline">
      <header className="journey-timeline-header">
        {eyebrow && <p className="journey-eyebrow">{eyebrow}</p>}
        <h2>{title}</h2>
        {description && <p className="journey-description">{description}</p>}
      </header>
      <ol className="journey-timeline-list">
        {steps.map((step, index) => (
          <li key={step.id ?? step.to ?? step.title} className="journey-step">
            <div className="journey-step-marker" aria-hidden="true">
              <span>{String(index + 1).padStart(2, '0')}</span>
            </div>
            <div className="journey-step-content">
              <div className="journey-step-heading">
                <h3>{step.title}</h3>
                {step.badge && <Badge variant={step.badge.variant} label={step.badge.label} />}
              </div>
              {step.meta && <p className="journey-step-meta">{step.meta}</p>}
              <p>{step.description}</p>
              {step.to && (
                <Link to={step.to} className="journey-step-link">
                  {step.ctaLabel ?? 'Ouvrir la page'}
                </Link>
              )}
            </div>
          </li>
        ))}
      </ol>
      {footnote && <p className="journey-footnote">{footnote}</p>}
    </section>
  );
}

JourneyTimeline.propTypes = {
  title: PropTypes.string.isRequired,
  description: PropTypes.string,
  eyebrow: PropTypes.string,
  steps: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.string,
      title: PropTypes.string.isRequired,
      description: PropTypes.string.isRequired,
      meta: PropTypes.string,
      to: PropTypes.string,
      ctaLabel: PropTypes.string,
      badge: PropTypes.shape({
        label: PropTypes.string.isRequired,
        variant: PropTypes.string,
      }),
    }),
  ).isRequired,
  footnote: PropTypes.string,
};

JourneyTimeline.defaultProps = {
  description: undefined,
  eyebrow: undefined,
  footnote: undefined,
};
