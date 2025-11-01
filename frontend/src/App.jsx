import { Suspense, lazy, useEffect, useMemo, useState } from 'react';
import { Link, Route, Routes, useLocation } from 'react-router-dom';
import { useAuth } from './auth/AuthContext.jsx';
import RequireAuth from './auth/RequireAuth.jsx';
import LoginModal from './components/LoginModal.jsx';
import MegaMenu from './components/MegaMenu.jsx';
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

const MEGA_MENU_SECTIONS = [
  {
    id: 'catalogue',
    label: 'Catalogue',
    subtitle: 'Gérer vos produits',
    title: 'Catalogue & achats',
    description: 'Filtrez, préparez vos commandes et mettez en avant vos promotions.',
    featuredActions: [
      { to: '/catalogue', label: 'Parcourir le catalogue', badge: { label: 'Nouveau', variant: 'new' } },
      { to: '/commandes', label: 'Créer une commande' },
      { to: '/approvisionnements', label: 'Suivre les approvisionnements' },
      { to: '/promotions', label: 'Voir les promotions', badge: { label: 'Promo', variant: 'promo' } },
    ],
    items: [
      {
        to: '/catalogue',
        label: 'Catalogue produits',
        description: 'Recherchez, filtrez et sauvegardez vos vues personnalisées.',
      },
      {
        to: '/categories',
        label: 'Catégories',
        description: 'Organisez vos références par familles et mettez-les à jour.',
      },
      {
        to: '/commandes',
        label: 'Commandes',
        description: 'Suivez vos commandes et reprenez les brouillons.',
      },
      {
        to: '/approvisionnements',
        label: 'Approvisionnements',
        description: 'Planifiez et consignez vos réceptions fournisseurs.',
      },
      {
        to: '/promotions',
        label: 'Promotions',
        description: 'Identifiez les offres à pousser en magasin.',
        badge: { label: 'Promo', variant: 'promo' },
      },
      {
        to: '/panier',
        label: 'Panier',
        description: 'Retrouvez vos sélections d’achats en attente.',
      },
    ],
  },
  {
    id: 'relations',
    label: 'Contacts',
    subtitle: 'Clients & fournisseurs',
    title: 'Relations commerciales',
    description: 'Retrouvez rapidement les interlocuteurs clés de votre activité.',
    featuredActions: [
      { to: '/clients', label: 'Répertoire clients' },
      { to: '/fournisseurs', label: 'Carnet fournisseurs' },
    ],
    items: [
      {
        to: '/clients',
        label: 'Clients',
        description: 'Coordonnées, préférences et suivi des commandes.',
      },
      {
        to: '/fournisseurs',
        label: 'Fournisseurs',
        description: 'Contacts privilégiés pour vos réassorts.',
      },
    ],
  },
  {
    id: 'explorer',
    label: 'Explorer',
    subtitle: 'Analyser & piloter',
    title: 'Explorer & analyser',
    description: 'Consolidez vos indicateurs et ouvrez les vues métiers à la demande.',
    featuredActions: [
      { to: '/dashboard', label: 'Ouvrir le tableau de bord' },
      { to: '/explorer/rapports', label: 'Consulter les rapports', badge: { label: 'Bêta', variant: 'beta' } },
      { to: '/pos', label: 'Point de vente' },
    ],
    items: [
      {
        to: '/dashboard',
        label: 'Tableau de bord',
        description: 'Cartes d’accès aux modules Inventaire, Commandes et Analyses.',
      },
      {
        to: '/explorer/rapports',
        label: 'Analyses & rapports',
        description: 'Visualisez la répartition des stocks par catégorie.',
        badge: { label: 'Bêta', variant: 'beta' },
      },
      {
        to: '/explorer/outils',
        label: 'Outils Streamlit',
        description: 'Retrouvez les applications historiques pendant la migration.',
      },
      {
        to: '/aide',
        label: 'Centre d’aide',
        description: 'Guides, FAQ et contact support.',
      },
    ],
  },
];

export default function App() {
  const { user } = useAuth();
  const location = useLocation();
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  const isAdmin = user?.role === 'admin';

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
        <MegaMenu
          sections={MEGA_MENU_SECTIONS}
          isMobileOpen={isMobileMenuOpen}
          onToggleMobile={setIsMobileMenuOpen}
          onNavigate={closeMobileMenu}
        />
        <div className="header-actions">
          <Link to="/dashboard" className="quick-action">
            Tableau de bord
          </Link>
          <Link to="/commandes" className="quick-action">
            Nouvelle commande
          </Link>
          <UserMenu onNavigate={closeMobileMenu} />
        </div>
      </header>
      <Breadcrumbs routes={availableRoutes} />
      <main>
        <Suspense fallback={<div className="app-loading">Chargement…</div>}>
          <Routes>
            {availableRoutes.map(({ path, Component }) => (
              <Route key={path} path={path} element={<Component />} />
            ))}
          </Routes>
        </Suspense>
      </main>
      <LoginModal />
    </div>
  );
}
