import { NavLink, Route, Routes } from 'react-router-dom';
import HomePage from './pages/HomePage.jsx';
import InventoryPage from './pages/InventoryPage.jsx';
import PosPage from './pages/PosPage.jsx';
import ReportsPage from './pages/ReportsPage.jsx';
import LegacyToolsPage from './pages/LegacyToolsPage.jsx';

const routes = [
  { path: '/', label: 'Vitrine', element: <HomePage /> },
  { path: '/inventory', label: 'Approvisionnement', element: <InventoryPage /> },
  { path: '/pos', label: 'Point de vente', element: <PosPage /> },
  { path: '/reports', label: 'Rapports', element: <ReportsPage /> },
  { path: '/legacy-tools', label: 'Outils Streamlit', element: <LegacyToolsPage /> }
];

export default function App() {
  return (
    <>
      <header>
        <h1>Inventaire Épicerie</h1>
        <p>Nouvelle interface SPA propulsée par React Router</p>
        <nav>
          {routes.map((route) => (
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
          {routes.map((route) => (
            <Route key={route.path} path={route.path} element={route.element} />
          ))}
        </Routes>
      </main>
    </>
  );
}
