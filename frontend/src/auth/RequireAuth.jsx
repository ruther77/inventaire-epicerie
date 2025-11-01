import { useEffect, useRef } from 'react';
import PropTypes from 'prop-types';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from './AuthContext.jsx';

export default function RequireAuth({ children, requireAdmin = false }) {
  const { token, user, isAuthenticating, openLoginModal, sessionExpiresAt } = useAuth();
  const location = useLocation();
  const promptRef = useRef(false);

  const isExpired = sessionExpiresAt ? sessionExpiresAt <= Date.now() : false;
  const isAuthenticated = Boolean(token && user && !isExpired);

  useEffect(() => {
    if (isAuthenticated) {
      promptRef.current = false;
      return;
    }
    if (!isAuthenticating && !promptRef.current) {
      promptRef.current = true;
      openLoginModal();
    }
  }, [isAuthenticated, isAuthenticating, openLoginModal]);

  if (isAuthenticating) {
    return (
      <div className="protected-route-loading" role="status" aria-live="polite">
        Vérification de la session…
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/auth/login" state={{ from: location }} replace />;
  }

  if (requireAdmin && user.role !== 'admin') {
    return <Navigate to="/" replace />;
  }

  return children;
}

RequireAuth.propTypes = {
  children: PropTypes.node.isRequired,
  requireAdmin: PropTypes.bool,
};

RequireAuth.defaultProps = {
  requireAdmin: false,
};
