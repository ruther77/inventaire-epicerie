import { Suspense, lazy, useEffect, useMemo, useState } from 'react';
import { Link, NavLink, Route, Routes, useLocation } from 'react-router-dom';
import { useAuth } from './auth/AuthContext.jsx';
import RequireAuth from './auth/RequireAuth.jsx';
import LoginModal from './components/LoginModal.jsx';
import Breadcrumbs from './components/Breadcrumbs.jsx';
import UserMenu from './components/UserMenu.jsx';

const HomePage = lazy(() => import('./pages/HomePage.jsx'));
const CatalogPage = lazy(() => import('./pages/CatalogPage.jsx'));
const PosPage = lazy(() => import('./pages/PosPage.jsx'));
const ReportsPage = lazy(() => import('./pages/ReportsPage.jsx'));
const LegacyToolsPage = lazy(() => import('./pages/LegacyToolsPage.jsx'));
const UserManagementPage = lazy(() => import('./pages/UserManagementPage.jsx'));
const OrdersPage = lazy(() => import('./pages/OrdersPage.jsx'));
const PromotionsPage = lazy(() => import('./pages/PromotionsPage.jsx'));
const DashboardPage = lazy(() => import('./pages/DashboardPage.jsx'));
const SupportPage = lazy(() => import('./pages/SupportPage.jsx'));
const AccountPage = lazy(() => import('./pages/AccountPage.jsx'));
const CartPage = lazy(() => import('./pages/CartPage.jsx'));
const FavoritesPage = lazy(() => import('./pages/FavoritesPage.jsx'));
const NotificationsPage = lazy(() => import('./pages/NotificationsPage.jsx'));
const SettingsPage = lazy(() => import('./pages/SettingsPage.jsx'));
const LoginPage = lazy(() => import('./pages/LoginPage.jsx'));
const SignupPage = lazy(() => import('./pages/SignupPage.jsx'));
const CategoriesPage = lazy(() => import('./pages/CategoriesPage.jsx'));
const ClientsPage = lazy(() => import('./pages/ClientsPage.jsx'));
const SuppliersPage = lazy(() => import('./pages/SuppliersPage.jsx'));
const ProcurementsPage = lazy(() => import('./pages/ProcurementsPage.jsx'));
const CustomerJourneyPage = lazy(() => import('./pages/CustomerJourneyPage.jsx'));
const ContentHubPage = lazy(() => import('./pages/ContentHubPage.jsx'));

const ROUTES = [
  { path: '/', Component: HomePage, breadcrumb: 'Accueil', section: 'home' },
  {
    path: '/dashboard',
    Component: DashboardPage,
    breadcrumb: 'Tableau de bord',
    section: 'explorer',
    requiresAuth: true,
  },
  {
    path: '/catalogue',
    Component: CatalogPage,
    breadcrumb: 'Catalogue',
    section: 'catalogue',
    badge: { label: 'Nouveau', variant: 'new' },
    requiresAuth: true,
  },
  {
    path: '/commandes',
    Component: OrdersPage,
    breadcrumb: 'Commandes',
    section: 'catalogue',
    requiresAuth: true,
  },
  {
    path: '/categories',
    Component: CategoriesPage,
    breadcrumb: 'Catégories',
    section: 'catalogue',
    requiresAuth: true,
  },
  {
    path: '/approvisionnements',
    Component: ProcurementsPage,
    breadcrumb: 'Approvisionnements',
    section: 'catalogue',
    requiresAuth: true,
  },
  {
    path: '/promotions',
    Component: PromotionsPage,
    breadcrumb: 'Promotions',
    section: 'catalogue',
    badge: { label: 'Promo', variant: 'promo' },
    requiresAuth: true,
  },
  {
    path: '/parcours/commerce',
    Component: CustomerJourneyPage,
    breadcrumb: 'Parcours e-commerce',
    section: 'scenarios',
    badge: { label: 'Nouveau', variant: 'new' },
    requiresAuth: true,
  },
  {
    path: '/parcours/contenus',
    Component: ContentHubPage,
    breadcrumb: 'Studio contenus',
    section: 'scenarios',
    requiresAuth: true,
  },
  {
    path: '/clients',
    Component: ClientsPage,
    breadcrumb: 'Clients',
    section: 'relations',
    requiresAuth: true,
  },
  {
    path: '/fournisseurs',
    Component: SuppliersPage,
    breadcrumb: 'Fournisseurs',
    section: 'relations',
    requiresAuth: true,
  },
  {
    path: '/pos',
    Component: PosPage,
    breadcrumb: 'Point de vente',
    section: 'explorer',
    requiresAuth: true,
  },
  {
    path: '/explorer/rapports',
    Component: ReportsPage,
    breadcrumb: 'Analyses',
    section: 'explorer',
    badge: { label: 'Bêta', variant: 'beta' },
    requiresAuth: true,
  },
  {
    path: '/explorer/outils',
    Component: LegacyToolsPage,
    breadcrumb: 'Outils Streamlit',
    section: 'explorer',
    requiresAuth: true,
  },
  {
    path: '/aide',
    Component: SupportPage,
    breadcrumb: 'Aide',
    section: 'support',
    requiresAuth: true,
  },
  {
    path: '/compte',
    Component: AccountPage,
    breadcrumb: 'Espace personnel',
    section: 'account',
    requiresAuth: true,
  },
  {
    path: '/panier',
    Component: CartPage,
    breadcrumb: 'Panier',
    section: 'account',
    requiresAuth: true,
  },
  {
    path: '/favoris',
    Component: FavoritesPage,
    breadcrumb: 'Favoris',
    section: 'account',
    requiresAuth: true,
  },
  {
    path: '/notifications',
    Component: NotificationsPage,
    breadcrumb: 'Notifications',
    section: 'account',
    requiresAuth: true,
  },
  {
    path: '/parametres',
    Component: SettingsPage,
    breadcrumb: 'Paramètres',
    section: 'account',
    requiresAuth: true,
  },
  {
    path: '/auth/login',
    Component: LoginPage,
    breadcrumb: 'Connexion',
    section: 'auth',
  },
  {
    path: '/auth/signup',
    Component: SignupPage,
    breadcrumb: 'Créer un compte',
    section: 'auth',
    badge: { label: 'Nouveau', variant: 'new' },
  },
];

