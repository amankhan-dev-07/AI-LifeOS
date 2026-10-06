export interface User {
  id: number;
  email: string;
  name: string;
  is_active: boolean;
  avatar_url?: string;
  created_at?: string;
}

export interface Task {
  id: number;
  title: string;
  description?: string | null;
  status: 'todo' | 'in_progress' | 'completed' | 'archived';
  priority: 'low' | 'medium' | 'high' | 'urgent';
  due_date?: string | null;
  goal_id?: number | null;
  estimated_minutes: number;
  user_id: number;
  created_at: string;
  updated_at?: string;
}

export interface Goal {
  id: number;
  title: string;
  description?: string | null;
  category?: string;
  target_date?: string | null;
  progress: number; // 0 - 100
  is_completed: boolean;
  user_id: number;
  created_at?: string;
  updated_at?: string;
}

export interface Habit {
  id: number;
  title: string;
  description?: string | null;
  frequency: string;
  goal_id?: number | null;
  current_streak: number;
  longest_streak: number;
  last_completed_at: string | null;
  is_active: boolean;
  user_id: number;
  created_at: string;
  updated_at?: string;
}

export type Note = {
  id: number;
  title: string;
  content: string;
  tag: string;
  is_pinned: boolean;
  is_archived: boolean;
  goal_id: number | null;
  task_id: number | null;
  user_id: number;
  created_at: string;
  updated_at: string;
};

export type TransactionType = 'income' | 'expense';

export interface Transaction {
  id: number;
  title: string;
  /** Numeric(12,2) on the backend; serialized as a decimal string in JSON. */
  amount: number;
  type: TransactionType;
  category: string;
  transaction_date: string;
  notes: string | null;
  user_id: number;
  created_at: string;
  updated_at: string;
}

export type PlannerEventType = 'task' | 'habit' | 'focus_block' | 'custom';

export interface PlannerEvent {
  id: number;
  title: string;
  description: string | null;
  event_date: string;
  start_time: string;
  end_time: string;
  event_type: PlannerEventType;
  task_id: number | null;
  habit_id: number | null;
  is_completed: boolean;
  user_id: number;
  created_at: string;
  updated_at: string;
}

export type NotificationType = 'info' | 'success' | 'warning' | 'error';

export interface AppNotification {
  id: number;
  title: string;
  message: string;
  type: NotificationType;
  link: string | null;
  is_read: boolean;
  read_at: string | null;
  created_at: string;
  user_id: number;
}

export interface UserPreferences {
  id: number;
  user_id: number;
  theme: string;
  daily_briefing_enabled: boolean;
  security_alerts_enabled: boolean;
  planner_start_hour: number;
  /** IANA timezone name, e.g. "Asia/Kolkata". */
  timezone: string;
  /** Display format for times; storage stays UTC either way. */
  time_format: '12h' | '24h';
  /** Whether the user has completed the first-time onboarding flow. */
  onboarding_completed: boolean;
  /** Onboarding version — allows future migrations to re-prompt if flow changes. */
  onboarding_version: number;
  created_at: string;
  updated_at: string;
}

export type ReminderStatus = 'pending' | 'completed' | 'cancelled';

export interface Reminder {
  id: number;
  user_id: number;
  title: string;
  message: string | null;
  /** Naive UTC datetime, matching the backend's timestamp convention. */
  remind_at: string;
  status: ReminderStatus;
  is_completed: boolean;
  is_cancelled: boolean;
  /** Set once the scheduler has delivered this reminder's notification. */
  notified_at: string | null;
  task_id: number | null;
  habit_id: number | null;
  planner_event_id: number | null;
  created_at: string;
  updated_at: string;
}

export interface TaskSummary {
  total: number;
  pending: number;
  completed: number;
}

export interface GoalSummary {
  total: number;
  active: number;
  completed: number;
}

export interface HabitSummary {
  total: number;
  active: number;
  current_streak: number;
  best_streak: number;
}

export interface DashboardResponse {
  tasks: TaskSummary;
  goals: GoalSummary;
  habits: HabitSummary;
}

export type SearchEntityType =
  | 'task'
  | 'goal'
  | 'habit'
  | 'note'
  | 'planner_event'
  | 'transaction';

/** One Global Search hit, scoped to the authenticated user by the backend. */
export interface SearchResult {
  id: number;
  entity_type: SearchEntityType;
  title: string;
  snippet: string | null;
  context: string | null;
  /** App view key the result belongs to, e.g. 'tasks' or 'finance'. */
  route: string;
  status: string | null;
  priority: string | null;
  category: string | null;
  frequency: string | null;
  tag: string | null;
  date: string | null;
}

