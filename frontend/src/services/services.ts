import { apiClient } from './api';
import { parseAmountToCents } from '../utils/money';
import { toLocalDateKey } from '../utils/datetime';
import type {
  AppNotification,
  DashboardResponse,
  Goal,
  Habit,
  IntelligenceResponse,
  Note,
  PlannerEvent,
  PlannerEventType,
  Reminder,
  ReminderStatus,
  SearchResponse,
  Task,
  Transaction,
  TransactionType,
  UserPreferences,
} from '../types';

/**
 * Normalize a Transaction coming off the wire. The backend serializes
 * `Numeric(12,2)` as a JSON string ("120.00"); components expect a number, so
 * the value is parsed to a finite float here and nowhere else.
 */
function toTransaction(raw: any): Transaction {
  return {
    ...raw,
    amount: parseAmountToCents(raw.amount) / 100,
  } as Transaction;
}

export const authService = {
  async login(email: string, password: string) {
    const response = await apiClient.post('/auth/login', { email, password });
    if (response.data.access_token) {
      localStorage.setItem('ai_lifeos_token', response.data.access_token);
    }
    return response.data;
  },

  async register(userData: { email: string; name: string; password: string }) {
    const payload = { email: userData.email, full_name: userData.name, password: userData.password };
    const response = await apiClient.post('/auth/register', payload);
    return response.data;
  },

  async getMe() {
    const response = await apiClient.get('/users/me');
    return response.data;
  },

  logout() {
    localStorage.removeItem('ai_lifeos_token');
  }
};

export const dashboardService = {
  async getOverview(): Promise<DashboardResponse> {
    const res = await apiClient.get('/dashboard');
    return res.data;
  }
};

/**
 * LifeOS Intelligence.
 *
 * A single derived read: the backend snapshots the authenticated user's own
 * records and returns explainable insights computed from them. Ownership
 * comes from the bearer token, so there is deliberately no user_id parameter.
 *
 * Nothing here is cached client-side and there is no polling — a caller
 * re-fetches when it wants fresher data, which is the same lifecycle the rest
 * of the app already uses.
 */
export const intelligenceService = {
  async getOverview(signal?: AbortSignal): Promise<IntelligenceResponse> {
    const res = await apiClient.get<IntelligenceResponse>('/intelligence', { signal });
    return res.data;
  }
};

export const taskService = {
  async getTasks(): Promise<Task[]> {
    const res = await apiClient.get('/tasks');
    return res.data;
  },
  async createTask(data: Partial<Task> & { title: string }) {
    const res = await apiClient.post('/tasks', data);
    return res.data;
  },
  async updateTask(id: number, data: Partial<Task>) {
    const res = await apiClient.put(`/tasks/${id}`, data);
    return res.data;
  },
  async deleteTask(id: number) {
    const res = await apiClient.delete(`/tasks/${id}`);
    return res.data;
  }
};

export const goalService = {
  async getGoals(): Promise<Goal[]> {
    const res = await apiClient.get('/goals');
    return res.data;
  },
  async createGoal(data: Partial<Goal> & { title: string }) {
    const res = await apiClient.post('/goals', data);
    return res.data;
  },
  async updateGoal(id: number, data: Partial<Goal>) {
    const res = await apiClient.put(`/goals/${id}`, data);
    return res.data;
  },
  async deleteGoal(id: number) {
    const res = await apiClient.delete(`/goals/${id}`);
    return res.data;
  }
};

export const habitService = {
  async getHabits(): Promise<Habit[]> {
    const res = await apiClient.get('/habits');
    return res.data;
  },
  async createHabit(data: Partial<Habit> & { title: string }) {
    const res = await apiClient.post('/habits', data);
    return res.data;
  },
  async updateHabit(id: number, data: Partial<Habit>) {
    const res = await apiClient.put(`/habits/${id}`, data);
    return res.data;
  },
  async completeHabit(id: number) {
    const res = await apiClient.post(`/habits/${id}/complete`, { completed_date: toLocalDateKey(new Date()) });
    return res.data;
  },
  async deleteHabit(id: number) {
    const res = await apiClient.delete(`/habits/${id}`);
    return res.data;
  }
};

