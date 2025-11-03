import PropTypes from 'prop-types';
import { Link } from 'react-router-dom';
import { useSavedViews } from '../contexts/SavedViewsContext.jsx';

export default function SavedViewsPanel({ title, description, views, slot, allowManage }) {
  const { getViews, removeView } = useSavedViews();

  const items = views ?? (slot ? getViews(slot) : []);

  if (!items || items.length === 0) {
    return null;
  }

  return (
    <aside className="saved-views-panel">
      <h3>{title}</h3>
      {description && <p>{description}</p>}
      <ul>
        {items.map((view) => (
          <li key={view.id} className="saved-view-item">
            <Link to={view.to} className="saved-view-link">
              <div>
                <span>{view.label}</span>
                {view.badge && <span className={`badge badge-${view.badge.variant}`}>{view.badge.label}</span>}
              </div>
              {view.description && <p>{view.description}</p>}
            </Link>
            {allowManage && slot && (
              <button
                type="button"
                className="saved-view-remove"
                onClick={() => removeView(slot, view.id)}
              >
                Retirer
              </button>
            )}
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
  slot: PropTypes.string,
  allowManage: PropTypes.bool,
};

SavedViewsPanel.defaultProps = {
  description: undefined,
  views: [],
  slot: undefined,
  allowManage: false,
};
