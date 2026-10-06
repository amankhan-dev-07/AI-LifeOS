import React, { useCallback, useEffect, useState } from 'react'
import { Activity, Plus, Check, Flame, Trash2, Loader2, Target, AlertCircle, X, Calendar } from 'lucide-react'
import { goalService, habitService } from '../services/services'
import { extractErrorMessage } from '../utils/apiError'
import type { Goal, Habit } from '../types'

function isToday(dateStr: string | null) {
  if (!dateStr) return false
  const d = new Date(dateStr)
  const now = new Date()
  return d.getFullYear() === now.getFullYear() && d.getMonth() === now.getMonth() && d.getDate() === now.getDate()
}

/**
 * Streak display.
 *
 * The count-up was a `requestAnimationFrame` loop calling `setState` on every
 * frame for every habit on screen. The number is now rendered directly and the
 * entrance is a short CSS opacity/scale reveal, so the streak appears without
 * ~36 renders per card.
 *
 * The two `shadow-[...]` glows and the white overlay gradient are gone as well:
 * depth comes from the surface token, not from a coloured bloom that has to be
 * repainted whenever the theme changes.
 *
 * The 48px tinted tile that used to wrap the flame is gone too. It re-encoded
 * the one fact this card already states in words — "completed today" — as a
 * second coloured box, and put a filled square in front of every habit title.
 * The streak is now a figure with a unit beneath it.
 */
const StreakDisplay: React.FC<{ streak: number; doneToday: boolean; index: number }> = ({
  streak,
  doneToday,
  index,
}) => (
  <div
    className="relative flex flex-col items-center justify-center w-14 shrink-0 animate-fadeIn"
    style={{ animationDelay: `${index * 60}ms` }}
  >
    <span
      className={`typo-numeric text-[22px] font-bold leading-none transition-colors duration-300 ${
        doneToday ? 'text-[rgb(var(--success))]' : 'text-[rgb(var(--text-primary))]'
      }`}
    >
      {streak}
    </span>
    <span className="typo-micro mt-1 !text-[9px] !tracking-[0.1em]">
      {streak === 1 ? 'day' : 'days'}
    </span>
  </div>
)

// === METADATA LINE ===
//
// Frequency and today's state were two more filled pills per habit: cyan for
// "daily", amber for "weekly", green for "Completed", grey for "Pending" — six
// habits meant up to six coloured chips before any title was read. Frequency is
// an adjective and today's state is a binary, so both are plain text on one
// line, with a single dot for the state.
const HabitMeta: React.FC<{ frequency: string; doneToday: boolean }> = ({ frequency, doneToday }) => (
  <p className="typo-micro mt-1.5">
    <span className="!normal-case !tracking-[0.06em] !font-normal">
      {frequency === 'daily' ? 'Every day' : 'Every week'}
    </span>
    <span className="w-1 h-1 rounded-full bg-[rgb(var(--border-strong))] inline-block align-middle mx-1.5" aria-hidden="true" />
    <span
      className={`inline-flex items-center gap-1.5 !normal-case !tracking-[0.06em] !font-normal ${
        doneToday ? 'text-[rgb(var(--success))]' : ''
      }`}
    >
      {!doneToday && (
        <span className="w-1 h-1 rounded-full bg-[rgb(var(--text-muted))] inline-block" aria-hidden="true" />
      )}
      {doneToday ? 'Checked in today' : 'Not yet today'}
    </span>
  </p>
)

// === HABIT CARD ===
interface HabitCardProps {
  habit: Habit
  goals: Goal[]
  onCheckIn: (id: number) => void
  onDelete: (id: number) => void
  onSetGoal: (habit: Habit, goalId: number | null) => void
  index: number
  busyId: number | null
}

