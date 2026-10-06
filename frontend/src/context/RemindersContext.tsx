import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { reminderService } from '../services/services';
import { parseNaiveUtc } from '../utils/datetime';
import { useAuth } from './AuthContext';
import type { Reminder } from '../types';

interface RemindersContextType {
  reminders: Reminder[];
  /** Pending reminders, soonest first — the actionable queue. */
  pending: Reminder[];
  /** Pending reminders whose time has passed but not yet been notified. */
  overdueCount: number;
  loading: boolean;
  error: string | null;
  createReminder: (data: {
    title: string;
    message?: string | null;
    remind_at: string;
    task_id?: number | null;
    habit_id?: number | null;
    planner_event_id?: number | null;
  }) => Promise<Reminder>;
  updateReminder: (id: number, data: Partial<Reminder>) => Promise<Reminder>;
  deleteReminder: (id: number) => Promise<void>;
  reload: () => Promise<void>;
}

const RemindersContext = createContext<RemindersContextType | undefined>(undefined);

const isPending = (reminder: Reminder): boolean => reminder.status === 'pending';

/**
 * Single source of truth for reminders, shared by the ReminderModal and the
 * "Remind me" buttons in the Tasks and Planner views, so the list is fetched
 * once per authenticated session rather than per component.
 */
export const RemindersProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isAuthenticated, user } = useAuth();
  const [reminders, setReminders] = useState<Reminder[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!isAuthenticated) return;

    setLoading(true);
    try {
      const data = await reminderService.getReminders();
      setReminders(Array.isArray(data) ? data : []);
      setError(null);
    } catch {
      setError('Could not load reminders.');
    } finally {
      setLoading(false);
    }
  }, [isAuthenticated]);

  useEffect(() => {
    if (isAuthenticated) {
      load();
    } else {
      setReminders([]);
      setError(null);
    }
  }, [isAuthenticated, user?.id, load]);

  const createReminder = useCallback<RemindersContextType['createReminder']>(
    async (data) => {
      // The server response is authoritative — the row is only added to local
      // state after the backend confirms the write.
      const created = await reminderService.createReminder(data);
      setReminders((prev) =>
        [...prev, created].sort(
          (a, b) => a.remind_at.localeCompare(b.remind_at) || a.id - b.id,
        ),
      );
      setError(null);
      return created;
    },
    [],
  );

  const updateReminder = useCallback<RemindersContextType['updateReminder']>(
    async (id, data) => {
      const updated = await reminderService.updateReminder(id, data);
      setReminders((prev) =>
        prev
          .map((reminder) => (reminder.id === id ? updated : reminder))
          .sort((a, b) => a.remind_at.localeCompare(b.remind_at) || a.id - b.id),
      );
      setError(null);
      return updated;
    },
    [],
  );

  const deleteReminder = useCallback<RemindersContextType['deleteReminder']>(async (id) => {
    await reminderService.deleteReminder(id);
    // Removed from local state rather than re-fetched, so the list a consumer
    // renders updates in the same pass as the delete — no intermediate frame
    // where the deleted row is still on screen.
    setReminders((prev) => prev.filter((reminder) => reminder.id !== id));
  }, []);

  const pending = useMemo(
    () =>
      reminders
        .filter(isPending)
        .sort((a, b) => a.remind_at.localeCompare(b.remind_at) || a.id - b.id),
    [reminders],
  );

  const overdueCount = useMemo(() => {
    const now = Date.now();
    // The backend sends naive UTC, so parse it explicitly rather than letting
    // `new Date(string)` guess the zone and shift it.
    return pending.filter(
      (reminder) => parseNaiveUtc(reminder.remind_at).getTime() <= now,
    ).length;
  }, [pending]);

  // Memoized so consumers only re-render when reminder state actually changes.
  const value = useMemo(
    () => ({
      reminders,
      pending,
      overdueCount,
      loading,
      error,
      createReminder,
      updateReminder,
      deleteReminder,
      reload: load,
    }),
    [
      reminders,
      pending,
      overdueCount,
      loading,
      error,
      createReminder,
      updateReminder,
      deleteReminder,
      load,
    ]
  );

  return (
    <RemindersContext.Provider value={value}>
      {children}
    </RemindersContext.Provider>
  );
};

export const useReminders = () => {
  const context = useContext(RemindersContext);
  if (!context) throw new Error('useReminders must be used within a RemindersProvider');
  return context;
};