export const aiService = {
  async queryBrain(prompt: string, conversationId?: string) {
    const res = await apiClient.post('/ai/chat', {
      message: prompt,
      conversation_id: conversationId
    });
    return res.data;
  },

  async confirmAction(planId: string, conversationId?: string) {
    const res = await apiClient.post('/ai/confirm', {
      plan_id: planId,
      conversation_id: conversationId
    });
    return res.data;
  },

  async cancelAction(planId: string, conversationId?: string) {
    const res = await apiClient.post('/ai/cancel', {
      plan_id: planId,
      conversation_id: conversationId
    });
    return res.data;
  }
};

/**
 * Planner events are the persistent source of truth for the Planner view.
 * Ownership is derived from the access token server-side; no user_id is ever
 * sent from the client.
 */
export const plannerService = {
  async getEvents(params: {
    startDate?: string;
    endDate?: string;
    eventType?: PlannerEventType | null;
  } = {}): Promise<PlannerEvent[]> {
    const res = await apiClient.get('/planner-events', {
      params: {
        ...(params.startDate ? { start_date: params.startDate } : {}),
        ...(params.endDate ? { end_date: params.endDate } : {}),
        ...(params.eventType ? { event_type: params.eventType } : {}),
      },
    });
    return Array.isArray(res.data) ? res.data : [];
  },
  async createEvent(data: {
    title: string;
    description?: string | null;
    event_date: string;
    start_time: string;
    end_time: string;
    event_type: PlannerEventType;
    task_id?: number | null;
    habit_id?: number | null;
  }): Promise<PlannerEvent> {
    const res = await apiClient.post('/planner-events', data);
    return res.data;
  },
  async updateEvent(id: number, data: Partial<PlannerEvent>): Promise<PlannerEvent> {
    const res = await apiClient.patch(`/planner-events/${id}`, data);
    return res.data;
  },
  async deleteEvent(id: number) {
    await apiClient.delete(`/planner-events/${id}`);
  }
};

export const noteService = {
  async getNotes(params: { isArchived?: boolean; tag?: string | null } = {}): Promise<Note[]> {
    const res = await apiClient.get('/notes', {
      params: {
        ...(typeof params.isArchived === 'boolean' ? { is_archived: params.isArchived } : {}),
        ...(params.tag ? { tag: params.tag } : {}),
      },
    });
    return Array.isArray(res.data) ? res.data : [];
  },
  async createNote(data: {
    title: string;
    content?: string;
    tag?: string;
    is_pinned?: boolean;
    goal_id?: number | null;
    task_id?: number | null;
  }): Promise<Note> {
    const res = await apiClient.post('/notes', data);
    return res.data;
  },
  async updateNote(id: number, data: Partial<Note>): Promise<Note> {
    const res = await apiClient.patch(`/notes/${id}`, data);
    return res.data;
  },
  async deleteNote(id: number) {
    await apiClient.delete(`/notes/${id}`);
  }
};

export const transactionService = {
  async getTransactions(params: {
    startDate?: string;
    endDate?: string;
    type?: TransactionType | null;
    category?: string | null;
  } = {}): Promise<Transaction[]> {
    const res = await apiClient.get('/transactions', {
      params: {
        ...(params.startDate ? { start_date: params.startDate } : {}),
        ...(params.endDate ? { end_date: params.endDate } : {}),
        ...(params.type ? { type: params.type } : {}),
        ...(params.category ? { category: params.category } : {}),
      },
    });
    return Array.isArray(res.data) ? res.data.map(toTransaction) : [];
  },
  async createTransaction(data: {
    title: string;
    amount: number;
    type: TransactionType;
    category?: string;
    transaction_date: string;
    notes?: string | null;
  }): Promise<Transaction> {
    const res = await apiClient.post('/transactions', data);
    return toTransaction(res.data);
  },
  async updateTransaction(id: number, data: Partial<Transaction>): Promise<Transaction> {
    const res = await apiClient.patch(`/transactions/${id}`, data);
    return toTransaction(res.data);
  },
  async deleteTransaction(id: number) {
    await apiClient.delete(`/transactions/${id}`);
  }
};

