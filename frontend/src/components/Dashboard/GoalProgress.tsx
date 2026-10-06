import React, { useMemo } from 'react'
import { Target, ArrowUpRight, AlertTriangle } from 'lucide-react'
import type { IntelligenceResponse, GoalSignal } from '../../types'

/**
 * Goal progress.
 *
 * Reads the backend's `GoalSignal` list, which already carries progress,
 * target date, days remaining, and the count of linked open work. The risk
 * flag below is shown only when the backend itself raised a `goal_risk` insight
 * for that goal id — the dashboard does not invent its own definition of "at
 * risk".
 */

const MAX_ACTIVE = 4

interface GoalProgressProps {
  data: IntelligenceResponse
  onNavigate: (route: string) => void
}

export const GoalProgress: React.FC<GoalProgressProps> = ({ data, onNavigate }) => {
  // A goal is "at risk" here only if the rule engine emitted an insight whose
  // id is keyed to this goal. Anything else is left unlabelled.
  const riskIds = useMemo(() => {
    const ids = new Set<number>()
    data.insights
      .filter((insight) => insight.type === 'goal_risk' && insight.entity_id != null)
      .forEach((insight) => ids.add(insight.entity_id as number))
    return ids
  }, [data.insights])

  const active = useMemo(
    () => data.goals.filter((goal) => !goal.is_completed).sort(byUrgency),
    [data.goals]
  )

  const completed = data.goals.filter((goal) => goal.is_completed)

  if (data.goals.length === 0) {
    return (
      <section aria-label="Goal progress" className="card-secondary p-6 stagger-in">
        <Header activeCount={0} onNavigate={onNavigate} />
        <Empty
          title="No goals yet"
          body="A goal gives your tasks and habits a destination. Define one and this section tracks how far along you are."
          actionLabel="Create a goal"
          onNavigate={onNavigate}
        />
      </section>
    )
  }

  return (
    <section aria-label="Goal progress" className="card-secondary p-6 stagger-in">
      <Header activeCount={active.length} onNavigate={onNavigate} />

      {active.length === 0 ? (
        <div className="text-center py-8">
          <p className="typo-body !font-medium">
            All {completed.length} goal{completed.length !== 1 ? 's' : ''} complete
          </p>
          <p className="typo-meta mt-1.5 max-w-[40ch] mx-auto">
            Define the next one when you are ready.
          </p>
        </div>
      ) : (
        /* A progress ledger: title on the left, percentage as a large tabular
           figure on the right, bar spanning the gap beneath. Rows share one
           container and are divided by hairlines rather than each rendering as
           its own card. */
        <div className="row-stack mt-4">
          {active.slice(0, MAX_ACTIVE).map((goal, i) => (
            <GoalRow
              key={goal.id}
              goal={goal}
              atRisk={riskIds.has(goal.id)}
              index={i}
              onNavigate={onNavigate}
            />
          ))}
        </div>
      )}

      {completed.length > 0 && (
        <div className="mt-4 pt-4 border-t border-[rgb(var(--border-subtle))] flex items-center justify-between gap-3">
          <span className="typo-micro !tracking-[0.12em] !text-[rgb(var(--success))]">
            {completed.length} completed
          </span>
          <button
            onClick={() => onNavigate('goals')}
            className="inline-flex items-center gap-1 text-[13px] font-medium text-accent text-accent-hover transition-colors focus-ring rounded"
          >
            View all goals
            <ArrowUpRight className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {active.length > MAX_ACTIVE && (
        <button
          onClick={() => onNavigate('goals')}
          className="btn-secondary btn-sm w-full mt-3 focus-ring"
        >
          {active.length - MAX_ACTIVE} more active goals
        </button>
      )}
    </section>
  )
}

/**
 * Most urgent first: goals the rule engine flagged as at risk, then those with
 * the nearest target date, then goals with open linked work. Deterministic and
 * derived entirely from fields the backend already returns.
 */
function byUrgency(a: GoalSignal, b: GoalSignal): number {
  if (a.days_to_target !== null && b.days_to_target !== null) {
    const delta = a.days_to_target - b.days_to_target;
    if (delta !== 0) return delta;
  } else if (a.days_to_target !== null) {
    return -1;
  } else if (b.days_to_target !== null) {
    return 1;
  }

  if (a.incomplete_task_count !== b.incomplete_task_count) {
    return b.incomplete_task_count - a.incomplete_task_count;
  }

  return b.progress - a.progress;
}

const Header: React.FC<{ activeCount: number; onNavigate: (route: string) => void }> = ({
  activeCount,
  onNavigate,
}) => (
  <div className="section-header">
    <div className="min-w-0">
      <p className="section-header-label">
        <Target className="w-3.5 h-3.5 !text-[rgb(var(--accent))]" />
        Objectives
      </p>
      <h2 className="section-header-title mt-2">
        Goal progress
        {activeCount > 0 && (
          <span className="typo-micro ml-2.5 align-middle">/ {activeCount} active</span>
        )}
      </h2>
    </div>
    <button
      onClick={() => onNavigate('goals')}
      className="shrink-0 inline-flex items-center gap-1 text-[13px] font-medium text-accent text-accent-hover transition-colors focus-ring rounded"
    >
      Manage
      <ArrowUpRight className="w-3.5 h-3.5" />
    </button>
  </div>
)

const GoalRow: React.FC<{
  goal: GoalSignal
  atRisk: boolean
  index: number
  onNavigate: (route: string) => void
}> = ({ goal, atRisk, index, onNavigate }) => (
  <button
    onClick={() => onNavigate('goals')}
    className={`row-item w-full text-left !items-start !p-4 !cursor-pointer stagger-in-fast focus-ring ${
      atRisk ? '!border-l-2 !border-l-[rgb(var(--danger))] !pl-5' : ''
    }`}
    style={{ animationDelay: `${index * 50}ms` }}
  >
    <div className="min-w-0 flex-1">
      <div className="flex items-baseline justify-between gap-4">
        <p className="typo-body !font-semibold !leading-tight !text-[rgb(var(--text-primary))] truncate">
          {goal.title}
        </p>
        <span
          className={`typo-numeric shrink-0 text-lg font-bold leading-none ${
            goal.progress >= 100 ? 'text-[rgb(var(--success))]' : 'text-[rgb(var(--text-primary))]'
          }`}
        >
          {goal.progress}
          <span className="text-[11px] font-medium text-[rgb(var(--text-muted))]">%</span>
        </span>
      </div>

      {/* Progress bar: width transitions via CSS, so there is no per-frame
          setState and no JavaScript-driven animation loop. Jade-only fill — the
          previous jade→amber gradient spent the "rare" secondary accent on
          ordinary progress, so every goal read as if it were partly champagne. */}
      <div className="h-1.5 rounded-full bg-[rgb(var(--surface-4))] overflow-hidden mt-2.5">
        <div
          className="h-full rounded-full bg-[rgb(var(--accent))] transition-all duration-700 ease-out"
          style={{ width: `${Math.min(100, Math.max(0, goal.progress))}%` }}
        />
      </div>

      <div className="mt-2.5 flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] font-mono text-[rgb(var(--text-tertiary))]">
        {goal.days_to_target !== null && (
          <span
            className={
              goal.days_to_target < 0
                ? 'text-[rgb(var(--danger))]'
                : goal.days_to_target <= 7
                  ? 'text-[rgb(var(--warning))]'
                  : ''
            }
          >
            {goal.days_to_target < 0
              ? `${Math.abs(goal.days_to_target)}d past target`
              : goal.days_to_target === 0
                ? 'due today'
                : `${goal.days_to_target}d left`}
          </span>
        )}
        {goal.incomplete_task_count > 0 && (
          <span>
            {goal.incomplete_task_count} open task{goal.incomplete_task_count !== 1 ? 's' : ''}
          </span>
        )}
        {goal.active_habit_count > 0 && (
          <span>
            {goal.active_habit_count} habit{goal.active_habit_count !== 1 ? 's' : ''}
          </span>
        )}
        {atRisk && (
          <span className="inline-flex items-center gap-1 text-[rgb(var(--danger))]">
            <AlertTriangle className="w-3 h-3" />
            at risk
          </span>
        )}
      </div>
    </div>
  </button>
)

const Empty: React.FC<{
  title: string;
  body: string;
  actionLabel: string;
  onNavigate: (route: string) => void
}> = ({ title, body, actionLabel, onNavigate }) => (
  <div className="text-center py-8">
    <p className="typo-body !font-medium">{title}</p>
    <p className="typo-meta mt-1.5 max-w-[42ch] mx-auto mb-5">{body}</p>
    <button onClick={() => onNavigate('goals')} className="btn-secondary btn-sm focus-ring">
      {actionLabel} <ArrowUpRight className="w-3.5 h-3.5" />
    </button>
  </div>
)