export interface SearchResponse {
  query: string;
  count: number;
  results: SearchResult[];
}

/**
 * LifeOS Intelligence.
 *
 * Every field here is derived server-side from the authenticated user's own
 * persisted records on each request — nothing is stored, and nothing is
 * generated. `insights` is the master list; the UI filters it by `type` and
 * `priority` to build its own sections rather than the API shipping a second
 * copy of every row.
 */

export type InsightType =
  | 'overdue'
  | 'upcoming'
  | 'goal_risk'
  | 'habit_consistency'
  | 'planning'
  | 'task_load'
  | 'finance'
  | 'reminder'
  | 'data_quality';

export type InsightPriority = 'low' | 'medium' | 'high';

export type AttentionLevel = 'clear' | 'watch' | 'busy';

export interface Insight {
  /** Stable slug, e.g. "overdue_tasks" or "goal_risk:12". */
  id: string;
  type: InsightType;
  priority: InsightPriority;
  domain: string;
  title: string;
  /** Factual, quantitative explanation the user can verify. */
  detail: string;
  /** Short leading figure, or null when the rule has no single number. */
  metric: string | null;
  action_label: string | null;
  /** App view key, or null when there is nowhere to navigate. */
  route: string | null;
  entity_type: string | null;
  entity_id: number | null;
}

export interface AttentionSummary {
  level: AttentionLevel;
  headline: string;
  detail: string;
  overdue_count: number;
  due_soon_count: number;
  incomplete_task_count: number;
  unread_notification_count: number;
}

export interface TaskContext {
  total: number;
  incomplete: number;
  completed: number;
  overdue: number;
  due_soon: number;
  unlinked: number;
}

export interface GoalSignal {
  id: number;
  title: string;
  progress: number;
  is_completed: boolean;
  target_date: string | null;
  days_to_target: number | null;
  incomplete_task_count: number;
  active_habit_count: number;
}

export interface HabitSignal {
  id: number;
  title: string;
  frequency: string;
  is_active: boolean;
  current_streak: number;
  longest_streak: number;
  completions_14d: number;
  completions_30d: number;
  last_completed_on: string | null;
}

export type UpcomingKind = 'overdue' | 'due_soon' | 'planner_event' | 'reminder';

export interface UpcomingItem {
  id: string;
  domain: string;
  kind: UpcomingKind;
  title: string;
  due_at: string;
  route: string | null;
  entity_type: string | null;
  entity_id: number | null;
}

export interface FinanceCategory {
  category: string;
  /** Numeric(12,2) on the backend; serialized as a decimal string. */
  total: string;
}

export interface FinanceSignal {
  period_start: string;
  period_end: string;
  income_total: string;
  expense_total: string;
  transaction_count: number;
  top_expense_categories: FinanceCategory[];
}

export interface IntelligenceResponse {
  generated_at: string;
  summary: AttentionSummary;
  tasks: TaskContext;
  goals: GoalSignal[];
  habits: HabitSignal[];
  upcoming: UpcomingItem[];
  finance: FinanceSignal | null;
  insights: Insight[];
  /** False only when the account has no records in any inspected domain. */
  has_data: boolean;
  populated_domains: string[];
}

/* ============================================================
   AI Command Center — Action Plan types
   ============================================================ */

export type ActionOperation =
  | 'read'
  | 'create'
  | 'update'
  | 'complete'
  | 'delete'
  | 'search'
  | 'plan';

export type ActionEntity =
  | 'task'
  | 'goal'
  | 'habit'
  | 'note'
  | 'reminder'
  | 'planner_event'
  | 'transaction'
  | 'intelligence';

export type ActionStepStatus = 'pending' | 'succeeded' | 'failed' | 'skipped';

export interface ActionStep {
  order: number;
  operation: ActionOperation;
  entity: ActionEntity;
  description: string;
  target_id: number | null;
  target_label: string | null;
  confirmation_required: boolean;
  confirmation_reason: string | null;
  parameters: Record<string, any>;
  status: ActionStepStatus;
  result_message: string | null;
}

export interface ActionPlanSummary {
  plan_id: string;
  requires_confirmation: boolean;
  steps: ActionStep[];
}

export interface AIChatResponse {
  response: string;
  ai_online: boolean;
  intent: string | null;
  plan: ActionPlanSummary | null;
  context_used: string[];
  conversation_id: string | null;
  awaiting_user: boolean;
  clarification_question: string | null;
}

export interface ActionConfirmRequest {
  plan_id: string;
  conversation_id: string | null;
}

export interface ActionCancelRequest {
  plan_id: string;
  conversation_id: string | null;
}