export const notificationService = {
  async getNotifications(params: { isRead?: boolean } = {}): Promise<AppNotification[]> {
    const res = await apiClient.get('/notifications', {
      params: {
        ...(typeof params.isRead === 'boolean' ? { is_read: params.isRead } : {}),
      },
    });
    return Array.isArray(res.data) ? res.data : [];
  },
  async getUnreadNotifications(): Promise<AppNotification[]> {
    const res = await apiClient.get('/notifications/unread');
    return Array.isArray(res.data) ? res.data : [];
  },
  async markRead(id: number): Promise<AppNotification> {
    const res = await apiClient.post(`/notifications/${id}/read`);
    return res.data;
  },
  async markAllRead() {
    await apiClient.post('/notifications/read-all');
  }
};

/**
 * Persistent reminders. Ownership is derived from the bearer token server
 * side, so there is deliberately no user_id in any of these calls — and
 * `remind_at` is sent as a naive-UTC string to match the backend's
 * timestamp convention.
 */
export const reminderService = {
  async getReminders(
    params: { status?: ReminderStatus | null; startDate?: string; endDate?: string } = {}
  ): Promise<Reminder[]> {
    const res = await apiClient.get('/reminders', {
      params: {
        ...(params.status ? { status: params.status } : {}),
        ...(params.startDate ? { start_date: params.startDate } : {}),
        ...(params.endDate ? { end_date: params.endDate } : {}),
      },
    });
    return Array.isArray(res.data) ? res.data : [];
  },
  async createReminder(data: {
    title: string;
    message?: string | null;
    remind_at: string;
    task_id?: number | null;
    habit_id?: number | null;
    planner_event_id?: number | null;
  }): Promise<Reminder> {
    const res = await apiClient.post('/reminders', data);
    return res.data;
  },
  async updateReminder(id: number, data: Partial<Reminder>): Promise<Reminder> {
    const res = await apiClient.patch(`/reminders/${id}`, data);
    return res.data;
  },
  async deleteReminder(id: number) {
    await apiClient.delete(`/reminders/${id}`);
  }
};

export const preferencesService = {
  async get(): Promise<UserPreferences> {
    const res = await apiClient.get('/preferences');
    return res.data;
  },
  async update(data: Partial<Omit<UserPreferences, 'id' | 'user_id' | 'created_at' | 'updated_at'>>): Promise<UserPreferences> {
    const res = await apiClient.patch('/preferences', data);
    return res.data;
  }
};

const MAX_QUERY_LENGTH = 100;
const DEFAULT_SEARCH_LIMIT = 20;

/**
 * Global Search over the authenticated user's own records.
 *
 * The bearer token already carries the user id — there is no user_id
 * parameter, and the backend derives ownership from the token alone. Passing a
 * `signal` lets the caller abort an in-flight request when the query changes,
 * so a stale response can never overwrite fresher results.
 */
export const searchService = {
  async search(
    query: string,
    options: { limit?: number; signal?: AbortSignal } = {}
  ): Promise<SearchResponse> {
    const trimmed = query.trim();

    const res = await apiClient.get<SearchResponse>('/search', {
      params: {
        // Mirror the backend's length window so short input never becomes a
        // 422, and over-long input is rejected before it reaches the network.
        q: trimmed.slice(0, MAX_QUERY_LENGTH),
        limit: options.limit ?? DEFAULT_SEARCH_LIMIT,
      },
      signal: options.signal,
    });
    return res.data;
  }
};