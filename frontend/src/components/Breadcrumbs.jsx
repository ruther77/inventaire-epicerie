import PropTypes from 'prop-types';
import { Link, useLocation } from 'react-router-dom';

export default function Breadcrumbs({ routes }) {
  const location = useLocation();
  const pathname = location.pathname || '/';

  const crumbs = [];
  const routeMap = routes.reduce((accumulator, route) => {
    accumulator[route.path] = route;
    return accumulator;
  }, {});

  let accumulatedPath = '';
  const segments = pathname.split('/').filter(Boolean);

  crumbs.push({ path: '/', label: routeMap['/']?.breadcrumb ?? 'Accueil' });

  segments.forEach((segment) => {
    accumulatedPath += `/${segment}`;
    const route = routeMap[accumulatedPath];
    if (route?.breadcrumb) {
      crumbs.push({ path: accumulatedPath, label: route.breadcrumb, badge: route.badge });
    }
  });

  const isSingle = crumbs.length <= 1;

  return (
    <nav className={`breadcrumbs ${isSingle ? 'breadcrumbs-single' : ''}`} aria-label="Fil d'Ariane">
      <ol>
        {crumbs.map((crumb, index) => {
          const isLast = index === crumbs.length - 1;
          if (isLast) {
            return (
              <li key={crumb.path} aria-current="page">
                <span>{crumb.label}</span>
                {crumb.badge && <span className={`badge badge-${crumb.badge.variant}`}>{crumb.badge.label}</span>}
              </li>
            );
          }
          return (
            <li key={crumb.path}>
              <Link to={crumb.path}>{crumb.label}</Link>
              {crumb.badge && <span className={`badge badge-${crumb.badge.variant}`}>{crumb.badge.label}</span>}
              <span className="breadcrumbs-separator">/</span>
            </li>
          );
        })}
      </ol>
    </nav>
  );
}

Breadcrumbs.propTypes = {
  routes: PropTypes.arrayOf(
    PropTypes.shape({
      path: PropTypes.string.isRequired,
      breadcrumb: PropTypes.string,
      badge: PropTypes.shape({
        label: PropTypes.string.isRequired,
        variant: PropTypes.string,
      }),
    }),
  ).isRequired,
};
