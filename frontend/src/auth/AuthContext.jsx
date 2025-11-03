import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import PropTypes from 'prop-types';
import {
  clearAuthToken,
  fetchCurrentUser,
  loginUser,
  setAuthToken,
} from '../api/client.js';

const STORAGE_KEY = 'inventaire-auth-state';

const decodeExpiration = (token) => {
  if (!token) {
    return null;
  }
  try {
    const parts = token.split('.');
    if (parts.length < 2) {
      return null;
    }
    const payload = JSON.parse(atob(parts[1].replace(/-/g, '+').replace(/_/g, '/')));
    if (typeof payload.exp !== 'number') {
      return null;
    }
    return payload.exp * 1000;
  } catch (error) {
    console.warn('Impossible de décoder la date expiration du jeton', error);
    return null;
  }
};

const AuthContext = createContext(undefined);

const loadStoredState = () => {
  if (typeof window === 'undefined') {
    return { token: null, user: null, expiresAt: null };
  }
  try {
    const raw = window.sessionStorage.getItem(STORAGE_KEY);
    if (!raw) {
      return { token: null, user: null, expiresAt: null };
    }
    const parsed = JSON.parse(raw);
    const storedExpiry = typeof parsed?.expiresAt === 'number' ? parsed.expiresAt : null;
    const expiresAt = storedExpiry ?? decodeExpiration(parsed?.token);
    if (expiresAt && Date.now() >= expiresAt) {
      window.sessionStorage.removeItem(STORAGE_KEY);
      return { token: null, user: null, expiresAt: null };
    }
    return {
      token: parsed?.token ?? null,
      user: parsed?.user ?? null,
      expiresAt,
    };
  } catch (error) {
    console.warn('Impossible de restaurer la session', error);
    return { token: null, user: null, expiresAt: null };
  }
};

export function AuthProvider({ children }) {
  const [authState, setAuthState] = useState(loadStoredState);
  const [isLoginOpen, setIsLoginOpen] = useState(false);
  const [isAuthenticating, setIsAuthenticating] = useState(false);
  const [authError, setAuthError] = useState(null);

  // Synchronise le token avec Axios et le stockage local.
  useEffect(() => {
    if (authState.token) {
      setAuthToken(authState.token);
    } else {
      clearAuthToken();
    }

    if (typeof window === 'undefined') {
      return;
    }

    if (authState.token) {
      window.sessionStorage.setItem(
        STORAGE_KEY,
        JSON.stringify({
          token: authState.token,
          user: authState.user,
          expiresAt: authState.expiresAt,
        }),
      );
    } else {
      window.sessionStorage.removeItem(STORAGE_KEY);
    }
  }, [authState.token, authState.user, authState.expiresAt]);

  const logout = useCallback(() => {
    setAuthState({ token: null, user: null, expiresAt: null });
    setAuthError(null);
    clearAuthToken();
  }, []);

  const refreshCurrentUser = useCallback(async () => {
    if (!authState.token) {
      return null;
    }
    if (authState.expiresAt && authState.expiresAt <= Date.now()) {
      logout();
      return null;
    }
    setIsAuthenticating(true);
    try {
      const user = await fetchCurrentUser();
      setAuthState((prev) => ({ ...prev, user }));
      return user;
    } catch (error) {
      logout();
      throw error;
    } finally {
      setIsAuthenticating(false);
    }
  }, [authState.token, authState.expiresAt, logout]);

  useEffect(() => {
    if (authState.token && !authState.user) {
      refreshCurrentUser().catch(() => {
        // Silence déjà géré par logout.
      });
    }
  }, [authState.token, authState.user, refreshCurrentUser]);

  const login = useCallback(
    async ({ username, password }) => {
      setIsAuthenticating(true);
      setAuthError(null);
      try {
        const response = await loginUser({ username, password });
        setAuthToken(response.access_token);
        setAuthState({
          token: response.access_token,
          user: response.user,
          expiresAt: decodeExpiration(response.access_token),
        });
        setIsLoginOpen(false);
        return response.user;
      } catch (error) {
        const detail = error?.response?.data?.detail;
        setAuthError(detail ?? "Échec de l'authentification");
        throw error;
      } finally {
        setIsAuthenticating(false);
      }
    },
    [],
  );

  const openLoginModal = useCallback(() => {
    setAuthError(null);
    setIsLoginOpen(true);
  }, []);

  const closeLoginModal = useCallback(() => {
    setIsLoginOpen(false);
    setAuthError(null);
  }, []);

  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }
    if (!authState.token || !authState.expiresAt) {
      return;
    }

    const remaining = authState.expiresAt - Date.now();
    if (remaining <= 0) {
      logout();
      openLoginModal();
      return;
    }

    const timer = window.setTimeout(() => {
      logout();
      openLoginModal();
    }, remaining);

    return () => {
      window.clearTimeout(timer);
    };
  }, [authState.token, authState.expiresAt, logout, openLoginModal]);

  const value = useMemo(
    () => ({
      user: authState.user,
      token: authState.token,
      sessionExpiresAt: authState.expiresAt,
      isLoginOpen,
      isAuthenticating,
      authError,
      login,
      logout,
      openLoginModal,
      closeLoginModal,
      refreshCurrentUser,
    }),
    [
      authState.user,
      authState.token,
      authState.expiresAt,
      isLoginOpen,
      isAuthenticating,
      authError,
      login,
      logout,
      openLoginModal,
      closeLoginModal,
      refreshCurrentUser,
    ],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

AuthProvider.propTypes = {
  children: PropTypes.node.isRequired,
};

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth doit être utilisé dans un AuthProvider');
  }
  return context;
}
