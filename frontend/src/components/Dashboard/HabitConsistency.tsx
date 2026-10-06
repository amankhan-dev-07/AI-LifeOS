import React, { useMemo } from 'react'
import { Activity, Flame, Check, ArrowUpRight, AlertTriangle } from 'lucide-react'
import type { IntelligenceResponse, HabitSignal } from '../../types'

/**
 * Habit consistency.
 *
 * Every figure here is a field the backend already computed from
 * `HabitCompletion` rows: `current_streak`, `longest_streak`, `completions_14d`,
 * `completions_30d` and `last_completed_on`. Nothing is inferred client-side and
 * no psychological claim is made — a habit is described by counts and dates the
 * user can verify.
 *
 * The "slipping" marker is shown only when the rule engine raised a
 * `habit_consistency` insight for that habit, so the dashboard never applies
 * its own consistency threshold.
 */

const MAX_ROWS = 5

interface HabitConsistencyProps {
  data: IntelligenceResponse
  onNavigate: (route: string) => void
}

export const HabitConsistency: React.FC<HabitConsistencyProps> = ({ data, onNavigate }) => {
  const flaggedIds = useMemo(() => {
    const ids = new Set<number>()
    data.insights
      .filter((insight) => insight.type === 'habit_consistency' && insight.entity_id != null)
      .forEach((insight) => ids.add(insight.entity_id as number))
    return ids
  }, [data.insights])

  const habits = useMemo(
    () =>
      [...data.habits].sort((a, b) => {
        // Flagged first, then longest current streak, then most recent activity.
        const aFlag = flaggedIds.has(a.id) ? 0 : 1;
        const bFlag = flaggedIds.has(b.id) ? 0 : 1;
        if (aFlag !== bFlag) return aFlag - bFlag;
        if (b.current_streak !== a.current_streak) return b.current_streak - a.current_streak;
        return (b.last_completed_on ?? '').localeCompare(a.last_completed_on ?? '');
      }),
    [data.habits, flaggedIds]
  )

  const flaggedCount = habits.filter((h) => flaggedIds.has(h.id)).length
  const bestStreak = habits.reduce((max, h) => Math.max(max, h.current_streak), 0)

  return (
    <section aria-label="Habit consistency" className="card-secondary p-6 stagger-in">
      <Header
        count={habits.length}
        bestStreak={bestStreak}
        flaggedCount={flaggedCount}
        onNavigate={onNavigate}
      />

      {habits.length === 0 ? (
        <Empty
          title="No habits yet"
          body="A habit is the smallest repeatable unit in AI-LifeOS. Add one and this section tracks streaks and recent consistency from your actual check-ins."
          onNavigate={onNavigate}
        />
      ) : (
        <div className="row-stack mt-4">
          {habits.slice(0, MAX_ROWS).map((habit, i) => (
            <HabitRow
              key={habit.id}
              habit={habit}
              flagged={flaggedIds.has(habit.id)}
              index={i}
              onNavigate={onNavigate}
            />
          ))}
        </div>
      )}

      {habits.length > MAX_ROWS && (
        <button
          onClick={() => onNavigate('habits')}
          className="btn-secondary btn-sm w-full mt-3 focus-ring"
        >
          {habits.length - MAX_ROWS} more habits
        </button>
      )}
    </section>
  )
}

/**
 * The summary chips live inside the label line rather than in a row of tinted
 * pills beneath the title. Two coloured pills ("best streak", "needs
 * attention") directly under a section header competed with the per-habit
 * warning markers in the list below; inline, they read as caption.
 */
