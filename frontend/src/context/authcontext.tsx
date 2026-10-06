import React, { createContext, useCallback, useContext, useMemo, useRef, useState, useEffect } from 'react';
import { User } from '../types';
import { authService } from '../services/services';

interface AuthContextType {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, pass: string) => Promise<void>;
  register: (data: { email: string; name: string; password: string }) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(localStorage.getItem('ai_lifeos_token'));
  const [isLoading, setIsLoading] = useState<boolean>(true);

  // The token whose `/users/me` has already been fetched.
  //
  // Both the bootstrap effect and `login` hydrate the user, and both are
  // triggered by `token` changing. Without this guard a fresh login issued two
  // identical `/users/me` requests: one from `login` and one from the effect
  // that re-ran on the new token. Recording the hydrated token lets the effect
  // skip work that has already been done.
  const hydratedTokenRef = useRef<string | null>(null);

  useEffect(() => {
    const initAuth = async () => {
      if (!token) {
        setIsLoading(false);
        return;
      }

      // Already hydrated this exact token (i.e. `login` just did it).
      if (hydratedTokenRef.current === token) {
        setIsLoading(false);
        return;
      }

      try {
        const userData = await authService.getMe();
        hydratedTokenRef.current = token;
        setUser(userData);
      } catch {
        hydratedTokenRef.current = null;
        authService.logout();
        setToken(null);
        setUser(null);
      } finally {
        setIsLoading(false);
      }
    };
    initAuth();
  }, [token]);

  useEffect(() => {
    const handleUnauthorized = () => {
      hydratedTokenRef.current = null;
      authService.logout();
      setToken(null);
      setUser(null);
    };

    window.addEventListener('ai_lifeos:unauthorized', handleUnauthorized);
    return () => {
      window.removeEventListener('ai_lifeos:unauthorized', handleUnauthorized);
    };
  }, []);

  const login = useCallback(async (email: string, pass: string) => {
    const res = await authService.login(email, pass);

    // Hydrate here rather than deferring to the effect, because callers await
    // `login()` and then navigate straight to `/app` — `RequireAuth` redirects
    // an unauthenticated visitor away, so the user has to be in place before
    // this promise resolves. Marking the token as hydrated first is what stops
    // the effect above from issuing a second identical request.
    try {
      const userData = await authService.getMe();
      hydratedTokenRef.current = res.access_token;
      setToken(res.access_token);
      setUser(userData);
    } catch (e) {
      hydratedTokenRef.current = null;
      authService.logout();
      throw e;
    }
  }, []);

  const register = useCallback(async (data: { email: string; name: string; password: string }) => {
    await authService.register(data);
    await login(data.email, data.password);
  }, [login]);

  const logout = useCallback(() => {
    hydratedTokenRef.current = null;
    authService.logout();
    setToken(null);
    setUser(null);
  }, []);

  // A fresh object literal here would re-render every consumer on each render
  // of this provider. Memoized so consumers only re-render when auth state
  // actually changes.
  const value = useMemo(
    () => ({
      user,
      token,
      isAuthenticated: !!user,
      isLoading,
      login,
      register,
      logout,
    }),
    [user, token, isLoading, login, register, logout]
  );

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used within an AuthProvider');
  return context;
};