const HabitCard: React.FC<HabitCardProps> = ({ habit, goals, onCheckIn, onDelete, onSetGoal, index, busyId }) => {
  const isBusy = busyId === habit.id
  const doneToday = isToday(habit.last_completed_at)
  const streak = habit.current_streak ?? 0
  // goal_id is a foreign key we do not always receive hydrated; fall back to the
  // id present in the local goals list rather than to a guessed default.
  const linkedGoal = goals.find(g => g.id === habit.goal_id) ?? null

  return (
    <div
      className={`row-item !p-4 md:!p-4 !gap-4 flex-col md:flex-row !items-stretch md:!items-center stagger-in-fast ${
        doneToday ? '!border-l-2 !border-l-[rgb(var(--success))] !pl-[15px]' : ''
      }`}
      style={{ animationDelay: `${index * 50}ms` }}
    >
      <div className="flex items-center gap-4 min-w-0">
        <StreakDisplay streak={streak} doneToday={doneToday} index={index} />

        <div className="min-w-0 flex-1">
          <h3 className="typo-body !text-[14px] !font-semibold !leading-tight !text-[rgb(var(--text-primary))] truncate">
            {habit.title}
          </h3>
          <HabitMeta frequency={habit.frequency} doneToday={doneToday} />

          {/* Goal relationship: explicit null clears it. */}
          <div className="mt-2.5">
            {linkedGoal ? (
              <span className="inline-flex items-center gap-1">
                <select
                  value={habit.goal_id as number}
                  disabled={isBusy}
                  onChange={e => onSetGoal(habit, Number(e.target.value))}
                  aria-label={`Goal for ${habit.title}, currently ${linkedGoal.title}`}
                  className="input input-sm !w-auto !h-8 !pl-2.5 !pr-9 !text-[12px] cursor-pointer max-w-[16rem]"
                >
                  {goals.map(g => <option key={g.id} value={g.id}>{g.title}</option>)}
                </select>
                <button
                  onClick={() => onSetGoal(habit, null)}
                  disabled={isBusy}
                  aria-label={`Remove ${linkedGoal.title} link`}
                  title="Remove from goal"
                  className="btn-icon !w-7 !h-7 focus-ring hover:!text-[rgb(var(--danger))] disabled:opacity-50"
                >
                  <X className="w-3 h-3" />
                </button>
              </span>
            ) : (
              <select
                value=""
                disabled={isBusy || goals.length === 0}
                onChange={e => e.target.value && onSetGoal(habit, Number(e.target.value))}
                aria-label={`Assign ${habit.title} to a goal`}
                className="input input-sm !w-auto !h-8 !pl-2.5 !pr-9 !text-[12px] !text-[rgb(var(--text-tertiary))] !border-dashed cursor-pointer max-w-[16rem] disabled:opacity-50"
                title={goals.length === 0 ? 'Create a goal first' : 'Assign to a goal'}
              >
                <option value="">{goals.length === 0 ? 'No goals yet' : '+ Link goal'}</option>
                {goals.map(g => <option key={g.id} value={g.id}>{g.title}</option>)}
              </select>
            )}
          </div>
        </div>
      </div>

      <div className="flex items-center gap-2 shrink-0 md:justify-end">
        <button
          onClick={() => onCheckIn(habit.id)}
          disabled={isBusy || doneToday}
          aria-pressed={doneToday}
          className={`btn-sm focus-ring ${doneToday ? 'btn-ghost !text-[rgb(var(--success))] cursor-default' : 'btn-primary'} ${
            isBusy && !doneToday ? 'disabled:opacity-50' : ''
          }`}
          title={doneToday ? 'Already checked in for today' : 'Check in for today'}
        >
          {doneToday
            ? <><Check className="w-4 h-4" aria-hidden="true" /> Done</>
            : isBusy
              ? <><Loader2 className="w-4 h-4 animate-spin" aria-hidden="true" /> Saving…</>
              : <><Check className="w-4 h-4" aria-hidden="true" /> Check in</>}
        </button>

        <button
          onClick={() => onDelete(habit.id)}
          disabled={isBusy}
          aria-label={`Delete ${habit.title}`}
          title="Delete habit"
          className="btn-icon focus-ring hover:!text-[rgb(var(--danger))] hover:!bg-[rgb(var(--danger)/0.1)] disabled:opacity-50"
        >
          <Trash2 className="w-4 h-4" />
        </button>
      </div>
    </div>
  )
}

// === CREATE FORM ===
interface CreateFormProps {
  title: string
  setTitle: (v: string) => void
  frequency: string
  setFrequency: (v: string) => void
  goalId: number | null
  setGoalId: (v: number | null) => void
  goals: Goal[]
  submitting: boolean
  error: string | null
  onSubmit: (e: React.FormEvent) => void
}

