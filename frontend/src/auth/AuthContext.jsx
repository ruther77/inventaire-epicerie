import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import PropTypes from 'prop-types';
import {
  clearAuthToken,
  fetchCurrentUser,
  loginUser,
  setAuthToken,
} from '../api/client.js';

const STORAGE_KEY = 'inventaire-auth-state';

const AuthContext = createContext(undefined);

const loadStoredState = () => {
  if (typeof window === 'undefined') {
    return { token: null, user: null };
  }
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      return { token: null, user: null };
    }
    const parsed = JSON.parse(raw);
    return {
      token: parsed?.token ?? null,
      user: parsed?.user ?? null,
    };
  } catch (error) {
    console.warn('Impossible de restaurer la session', error);
    return { token: null, user: null };
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
      window.localStorage.setItem(
        STORAGE_KEY,
        JSON.stringify({ token: authState.token, user: authState.user }),
      );
    } else {
      window.localStorage.removeItem(STORAGE_KEY);
    }
  }, [authState.token, authState.user]);

  const logout = useCallback(() => {
    setAuthState({ token: null, user: null });
    setAuthError(null);
    clearAuthToken();
  }, []);

  const refreshCurrentUser = useCallback(async () => {
    if (!authState.token) {
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
  }, [authState.token, logout]);

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
        setAuthState({ token: response.access_token, user: response.user });
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

  const value = useMemo(
    () => ({
      user: authState.user,
      token: authState.token,
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
