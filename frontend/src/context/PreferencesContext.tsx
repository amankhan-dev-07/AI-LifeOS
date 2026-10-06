import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { preferencesService } from '../services/services';
import { useAuth } from './AuthContext';
import {
  DEFAULT_TIME_FORMAT,
  DEFAULT_TIMEZONE,
  normalizeTimeFormat,
  normalizeTimezone,
  type TimeFormat,
} from '../utils/datetime';
import type { UserPreferences } from '../types';

export type ThemeMode = 'dark' | 'light';

interface PreferencesContextType {
  preferences: UserPreferences | null;
  theme: ThemeMode;
  /** IANA zone every timestamp in the app is displayed in. */
  timezone: string;
  /** 12h or 24h; affects display only, never stored instants. */
  timeFormat: TimeFormat;
  /** Whether the user has completed the first-time onboarding flow. */
  onboardingCompleted: boolean;
  /** Onboarding version — allows future migrations to re-prompt if flow changes. */
  onboardingVersion: number;
  /**
   * Whether a read has actually settled — as opposed to `loading`, which is
   * false both before the first request and after one completes.
   *
   * Consumers that must not act on a default value (onboarding decides whether
   * to take over the screen) need to tell "server says false" apart from "we
   * haven't asked yet". `loading` cannot express that: it starts false, so
   * gating on `!loading` fires immediately on a cold mount and reads the
   * not-yet-loaded default. This flag is set in a `finally`, so a failed read
   * settles it too rather than hanging a consumer that waits on it forever.
   */
  loaded: boolean;
  loading: boolean;
  saving: boolean;
  error: string | null;
  updatePreferences: (patch: Partial<UserPreferences>) => Promise<UserPreferences>;
  reload: () => Promise<void>;
  /** Mark onboarding as complete (persists to backend). */
  completeOnboarding: () => Promise<void>;
}

const PreferencesContext = createContext<PreferencesContextType | undefined>(undefined);

/**
 * Boot-time theme cache.
 *
 * The backend is authoritative for the theme *after* authentication, but the
 * document class has to be applied before the first paint to avoid a flash of
 * the wrong theme. This key is a cache only — it is overwritten by
 * `GET /preferences` on every authenticated bootstrap.
 */
const THEME_CACHE_KEY = 'ai_lifeos_theme';

function readCachedTheme(): ThemeMode {
  try {
    return localStorage.getItem(THEME_CACHE_KEY) === 'light' ? 'light' : 'dark';
  } catch {
    return 'dark';
  }
}

function writeCachedTheme(theme: ThemeMode) {
  try {
    localStorage.setItem(THEME_CACHE_KEY, theme);
  } catch {}
}

function applyTheme(theme: ThemeMode) {
  if (typeof document === 'undefined') return;
  document.documentElement.classList.toggle('dark', theme === 'dark');
}

function normalizeTheme(value: unknown): ThemeMode {
  return value === 'light' ? 'light' : 'dark';
}

export const PreferencesProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isAuthenticated, user } = useAuth();
  const [preferences, setPreferences] = useState<UserPreferences | null>(null);
  const [theme, setTheme] = useState<ThemeMode>(readCachedTheme);
  const [loading, setLoading] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Paint the cached theme immediately so the shell never flashes.
  useEffect(() => {
    applyTheme(theme);
  }, [theme]);

  const load = useCallback(async () => {
    if (!isAuthenticated) return;

    setLoading(true);
    try {
      const data = await preferencesService.get();
      setPreferences(data);
      const nextTheme = normalizeTheme(data.theme);
      setTheme(nextTheme);
      writeCachedTheme(nextTheme);
      setError(null);
    } catch {
      // A failed preferences read must not wipe the cached theme; keep the
      // current UI state and surface the failure to Settings.
      setError('Could not load preferences from the server.');
    } finally {
      setLoading(false);
      // Settled either way. `preferences` stays null on failure, so consumers
      // reading a boolean off it keep the documented default rather than
      // inheriting the previous user's value.
      setLoaded(true);
    }
  }, [isAuthenticated]);

  // Load on authenticated bootstrap, and clear user-scoped state on logout.
  useEffect(() => {
    if (isAuthenticated) {
      // Re-arm the gate before the read, so switching accounts (where
      // `isAuthenticated` stays true and only `user?.id` changes) cannot leave
      // the previous account's `loaded` value in place while the new one
      // fetches — that would let onboarding decide on stale state.
      setLoaded(false);
      load();
    } else {
      setPreferences(null);
      setError(null);
      setLoaded(false);
      const cached = readCachedTheme();
      setTheme(cached);
      applyTheme(cached);
    }
  }, [isAuthenticated, user?.id, load]);

  const updatePreferences = useCallback(
    async (patch: Partial<UserPreferences>) => {
      // Optimistic UI for responsiveness; the backend response is authoritative.
      if (patch.theme !== undefined) {
        const nextTheme = normalizeTheme(patch.theme);
        setTheme(nextTheme);
        applyTheme(nextTheme);
        writeCachedTheme(nextTheme);
      }
      setPreferences((prev) => (prev ? { ...prev, ...patch } : prev));
      setSaving(true);

      try {
        const saved = await preferencesService.update(patch);
        setPreferences(saved);
        const nextTheme = normalizeTheme(saved.theme);
        setTheme(nextTheme);
        applyTheme(nextTheme);
        writeCachedTheme(nextTheme);
        setError(null);
        return saved;
      } catch (e) {
        setError('Could not save preferences.');
        throw e;
      } finally {
        setSaving(false);
      }
    },
    [],
  );

  /**
   * Mark the first-time flow as finished.
   *
   * Throws when no preferences row is loaded rather than returning quietly:
   * `updatePreferences` already writes the row server-side (the backend's
   * `get_or_create` handles a missing row), so the only reason to bail here is
   * a client that never got a successful read. Returning silently would let
   * the caller advance as though the decision were saved, and the flow would
   * reappear on the next visit. Surfacing the failure lets the caller keep the
   * user on the screen with a real error.
   */
  const completeOnboarding = useCallback(async () => {
    if (!preferences) {
      throw new Error('Preferences are not loaded yet.');
    }

    await updatePreferences({ onboarding_completed: true });
  }, [preferences, updatePreferences]);

  // Memoized so consumers only re-render when preferences actually change.
  // Previously the derived values below were recomputed on every render of this
  // provider and a fresh object was handed to every consumer.
  const value = useMemo(
    () => ({
      preferences,
      theme,
      // Derived once here so every consumer renders the same zone and format
      // instead of each re-defaulting on its own.
      timezone: normalizeTimezone(preferences?.timezone),
      timeFormat: normalizeTimeFormat(preferences?.time_format),
      onboardingCompleted: preferences?.onboarding_completed ?? false,
      onboardingVersion: preferences?.onboarding_version ?? 1,
      loaded,
      loading,
      saving,
      error,
      updatePreferences,
      reload: load,
      completeOnboarding,
    }),
    [
      preferences,
      theme,
      loaded,
      loading,
      saving,
      error,
      updatePreferences,
      load,
      completeOnboarding,
    ]
  );

  return (
    <PreferencesContext.Provider value={value}>
      {children}
    </PreferencesContext.Provider>
  );
};

export const usePreferences = () => {
  const context = useContext(PreferencesContext);
  if (!context) throw new Error('usePreferences must be used within a PreferencesProvider');
  return context;
};