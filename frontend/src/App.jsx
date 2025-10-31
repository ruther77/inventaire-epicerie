import { NavLink, Route, Routes } from 'react-router-dom';
import HomePage from './pages/HomePage.jsx';
import InventoryPage from './pages/InventoryPage.jsx';
import PosPage from './pages/PosPage.jsx';
import ReportsPage from './pages/ReportsPage.jsx';
import LegacyToolsPage from './pages/LegacyToolsPage.jsx';
import UserManagementPage from './pages/UserManagementPage.jsx';
import { useAuth } from './auth/AuthContext.jsx';
import LoginModal from './components/LoginModal.jsx';

const baseRoutes = [
  { path: '/', label: 'Vitrine', element: <HomePage /> },
  { path: '/inventory', label: 'Approvisionnement', element: <InventoryPage /> },
  { path: '/pos', label: 'Point de vente', element: <PosPage /> },
  { path: '/reports', label: 'Rapports', element: <ReportsPage /> },
  { path: '/legacy-tools', label: 'Outils Streamlit', element: <LegacyToolsPage /> },
];

const adminRoutes = [
  { path: '/users', label: 'Comptes utilisateurs', element: <UserManagementPage /> },
];

export default function App() {
  const { user, openLoginModal, logout } = useAuth();

  const isAdmin = user?.role === 'admin';
  const availableRoutes = isAdmin ? [...baseRoutes, ...adminRoutes] : baseRoutes;
  const displayName = user?.full_name || user?.username;

  return (
    <>
      <header>
        <div className="header-top">
          <div>
            <h1>Inventaire Épicerie</h1>
            <p>Nouvelle interface unifiée pour piloter l&apos;activité</p>
          </div>
          <div className="header-actions">
            {user ? (
              <div className="user-menu">
                <div>
                  <span className="user-name">Bonjour&nbsp;{displayName}</span>
                  <span className={`role-badge role-${user.role}`}>
                    {user.role === 'admin' ? 'Administrateur' : 'Utilisateur'}
                  </span>
                </div>
                <button type="button" onClick={logout} className="logout-button">
                  Déconnexion
                </button>
              </div>
            ) : (
              <button type="button" className="login-button" onClick={openLoginModal}>
                Connexion
              </button>
            )}
          </div>
        </div>
        <nav>
          {availableRoutes.map((route) => (
            <NavLink
              key={route.path}
              to={route.path}
              className={({ isActive }) => (isActive ? 'active' : undefined)}
              end={route.path === '/'}
            >
              {route.label}
            </NavLink>
          ))}
        </nav>
      </header>
      <main>
        <Routes>
          {availableRoutes.map((route) => (
            <Route key={route.path} path={route.path} element={route.element} />
          ))}
        </Routes>
      </main>
      <LoginModal />
    </>
  );
}
