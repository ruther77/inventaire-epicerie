import { useEffect, useMemo, useState } from 'react';
import { Link, Route, Routes, useLocation } from 'react-router-dom';
import HomePage from './pages/HomePage.jsx';
import CatalogPage from './pages/CatalogPage.jsx';
import PosPage from './pages/PosPage.jsx';
import ReportsPage from './pages/ReportsPage.jsx';
import LegacyToolsPage from './pages/LegacyToolsPage.jsx';
import UserManagementPage from './pages/UserManagementPage.jsx';
import OrdersPage from './pages/OrdersPage.jsx';
import PromotionsPage from './pages/PromotionsPage.jsx';
import DashboardPage from './pages/DashboardPage.jsx';
import SupportPage from './pages/SupportPage.jsx';
import AccountPage from './pages/AccountPage.jsx';
import CartPage from './pages/CartPage.jsx';
import FavoritesPage from './pages/FavoritesPage.jsx';
import NotificationsPage from './pages/NotificationsPage.jsx';
import SettingsPage from './pages/SettingsPage.jsx';
import LoginPage from './pages/LoginPage.jsx';
import SignupPage from './pages/SignupPage.jsx';
import CategoriesPage from './pages/CategoriesPage.jsx';
import ClientsPage from './pages/ClientsPage.jsx';
import SuppliersPage from './pages/SuppliersPage.jsx';
import ProcurementsPage from './pages/ProcurementsPage.jsx';
import { useAuth } from './auth/AuthContext.jsx';
import LoginModal from './components/LoginModal.jsx';
import MegaMenu from './components/MegaMenu.jsx';
import Breadcrumbs from './components/Breadcrumbs.jsx';
import UserMenu from './components/UserMenu.jsx';

const ROUTES = [
  { path: '/', element: <HomePage />, breadcrumb: 'Accueil', section: 'home' },
  {
    path: '/dashboard',
    element: <DashboardPage />,
    breadcrumb: 'Tableau de bord',
    section: 'explorer',
  },
  {
    path: '/catalogue',
    element: <CatalogPage />,
    breadcrumb: 'Catalogue',
    section: 'catalogue',
    badge: { label: 'Nouveau', variant: 'new' },
  },
  {
    path: '/commandes',
    element: <OrdersPage />,
    breadcrumb: 'Commandes',
    section: 'catalogue',
  },
  {
    path: '/categories',
    element: <CategoriesPage />,
    breadcrumb: 'Catégories',
    section: 'catalogue',
  },
  {
    path: '/approvisionnements',
    element: <ProcurementsPage />,
    breadcrumb: 'Approvisionnements',
    section: 'catalogue',
  },
  {
    path: '/promotions',
    element: <PromotionsPage />,
    breadcrumb: 'Promotions',
    section: 'catalogue',
    badge: { label: 'Promo', variant: 'promo' },
  },
  {
    path: '/clients',
    element: <ClientsPage />,
    breadcrumb: 'Clients',
    section: 'relations',
  },
  {
    path: '/fournisseurs',
    element: <SuppliersPage />,
    breadcrumb: 'Fournisseurs',
    section: 'relations',
  },
  {
    path: '/pos',
    element: <PosPage />,
    breadcrumb: 'Point de vente',
    section: 'explorer',
  },
  {
    path: '/explorer/rapports',
    element: <ReportsPage />,
    breadcrumb: 'Analyses',
    section: 'explorer',
    badge: { label: 'Bêta', variant: 'beta' },
  },
  {
    path: '/explorer/outils',
    element: <LegacyToolsPage />,
    breadcrumb: 'Outils Streamlit',
    section: 'explorer',
  },
  {
    path: '/aide',
    element: <SupportPage />,
    breadcrumb: 'Aide',
    section: 'support',
  },
  {
    path: '/compte',
    element: <AccountPage />,
    breadcrumb: 'Espace personnel',
    section: 'account',
  },
  {
    path: '/panier',
    element: <CartPage />,
    breadcrumb: 'Panier',
    section: 'account',
  },
  {
    path: '/favoris',
    element: <FavoritesPage />,
    breadcrumb: 'Favoris',
    section: 'account',
  },
  {
    path: '/notifications',
    element: <NotificationsPage />,
    breadcrumb: 'Notifications',
    section: 'account',
  },
  {
    path: '/parametres',
    element: <SettingsPage />,
    breadcrumb: 'Paramètres',
    section: 'account',
  },
  {
    path: '/auth/login',
    element: <LoginPage />,
    breadcrumb: 'Connexion',
    section: 'auth',
  },
  {
    path: '/auth/signup',
    element: <SignupPage />,
    breadcrumb: 'Créer un compte',
    section: 'auth',
    badge: { label: 'Nouveau', variant: 'new' },
  },
];

const ADMIN_ROUTES = [
  {
    path: '/users',
    element: <UserManagementPage />,
    breadcrumb: 'Comptes utilisateurs',
    section: 'administration',
    adminOnly: true,
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
        <Routes>
          {availableRoutes.map((route) => (
            <Route key={route.path} path={route.path} element={route.element} />
          ))}
        </Routes>
      </main>
      <LoginModal />
    </div>
  );
}