const Header: React.FC<{
  count: number
  bestStreak: number
  flaggedCount: number
  onNavigate: (route: string) => void
}> = ({ count, bestStreak, flaggedCount, onNavigate }) => (
  <div className="section-header">
    <div className="min-w-0">
      <p className="section-header-label flex-wrap">
        <Activity className="w-3.5 h-3.5 !text-[rgb(var(--accent))]" />
        Routines
        {count > 0 && (
          <>
            <span className="w-1 h-1 rounded-full bg-[rgb(var(--border-strong))]" aria-hidden="true" />
            <span className="!normal-case !tracking-[0.06em] !font-normal">
              best streak {bestStreak}d
            </span>
            {flaggedCount > 0 && (
              <>
                <span className="w-1 h-1 rounded-full bg-[rgb(var(--border-strong))]" aria-hidden="true" />
                <span className="!normal-case !tracking-[0.06em] !font-normal !text-[rgb(var(--warning))]">
                  {flaggedCount} slipping
                </span>
              </>
            )}
          </>
        )}
      </p>
      <h2 className="section-header-title mt-2">Habit consistency</h2>
    </div>
    {count > 0 && (
      <button
        onClick={() => onNavigate('habits')}
        className="shrink-0 inline-flex items-center gap-1 text-[13px] font-medium text-accent text-accent-hover transition-colors focus-ring rounded"
      >
        All habits
        <ArrowUpRight className="w-3.5 h-3.5" />
      </button>
    )}
  </div>
)

const HabitRow: React.FC<{
  habit: HabitSignal
  flagged: boolean
  index: number
  onNavigate: (route: string) => void
}> = ({ habit, flagged, index, onNavigate }) => {
  // "Done today" is read against the backend's own last-completion date rather
  // than a separate client-side clock, so it cannot disagree with the streak.
  const doneRecently = habit.last_completed_on !== null
  const live = habit.current_streak > 0

  return (
    <button
      onClick={() => onNavigate('habits')}
      className={`row-item w-full text-left !cursor-pointer stagger-in-fast focus-ring ${
        flagged ? '!border-l-2 !border-l-[rgb(var(--warning))] !pl-5' : ''
      }`}
      style={{ animationDelay: `${index * 45}ms` }}
    >
      <span
        className={`w-9 h-9 shrink-0 grid place-items-center rounded-lg border ${
          live
            ? 'bg-[rgb(var(--accent) / 0.12)] border-[rgb(var(--accent) / 0.3)] text-[rgb(var(--accent))]'
            : 'bg-[rgb(var(--surface-4))] border-[rgb(var(--border-subtle))] text-[rgb(var(--text-muted))]'
        }`}
        aria-hidden="true"
      >
        {live ? <Flame className="w-4 h-4" /> : <Activity className="w-4 h-4" />}
      </span>

      <div className="min-w-0 flex-1">
        <p className="typo-body-sm !font-medium !leading-tight !text-[rgb(var(--text-primary))] truncate">
          {habit.title}
        </p>
        <div className="mt-1.5 flex flex-wrap items-center gap-x-2.5 gap-y-1 text-[11px] font-mono text-[rgb(var(--text-tertiary))]">
          <span>{habit.frequency}</span>
          <span className="w-1 h-1 rounded-full bg-[rgb(var(--border-strong))]" aria-hidden="true" />
          <span>
            {habit.completions_14d}× / 14d · {habit.completions_30d}× / 30d
          </span>
          {flagged && (
            <span className="inline-flex items-center gap-1 text-[rgb(var(--warning))]">
              <AlertTriangle className="w-3 h-3" />
              slipping
            </span>
          )}
          {!doneRecently && <span className="text-[rgb(var(--text-muted))]">no completions yet</span>}
        </div>
      </div>

      {/* Streak as the row's numeric anchor: current on top, best beneath. */}
      <span className="shrink-0 text-right">
        <span
          className={`typo-numeric block text-xl font-bold leading-none ${
            live ? 'text-[rgb(var(--accent))]' : 'text-[rgb(var(--text-muted))]'
          }`}
        >
          {habit.current_streak}
        </span>
        <span className="block mt-1 text-[10px] font-mono text-[rgb(var(--text-muted))]">
          best {habit.longest_streak}
        </span>
      </span>

      {live && (
        <Check className="w-4 h-4 shrink-0 text-[rgb(var(--success))]" aria-label="has a live streak" />
      )}
    </button>
  )
}

const Empty: React.FC<{
  title: string;
  body: string;
  onNavigate: (route: string) => void
}> = ({ title, body, onNavigate }) => (
  <div className="text-center py-8">
    <p className="typo-body !font-medium">{title}</p>
    <p className="typo-meta mt-1.5 max-w-[42ch] mx-auto mb-5">{body}</p>
    <button onClick={() => onNavigate('habits')} className="btn-secondary btn-sm focus-ring">
      Create a habit <ArrowUpRight className="w-3.5 h-3.5" />
    </button>
  </div>
)