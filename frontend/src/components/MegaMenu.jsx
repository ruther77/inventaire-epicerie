import { useState } from 'react';
import PropTypes from 'prop-types';
import { Link, NavLink } from 'react-router-dom';

import { Badge } from '../design-system/index.js';

export default function MegaMenu({ sections, isMobileOpen, onToggleMobile, onNavigate }) {
  const [activeSection, setActiveSection] = useState(sections[0]?.id ?? null);

  const handleSectionChange = (sectionId) => {
    setActiveSection(sectionId);
  };

  const handleNavigate = () => {
    onNavigate();
    onToggleMobile(false);
  };

  const defaultSection = sections[0]?.id ?? null;

  return (
    <div className={`mega-menu ${isMobileOpen ? 'mega-menu-open' : ''}`}>
      <button
        type="button"
        className="mega-menu-trigger"
        aria-expanded={isMobileOpen}
        onClick={() => onToggleMobile(!isMobileOpen)}
      >
        Menu
      </button>
      <div className="mega-menu-content" onMouseLeave={() => setActiveSection(defaultSection)}>
        <div className="mega-menu-tabs">
          {sections.map((section) => (
            <button
              key={section.id}
              type="button"
              className={`mega-menu-tab ${activeSection === section.id ? 'active' : ''}`}
              onMouseEnter={() => handleSectionChange(section.id)}
              onFocus={() => handleSectionChange(section.id)}
              onClick={() => handleSectionChange(section.id)}
            >
              <span className="mega-menu-tab-label">{section.label}</span>
              {section.subtitle && <span className="mega-menu-tab-subtitle">{section.subtitle}</span>}
            </button>
          ))}
        </div>
        {sections.map((section) => (
          <div
            key={section.id}
            className={`mega-menu-panel ${activeSection === section.id ? 'visible' : ''}`}
          >
            <div className="mega-menu-panel-header">
              <div>
                <h3>{section.title}</h3>
                {section.description && <p>{section.description}</p>}
              </div>
              <div className="mega-menu-featured-actions">
                {section.featuredActions?.map((action) => (
                  <NavLink
                    key={action.to}
                    to={action.to}
                    className="mega-menu-featured-link"
                    onClick={handleNavigate}
                  >
                    {action.label}
                    {action.badge && <Badge variant={action.badge.variant} label={action.badge.label} />}
                  </NavLink>
                ))}
              </div>
            </div>
            <div className="mega-menu-grid">
              {section.items?.map((item) => (
                <Link
                  key={item.to}
                  to={item.to}
                  className="mega-menu-item"
                  onClick={handleNavigate}
                >
                  <div className="mega-menu-item-heading">
                    <span>{item.label}</span>
                    {item.badge && <Badge variant={item.badge.variant} label={item.badge.label} />}
                  </div>
                  {item.description && <p>{item.description}</p>}
                </Link>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

MegaMenu.propTypes = {
  sections: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.string.isRequired,
      label: PropTypes.string.isRequired,
      subtitle: PropTypes.string,
      title: PropTypes.string.isRequired,
      description: PropTypes.string,
      featuredActions: PropTypes.arrayOf(
        PropTypes.shape({
          to: PropTypes.string.isRequired,
          label: PropTypes.string.isRequired,
          badge: PropTypes.shape({
            label: PropTypes.string.isRequired,
            variant: PropTypes.string,
          }),
        }),
      ),
      items: PropTypes.arrayOf(
        PropTypes.shape({
          to: PropTypes.string.isRequired,
          label: PropTypes.string.isRequired,
          description: PropTypes.string,
          badge: PropTypes.shape({
            label: PropTypes.string.isRequired,
            variant: PropTypes.string,
          }),
        }),
      ),
    }),
  ).isRequired,
  isMobileOpen: PropTypes.bool.isRequired,
  onToggleMobile: PropTypes.func.isRequired,
  onNavigate: PropTypes.func,
};

MegaMenu.defaultProps = {
  onNavigate: () => {},
};