const ADMIN_ROUTES = [
  {
    path: '/users',
    Component: UserManagementPage,
    breadcrumb: 'Comptes utilisateurs',
    section: 'administration',
    adminOnly: true,
    requiresAuth: true,
  },
];

const PRIMARY_NAV_LINKS = [
  { to: '/', label: 'Accueil' },
  { to: '/catalogue', label: 'Catalogue', requiresAuth: true },
  { to: '/clients', label: 'Contacts', requiresAuth: true },
  { to: '/dashboard', label: 'Explorer', requiresAuth: true },
  { to: '/parcours/commerce', label: 'Parcours', requiresAuth: true },
  { to: '/aide', label: 'Support', requiresAuth: true },
];

export default function App() {
  const { user } = useAuth();
  const location = useLocation();
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  const isAdmin = user?.role === 'admin';

  const primaryNavLinks = useMemo(
    () =>
      PRIMARY_NAV_LINKS.filter((link) => {
        if (link.requiresAuth && !user) {
          return false;
        }
        if (link.adminOnly && !isAdmin) {
          return false;
        }
        return true;
      }),
    [isAdmin, user],
  );

  const availableRoutes = useMemo(() => {
    if (isAdmin) {
      return [...ROUTES, ...ADMIN_ROUTES];
    }
    return ROUTES;
  }, [isAdmin]);

  const closeMobileMenu = () => setIsMobileMenuOpen(false);

  useEffect(() => {
    setIsMobileMenuOpen(false);
  }, [location.pathname]);

  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="app-header-inner layout-container">
          <div className="brand-area">
            <button
              type="button"
              className="hamburger"
              aria-expanded={isMobileMenuOpen}
              onClick={() => setIsMobileMenuOpen((prev) => !prev)}
            >
              <span className="visually-hidden">Ouvrir le menu</span>
              <span />
              <span />
              <span />
            </button>
            <Link to="/" className="brand-title">
              Inventaire Épicerie
            </Link>
          </div>
          <nav className={`primary-nav ${isMobileMenuOpen ? 'is-open' : ''}`}>
            <ul className="primary-nav-list">
              {primaryNavLinks.map((link) => (
                <li key={link.to}>
                  <NavLink
                    to={link.to}
                    className={({ isActive }) =>
                      `primary-nav-link${isActive ? ' primary-nav-link-active' : ''}`
                    }
                    onClick={closeMobileMenu}
                  >
                    {link.label}
                  </NavLink>
                </li>
              ))}
            </ul>
          </nav>
          <div className="header-actions">
            <Link to="/dashboard" className="quick-action">
              Tableau de bord
            </Link>
            <Link to="/commandes" className="quick-action">
              Nouvelle commande
            </Link>
            <UserMenu onNavigate={closeMobileMenu} />
          </div>
        </div>
      </header>
      <div className="app-main-wrapper">
        <div className="breadcrumbs-wrapper layout-container">
          <Breadcrumbs routes={availableRoutes} />
        </div>
        <main className="app-main layout-container">
          <Suspense fallback={<div className="app-loading">Chargement…</div>}>
            <Routes>
              {availableRoutes.map(({ path, Component }) => (
                <Route key={path} path={path} element={<Component />} />
              ))}
            </Routes>
          </Suspense>
        </main>
      </div>
      <LoginModal />
    </div>
  );
}
