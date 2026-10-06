import React, { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';
import { notificationService } from '../services/services';
import { useAuth } from './AuthContext';
import type { AppNotification } from '../types';

/**
 * How often the bell quietly re-reads /notifications while the tab is open.
 *
 * The backend scheduler ticks once a minute, so a shorter interval could not
 * surface a due reminder any sooner — it would only add requests. Matching the
 * scheduler's own cadence means one request per tick at most, and a reminder
 * appears within a minute of coming due.
 */
const REFRESH_INTERVAL_MS = 60_000;

interface NotificationsContextType {
  notifications: AppNotification[];
  unreadCount: number;
  loading: boolean;
  error: string | null;
  markRead: (id: number) => Promise<void>;
  markAllRead: () => Promise<void>;
  reload: () => Promise<void>;
}

const NotificationsContext = createContext<NotificationsContextType | undefined>(undefined);

/**
 * Single source of truth for notification state, shared by the header bell
 * (badge + dropdown) so the list is fetched once per authenticated session
 * rather than per component.
 */
export const NotificationsProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isAuthenticated, user } = useAuth();
  const [notifications, setNotifications] = useState<AppNotification[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // A background refresh must never blank the bell: `reload` flips the loading
  // flag the dropdown renders as a spinner and an empty list, so a periodic
  // fetch would visibly reset the UI every minute. This keeps the quiet path
  // silent and leaves the spinner for the initial load and manual refresh.
  const loadRef = useRef<((options?: { silent?: boolean }) => Promise<void>) | null>(null);

  const load = useCallback(async (options: { silent?: boolean } = {}) => {
    if (!isAuthenticated) return;

    if (!options.silent) setLoading(true);
    try {
      const data = await notificationService.getNotifications();
      setNotifications(data);
      setError(null);
    } catch {
      setError('Could not load notifications.');
    } finally {
      if (!options.silent) setLoading(false);
    }
  }, [isAuthenticated]);

  loadRef.current = load;

  useEffect(() => {
    if (isAuthenticated) {
      load();
    } else {
      setNotifications([]);
      setError(null);
    }
  }, [isAuthenticated, user?.id, load]);

  /**
   * Quiet refresh while the session is open.
   *
   * Reminders are delivered by a backend background task, so nothing tells the
   * browser a notification exists. Two lifecycle events cover every case
   * without a busy loop:
   *
   * - a 60s interval, matching the scheduler's own tick, so a reminder shows
   *   up within a minute of coming due;
   * - `visibilitychange` / `focus`, so returning to a long-idle tab fills in
   *   everything it missed immediately instead of waiting out the interval.
   *
   * The interval is skipped while the document is hidden, and the visibility
   * handler refreshes on return, so a backgrounded tab costs no requests. The
   * fetch is the same single `GET /notifications` the app already issues, and
   * state is replaced wholesale from that response — so the unread badge is
   * derived from server truth (`unreadCount`, below) rather than incremented,
   * and a re-fetch can never duplicate an entry.
   */
  useEffect(() => {
    if (!isAuthenticated) return;

    const refresh = () => {
      if (document.visibilityState === 'hidden') return;
      void loadRef.current?.({ silent: true });
    };

    const intervalId = window.setInterval(refresh, REFRESH_INTERVAL_MS);
    const onVisibility = () => {
      if (document.visibilityState === 'visible') refresh();
    };

    document.addEventListener('visibilitychange', onVisibility);
    window.addEventListener('focus', refresh);

    return () => {
      window.clearInterval(intervalId);
      document.removeEventListener('visibilitychange', onVisibility);
      window.removeEventListener('focus', refresh);
    };
  }, [isAuthenticated]);

  const markRead = useCallback(async (id: number) => {
    // Optimistic: the badge should respond immediately.
    setNotifications((prev) =>
      prev.map((n) => (n.id === id && !n.is_read ? { ...n, is_read: true } : n)),
    );
    try {
      await notificationService.markRead(id);
    } catch {
      // Roll back to server truth on failure.
      await load();
    }
  }, [load]);

  const markAllRead = useCallback(async () => {
    const snapshot = notifications;
    setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
    try {
      await notificationService.markAllRead();
    } catch {
      setNotifications(snapshot);
      setError('Could not mark all notifications as read.');
    }
  }, [notifications]);

  const unreadCount = useMemo(() => notifications.filter((n) => !n.is_read).length, [notifications]);

  // Stable identity. Previously this was an inline `() => load()`, a new
  // function on every render, so every consumer of the notifications context
  // re-rendered whenever any part of this provider re-rendered.
  const reload = useCallback(() => load(), [load]);

  // Memoized so consumers only re-render when the notification state actually
  // changes, rather than on every provider render.
  const value = useMemo(
    () => ({
      notifications,
      unreadCount,
      loading,
      error,
      markRead,
      markAllRead,
      reload,
    }),
    [notifications, unreadCount, loading, error, markRead, markAllRead, reload]
  );

  return (
    <NotificationsContext.Provider value={value}>
      {children}
    </NotificationsContext.Provider>
  );
};

export const useNotifications = () => {
  const context = useContext(NotificationsContext);
  if (!context) throw new Error('useNotifications must be used within a NotificationsProvider');
  return context;
};