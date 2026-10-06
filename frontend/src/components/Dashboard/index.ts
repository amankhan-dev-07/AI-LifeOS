/**
 * LifeOS Command Center — dashboard sections.
 *
 * Every section here is a pure read of one `IntelligenceResponse` payload from
 * `GET /intelligence`, plus the authenticated user's name. No section fetches on
 * its own, so mounting the dashboard issues a single intelligence request.
 */
export { RightNowSummary, RightNowSkeleton } from './RightNowSummary';
export { AttentionCenter } from './AttentionCenter';
export { TodayActions } from './TodayActions';
export { GoalProgress } from './GoalProgress';
export { HabitConsistency } from './HabitConsistency';
export { PlannerToday } from './PlannerToday';
export { FinanceSnapshot } from './FinanceSnapshot';
export { QuickActions } from './QuickActions';
export { EmptyOnboarding } from './EmptyOnboarding';
