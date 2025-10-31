import PropTypes from 'prop-types';
import { Link } from 'react-router-dom';

export default function SavedViewsPanel({ title, description, views }) {
  if (!views || views.length === 0) {
    return null;
  }

  return (
    <aside className="saved-views-panel">
      <h3>{title}</h3>
      {description && <p>{description}</p>}
      <ul>
        {views.map((view) => (
          <li key={view.id}>
            <Link to={view.to} className="saved-view-link">
              <div>
                <span>{view.label}</span>
                {view.badge && <span className={`badge badge-${view.badge.variant}`}>{view.badge.label}</span>}
              </div>
              {view.description && <p>{view.description}</p>}
            </Link>
          </li>
        ))}
      </ul>
    </aside>
  );
}

SavedViewsPanel.propTypes = {
  title: PropTypes.string.isRequired,
  description: PropTypes.string,
  views: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.string.isRequired,
      label: PropTypes.string.isRequired,
      description: PropTypes.string,
      to: PropTypes.string.isRequired,
      badge: PropTypes.shape({
        label: PropTypes.string.isRequired,
        variant: PropTypes.string,
      }),
    }),
  ),
};

SavedViewsPanel.defaultProps = {
  description: undefined,
  views: [],
};