const CreateForm: React.FC<CreateFormProps> = ({ title, setTitle, frequency, setFrequency, goalId, setGoalId, goals, submitting, error, onSubmit }) => (
  <form onSubmit={onSubmit} className="card-input p-5 space-y-4 stagger-in" style={{ animationDelay: '80ms' }}>
    <p className="typo-label">New habit</p>
    <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
      <div className="relative">
        <input
          value={title}
          onChange={e => setTitle(e.target.value)}
          placeholder="Habit title (e.g. Deep Work)…"
          aria-label="Habit title"
          required
          className="input input-icon-left"
        />
        <Activity className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[rgb(var(--text-tertiary))] pointer-events-none" aria-hidden="true" />
      </div>
      <div className="relative">
        <select
          value={frequency}
          onChange={e => setFrequency(e.target.value)}
          aria-label="Frequency"
          className="input input-icon-left"
        >
          <option value="daily">Daily</option>
          <option value="weekly">Weekly</option>
        </select>
        <Calendar className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[rgb(var(--text-tertiary))] pointer-events-none" aria-hidden="true" />
      </div>
      <div className="relative">
        <select
          value={goalId ?? ''}
          onChange={e => setGoalId(e.target.value ? Number(e.target.value) : null)}
          aria-label="Linked goal"
          className="input input-icon-left"
        >
          <option value="">No linked goal</option>
          {goals.map(g => <option key={g.id} value={g.id}>{g.title}</option>)}
        </select>
        <Target className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[rgb(var(--text-tertiary))] pointer-events-none" aria-hidden="true" />
      </div>
    </div>

    {error && (
      <p role="alert" className="text-[13px] text-[rgb(var(--danger))] flex items-center gap-1.5">
        <AlertCircle className="w-3.5 h-3.5 shrink-0" aria-hidden="true" /> {error}
      </p>
    )}

    <div className="flex justify-end">
      <button type="submit" disabled={submitting || !title.trim()} className="btn-primary focus-ring disabled:opacity-50">
        {submitting ? <Loader2 className="w-4 h-4 animate-spin" aria-hidden="true" /> : <Plus className="w-4 h-4" aria-hidden="true" />}
        Create habit
      </button>
    </div>
  </form>
)

// === NOTICE BANNER ===
const NoticeBanner: React.FC<{ notice: string | null }> = ({ notice }) => {
  if (!notice) return null
  const isSuccess = notice.startsWith('Checked in') || notice.includes('streak preserved')
  const isWarning = notice.includes('Already checked in')

  return (
    <div
      role="status"
      aria-live="polite"
      className={`card-secondary px-4 py-3 rounded-xl border animate-fadeInUp ${
        isSuccess
          ? 'bg-[rgb(var(--success) / 0.1)] border-[rgb(var(--success) / 0.3)] text-[rgb(var(--success))]'
          : isWarning
            ? 'bg-[rgb(var(--warning) / 0.1)] border-[rgb(var(--warning) / 0.3)] text-[rgb(var(--warning))]'
            : 'bg-[rgb(var(--danger) / 0.1)] border-[rgb(var(--danger) / 0.3)] text-[rgb(var(--danger))]'
      }`}
    >
      <p className="typo-body-sm">{notice}</p>
    </div>
  )
}

// === EMPTY STATE ===
const EmptyState: React.FC<{ error: string | null; onRetry: () => void }> = ({ error, onRetry }) => (
  <div className="card-secondary p-8 flex flex-col items-center justify-center text-center stagger-in">
    <span
      className={`grid place-items-center w-12 h-12 rounded-xl mb-4 ${
        error
          ? 'bg-[rgb(var(--danger)/0.1)] border border-[rgb(var(--danger)/0.25)] text-[rgb(var(--danger))]'
          : 'bg-[rgb(var(--surface-4))] border border-[rgb(var(--border-subtle))] text-[rgb(var(--text-tertiary))]'
      }`}
      aria-hidden="true"
    >
      {error ? <AlertCircle className="w-5 h-5" /> : <Flame className="w-5 h-5" />}
    </span>
    <h3 className="typo-card-title">{error ? 'Could not load your habits' : 'No habits yet'}</h3>
    <p className="typo-body-sm mt-1.5 max-w-sm">
      {error
        ? error
        : 'Create a habit above and check in each day. Your current and longest streak are counted from your check-ins.'}
    </p>
    {error && (
      <button onClick={onRetry} className="btn-primary btn-sm mt-5 focus-ring">
        <Loader2 className="w-4 h-4" aria-hidden="true" /> Try again
      </button>
    )}
  </div>
)

// === LOADING SKELETON ===
const HabitSkeleton: React.FC = () => (
  <div className="row-stack stagger-in-fast" aria-busy="true" aria-label="Loading habits">
    {[1, 2, 3].map(i => (
      <div key={i} className="row-item !p-4">
        <div className="w-14 h-14 skeleton rounded-xl shrink-0" />
        <div className="flex-1 min-w-0 space-y-2">
          <div className="w-40 h-4 skeleton rounded" />
          <div className="w-28 h-3 skeleton rounded" />
        </div>
        <div className="w-20 h-8 skeleton rounded-lg shrink-0" />
        <div className="w-8 h-8 skeleton rounded-lg shrink-0" />
      </div>
    ))}
  </div>
)

