import { useState } from 'react';
import PropTypes from 'prop-types';
import { Link } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext.jsx';

const AUTH_MENU = [
  { to: '/panier', label: 'Panier', badge: { label: '2', variant: 'count' } },
  { to: '/favoris', label: 'Favoris' },
  { to: '/notifications', label: 'Notifications', badge: { label: 'Nouveau', variant: 'new' } },
  { to: '/parametres', label: 'Paramètres' },
  { to: '/compte', label: 'Profil & espace perso' },
];

const GUEST_MENU = [
  { to: '/auth/login', label: 'Se connecter' },
  { to: '/auth/signup', label: "Créer un compte", badge: { label: 'Nouveau', variant: 'new' } },
  { to: '/aide', label: 'Besoin d\'aide ?' },
];

export default function UserMenu({ onNavigate }) {
  const { user, logout, openLoginModal } = useAuth();
  const [isOpen, setIsOpen] = useState(false);

  const initials = user?.full_name
    ? user.full_name
        .split(' ')
        .filter(Boolean)
        .map((part) => part[0]?.toUpperCase())
        .slice(0, 2)
        .join('')
    : user?.username?.slice(0, 2)?.toUpperCase() ?? '??';

  const displayName = user?.full_name || user?.username || 'Espace utilisateur';

  const toggle = () => setIsOpen((prev) => !prev);
  const closeMenu = () => setIsOpen(false);

  const handleNavigation = () => {
    closeMenu();
    onNavigate();
  };

  return (
    <div className={`user-menu-shell ${isOpen ? 'open' : ''}`}>
      <button
        type="button"
        className="user-menu-trigger"
        aria-haspopup="true"
        aria-expanded={isOpen}
        onClick={toggle}
      >
        <span className="user-menu-avatar" aria-hidden="true">
          {initials}
        </span>
        <span className="user-menu-label">{displayName}</span>
      </button>
      {isOpen && (
        <div className="user-menu-dropdown" role="menu">
          <div className="user-menu-header">
            {user ? (
              <>
                <p className="user-menu-welcome">Bonjour, {displayName}</p>
                <p className="user-menu-subtitle">Retrouvez vos commandes, favoris et paramètres.</p>
              </>
            ) : (
              <>
                <p className="user-menu-welcome">Bienvenue !</p>
                <p className="user-menu-subtitle">
                  Connectez-vous ou créez un compte pour sauvegarder vos préférences.
                </p>
              </>
            )}
          </div>
          <ul>
            {(user ? AUTH_MENU : GUEST_MENU).map((item) => (
              <li key={item.to}>
                <Link to={item.to} className="user-menu-link" onClick={handleNavigation}>
                  <span>{item.label}</span>
                  {item.badge && (
                    <span className={`badge badge-${item.badge.variant}`}>{item.badge.label}</span>
                  )}
                </Link>
              </li>
            ))}
          </ul>
          <div className="user-menu-footer">
            {user ? (
              <button type="button" onClick={() => { logout(); closeMenu(); }} className="user-menu-secondary">
                Déconnexion
              </button>
            ) : (
              <button type="button" onClick={() => { openLoginModal(); closeMenu(); }} className="user-menu-secondary">
                Connexion rapide
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

UserMenu.propTypes = {
  onNavigate: PropTypes.func,
};

UserMenu.defaultProps = {
  onNavigate: () => {},
};