// === MAIN COMPONENT ===
export const HabitsView: React.FC = () => {
  const [habits, setHabits] = useState<Habit[]>([])
  const [goals, setGoals] = useState<Goal[]>([])
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [title, setTitle] = useState('')
  const [frequency, setFrequency] = useState('daily')
  const [goalId, setGoalId] = useState<number | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [busyId, setBusyId] = useState<number | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setLoadError(null)
    try {
      const [habitRes, goalRes] = await Promise.all([
        habitService.getHabits(),
        goalService.getGoals().catch(() => []),
      ])
      setHabits(Array.isArray(habitRes) ? habitRes : [])
      setGoals(Array.isArray(goalRes) ? goalRes : [])
    } catch (e) {
      setHabits([])
      setLoadError(extractErrorMessage(e, 'Failed to load habits.'))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const create = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!title.trim()) return

    setSubmitting(true)
    setFormError(null)
    try {
      await habitService.createHabit({ title: title.trim(), frequency, goal_id: goalId })
      setTitle('')
      setGoalId(null)
      setNotice(null)
      await load()
    } catch (e) {
      setFormError(extractErrorMessage(e, 'Could not create the habit.'))
    } finally {
      setSubmitting(false)
    }
  }

  const complete = async (id: number) => {
    setBusyId(id)
    setNotice(null)

    setHabits(prev => prev.map(h => h.id === id ? { ...h, last_completed_at: new Date().toISOString() } : h))

    try {
      const res = await habitService.completeHabit(id)
      setNotice(res?.completed_date ? `Checked in for ${res.completed_date}.` : 'Checked in for today.')
      await load()
    } catch (e: any) {
      const status = e?.response?.status
      const msg = extractErrorMessage(e, 'Check-in failed.')
      if (status === 409 && /already completed/i.test(msg)) {
        setNotice('Already checked in for today — streak preserved.')
      } else {
        setNotice(msg)
      }
      await load()
    } finally {
      setBusyId(null)
      setTimeout(() => setNotice(n => n && n.startsWith('Checked in') ? null : n), 4000)
    }
  }

  const setGoal = async (habit: Habit, nextGoalId: number | null) => {
    setBusyId(habit.id)
    // Optimistic update, reverted if the server rejects it.
    setHabits(prev => prev.map(h => h.id === habit.id ? { ...h, goal_id: nextGoalId } : h))
    try {
      await habitService.updateHabit(habit.id, { goal_id: nextGoalId })
      await load()
    } catch (e) {
      setHabits(prev => prev.map(h => h.id === habit.id ? { ...h, goal_id: habit.goal_id } : h))
      setNotice(extractErrorMessage(e, 'Could not update the goal link.'))
    } finally {
      setBusyId(null)
    }
  }

  const del = async (id: number) => {
    if (!window.confirm('Delete this habit?')) return
    setBusyId(id)
    try {
      await habitService.deleteHabit(id)
      await load()
    } catch (e) {
      setNotice(extractErrorMessage(e, 'Could not delete the habit.'))
    } finally {
      setBusyId(null)
    }
  }

  return (
    <div className="relative space-y-6 animate-fadeInUp">
      {/* === HEADER ===
          No 40px icon tile: the heading is text, and a tiny label carries the
          orientation the tile used to give, at zero chromatic cost. */}
      <div className="stagger-in">
        <p className="section-header-label !m-0 !p-0">
          <Activity className="w-3.5 h-3.5 !text-[rgb(var(--accent))]" aria-hidden="true" />
          Routines
        </p>
        <h1 className="typo-h1 mt-2">Habits</h1>
        <p className="typo-meta mt-1.5">
          Your routines, checked in daily. Streaks are counted from your own check-ins.
        </p>
      </div>

      {/* === NOTICE BANNER === */}
      <NoticeBanner notice={notice} />

      {/* === CREATE FORM === */}
      <CreateForm
        title={title}
        setTitle={setTitle}
        frequency={frequency}
        setFrequency={setFrequency}
        goalId={goalId}
        setGoalId={setGoalId}
        goals={goals}
        submitting={submitting}
        error={formError}
        onSubmit={create}
      />

      {/* === HABITS LIST === */}
      <div className="stagger-in" style={{ animationDelay: '160ms' }}>
        {loading ? (
          <HabitSkeleton />
        ) : habits.length === 0 ? (
          <EmptyState error={loadError} onRetry={load} />
        ) : (
          <div className="row-stack">
            {loadError && (
              <div role="alert" className="typo-body-sm text-[rgb(var(--danger))] flex items-center gap-2 px-1">
                <AlertCircle className="w-4 h-4 shrink-0" aria-hidden="true" /> {loadError}
              </div>
            )}
            {habits.map((habit, i) => (
              <HabitCard
                key={habit.id}
                habit={habit}
                goals={goals}
                onCheckIn={complete}
                onDelete={del}
                onSetGoal={setGoal}
                index={i}
                busyId={busyId}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}