import React, { useCallback, useEffect, useMemo, useState } from 'react'
import { Target, Plus, Trash2, Loader2, Flag, CheckCircle2, BarChart2, AlertCircle, CheckSquare, Activity, X } from 'lucide-react'
import { goalService, habitService, taskService } from '../services/services'
import { extractErrorMessage } from '../utils/apiError'
import type { Goal, Habit, Task } from '../types'

/**
 * Progress bar.
 *
 * The count-up is done by CSS, not by JavaScript. The previous version ran a
 * `requestAnimationFrame` loop that called `setState` roughly 48 times per goal
 * over 800ms — so a screen of eight goals drove ~400 React renders purely to
 * animate a width, on top of the width transition that was already on the
 * element. The bar now renders its final width immediately and lets the
 * compositor run the transition; `animation-delay` preserves the staggered
 * reveal so the entrance still reads as sequential.
 */
const ProgressBar: React.FC<{ progress: number; index: number }> = ({ progress, index }) => (
  <div
    className="h-1.5 rounded-full bg-[rgb(var(--surface-4))] overflow-hidden relative"
    role="progressbar"
    aria-valuenow={Math.round(progress)}
    aria-valuemin={0}
    aria-valuemax={100}
    aria-label="Goal completion"
  >
    {/* Jade-only fill. The previous jade → tertiary gradient spent the "rare"
        secondary accent on the most ordinary element on the page, and made
        every goal bar a different colour span than the ring beside it. */}
    <div
      className="h-full rounded-full bg-[rgb(var(--accent))] transition-all duration-700 ease-out"
      style={{ width: `${Math.min(100, Math.max(0, progress))}%`, transitionDelay: `${index * 60}ms` }}
    />
  </div>
)

// === PROGRESS RING ===
//
// Same reasoning as the bar: `strokeDashoffset` transitions in CSS, the label
// shows the real value immediately, and the `blur-md` glow that pulsed behind
// the ring forever is gone. The stroke is a token colour rather than an SVG
// gradient, which also removes a duplicate `id="progressGradient"` that was
// being emitted once per goal card.
const ProgressRing: React.FC<{ progress: number; size?: number; index: number }> = ({
  progress,
  size = 56,
  index,
}) => {
  const radius = size / 2 - 4
  const circumference = 2 * Math.PI * radius
  const clamped = Math.min(100, Math.max(0, progress))
  const offset = circumference - (clamped / 100) * circumference

  return (
    <div
      className="relative shrink-0"
      style={{ width: size, height: size }}
      role="progressbar"
      aria-valuenow={Math.round(clamped)}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-label="Goal completion"
    >
      <svg width={size} height={size} className="transform -rotate-90" aria-hidden="true">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="rgb(var(--border))"
          strokeWidth="4"
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="rgb(var(--accent))"
          strokeWidth="4"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          className="transition-all duration-700 ease-out"
          style={{ transitionDelay: `${index * 60}ms` }}
        />
      </svg>
      {/* The figure, not a heading: tabular numerals, no display face. A ring is
          a readout, and the old display-serif number inside it was the only
          place on the page where a value was set in the heading typeface. */}
      <div className="absolute inset-0 flex items-center justify-center">
        <span className="typo-numeric text-[13px] font-bold text-[rgb(var(--text-primary))]">
          {Math.round(clamped)}%
        </span>
      </div>
    </div>
  )
}

// === METADATA LINE ===
//
// Category and status are two words of metadata, and they were carrying four
// coloured filled pills per card — amber-tinted "Complete", jade-tinted "In
// Progress", and a champagne "Category" chip. That put more chromatic
// information above the goal title than the title itself. Both are now plain
// text on the same line; status keeps a single dot because it is the one field
// that changes meaning, and "Complete" alone reads ambiguously without it.
const GoalMeta: React.FC<{ category?: string; isCompleted: boolean }> = ({ category, isCompleted }) => (
  <p className="typo-micro mb-2">
    {category && <span className="!normal-case !tracking-[0.06em] !font-normal">{category}</span>}
    {category && (
      <span className="w-1 h-1 rounded-full bg-[rgb(var(--border-strong))] inline-block align-middle mx-1.5" aria-hidden="true" />
    )}
    <span
      className={`inline-flex items-center gap-1.5 !normal-case !tracking-[0.06em] !font-normal ${
        isCompleted ? 'text-[rgb(var(--success))]' : ''
      }`}
    >
      {!isCompleted && (
        <span className="w-1 h-1 rounded-full bg-[rgb(var(--text-muted))] inline-block" aria-hidden="true" />
      )}
      {isCompleted ? 'Complete' : 'In progress'}
    </span>
  </p>
)

// === CONNECTED ITEM ROW ===
const LinkedRow: React.FC<{
  title: string
  meta: string
  icon: React.ComponentType<{ className?: string }>
  onUnlink: () => void
  disabled: boolean
}> = ({ title, meta, icon: Icon, onUnlink, disabled }) => (
  <div className="row-item !py-2 !px-3">
    <Icon className="w-3.5 h-3.5 shrink-0 text-[rgb(var(--text-tertiary))]" aria-hidden="true" />
    <span className="typo-body-sm !text-[13px] truncate !text-[rgb(var(--text-primary))]">{title}</span>
    {meta && <span className="typo-micro !text-[9px] !normal-case !tracking-normal ml-auto shrink-0">{meta}</span>}
    <button
      onClick={onUnlink}
      disabled={disabled}
      aria-label={`Remove ${title} from this goal`}
      title="Remove from goal"
      className="btn-icon !w-7 !h-7 shrink-0 focus-ring hover:!text-[rgb(var(--danger))] disabled:opacity-50"
    >
      <X className="w-3 h-3" />
    </button>
  </div>
)

// === GOAL CARD ===
interface GoalCardProps {
  goal: Goal
  linkedTasks: Task[]
  linkedHabits: Habit[]
  onUpdateProgress: (goal: Goal, progress: number) => void
  onDelete: (id: number) => void
  onUnlinkTask: (task: Task) => void
  onUnlinkHabit: (habit: Habit) => void
  index: number
  busyId: number | null
}

const GoalCard: React.FC<GoalCardProps> = ({ goal, linkedTasks, linkedHabits, onUpdateProgress, onDelete, onUnlinkTask, onUnlinkHabit, index, busyId }) => {
  const [showLinks, setShowLinks] = useState(false)
  const isBusy = busyId === goal.id
  const isComplete = goal.is_completed || goal.progress >= 100
  const linkCount = linkedTasks.length + linkedHabits.length

  return (
    <div
      className={`card-secondary p-5 space-y-4 stagger-in-fast ${
        isComplete ? '!border-[rgb(var(--success)/0.35)]' : ''
      }`}
      style={{ animationDelay: `${index * 80}ms` }}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <GoalMeta category={goal.category} isCompleted={isComplete} />
          <h3 className="typo-card-title truncate pr-2">{goal.title}</h3>
          {goal.description && (
            <p className="typo-body-sm mt-1.5 line-clamp-2">{goal.description}</p>
          )}
        </div>
        <button
          onClick={() => onDelete(goal.id)}
          disabled={isBusy}
          aria-label={`Delete ${goal.title}`}
          className="btn-icon focus-ring hover:!text-[rgb(var(--danger))] hover:!bg-[rgb(var(--danger)/0.1)] disabled:opacity-50"
        >
          <Trash2 className="w-4 h-4" />
        </button>
      </div>

      {/* Progress. The ring carries the figure and the bar the trend, side by
          side at matched scale. The previous version also printed "Completion
          62%" in bold display type between them, so the same number appeared
          three times on one card. */}
      <div className="flex items-center gap-5">
        <ProgressRing progress={goal.progress} size={56} index={index} />
        <div className="flex-1 min-w-0">
          <ProgressBar progress={goal.progress} index={index} />
        </div>
      </div>

      {!isComplete && (
        <div className="flex items-center justify-between gap-3 pt-3 border-t border-[rgb(var(--border-subtle))]">
          <span className="typo-micro">Adjust completion</span>
          <div className="flex items-center gap-2">
            <button
              onClick={() => onUpdateProgress(goal, Math.max(0, goal.progress - 10))}
              disabled={isBusy}
              className="btn-secondary btn-sm focus-ring disabled:opacity-50"
            >
              −10%
            </button>
            <button
              onClick={() => onUpdateProgress(goal, Math.min(100, goal.progress + 10))}
              disabled={isBusy}
              className="btn-primary btn-sm focus-ring disabled:opacity-50"
            >
              +10%
            </button>
          </div>
        </div>
      )}

      {isComplete && (
        <p className="flex items-center gap-2 pt-3 border-t border-[rgb(var(--border-subtle))] text-[13px] font-medium text-[rgb(var(--success))]">
          <CheckCircle2 className="w-4 h-4" aria-hidden="true" />
          Goal complete.
        </p>
      )}

      {/* Connected work — derived from task.goal_id / habit.goal_id */}
      <div className="pt-3.5 border-t border-[rgb(var(--border-subtle))]">
        <button
          onClick={() => setShowLinks(v => !v)}
          aria-expanded={showLinks}
          className="inline-flex items-center gap-2 -ml-1 rounded px-1 py-0.5 text-[13px] font-medium text-[rgb(var(--text-tertiary))] hover:text-[rgb(var(--accent))] transition-colors focus-ring"
        >
          <Target className="w-3.5 h-3.5" aria-hidden="true" />
          Connected work
          <span className="typo-micro !text-[9px] !tracking-normal !normal-case">{linkCount}</span>
        </button>

        {showLinks && (
          <div className="mt-3 row-stack animate-fadeInUp">
            {linkedTasks.length === 0 && linkedHabits.length === 0 ? (
              <p className="typo-meta px-1">
                No tasks or habits linked yet. Link them from the Tasks or Habits view.
              </p>
            ) : (
              <>
                {linkedTasks.map(task => (
                  <LinkedRow
                    key={`task-${task.id}`}
                    title={task.title}
                    meta={task.status === 'completed' ? 'done' : task.priority}
                    icon={CheckSquare}
                    disabled={isBusy}
                    onUnlink={() => onUnlinkTask(task)}
                  />
                ))}
                {linkedHabits.map(habit => (
                  <LinkedRow
                    key={`habit-${habit.id}`}
                    title={habit.title}
                    meta={`${habit.current_streak}d`}
                    icon={Activity}
                    disabled={isBusy}
                    onUnlink={() => onUnlinkHabit(habit)}
                  />
                ))}
              </>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

// === CREATE FORM ===
interface CreateFormProps {
  title: string
  setTitle: (v: string) => void
  category: string
  setCategory: (v: string) => void
  progress: number
  setProgress: (v: number) => void
  submitting: boolean
  error: string | null
  onSubmit: (e: React.FormEvent) => void
}

const CreateForm: React.FC<CreateFormProps> = ({ title, setTitle, category, setCategory, progress, setProgress, submitting, error, onSubmit }) => (
  <form onSubmit={onSubmit} className="card-input p-5 space-y-4 stagger-in" style={{ animationDelay: '80ms' }}>
    <p className="typo-label">New goal</p>
    <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
      <div className="relative">
        <input
          value={title}
          onChange={e => setTitle(e.target.value)}
          placeholder="Goal title…"
          aria-label="Goal title"
          required
          className="input input-icon-left"
        />
        <Target className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[rgb(var(--text-tertiary))] pointer-events-none" aria-hidden="true" />
      </div>
      <div className="relative">
        <input
          value={category}
          onChange={e => setCategory(e.target.value)}
          placeholder="Category (optional)"
          aria-label="Category"
          className="input input-icon-left"
        />
        <BarChart2 className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[rgb(var(--text-tertiary))] pointer-events-none" aria-hidden="true" />
      </div>
      <div className="flex items-center gap-3 h-[var(--control-h-lg)]">
        <input
          id="goal-progress-range"
          type="range"
          min={0}
          max={100}
          value={progress}
          onChange={e => setProgress(Number(e.target.value))}
          aria-label="Starting progress"
          className="flex-1 h-1.5 rounded-full accent-[rgb(var(--accent))] cursor-pointer bg-transparent"
        />
        <label htmlFor="goal-progress-range" className="typo-numeric text-[13px] font-semibold w-10 text-right shrink-0">
          {progress}%
        </label>
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
        Create goal
      </button>
    </div>
  </form>
)

// === EMPTY STATE ===
const EmptyState: React.FC<{ error: string | null; onRetry: () => void }> = ({ error, onRetry }) => (
  <div className="card-secondary p-8 flex flex-col items-center justify-center text-center stagger-in md:col-span-2">
    <span
      className={`grid place-items-center w-12 h-12 rounded-xl mb-4 ${
        error
          ? 'bg-[rgb(var(--danger)/0.1)] border border-[rgb(var(--danger)/0.25)] text-[rgb(var(--danger))]'
          : 'bg-[rgb(var(--surface-4))] border border-[rgb(var(--border-subtle))] text-[rgb(var(--text-tertiary))]'
      }`}
      aria-hidden="true"
    >
      {error ? <AlertCircle className="w-5 h-5" /> : <Flag className="w-5 h-5" />}
    </span>
    <h3 className="typo-card-title">{error ? 'Could not load your goals' : 'No goals yet'}</h3>
    <p className="typo-body-sm mt-1.5 max-w-sm">
      {error
        ? error
        : 'Define an objective above and attach tasks and habits to it. Progress is then tracked in one place.'}
    </p>
    {error && (
      <button onClick={onRetry} className="btn-primary btn-sm mt-5 focus-ring">
        <Loader2 className="w-4 h-4" aria-hidden="true" /> Try again
      </button>
    )}
  </div>
)

// === LOADING SKELETON ===
const GoalSkeleton: React.FC = () => (
  <div className="row-stack stagger-in-fast md:col-span-2" aria-busy="true" aria-label="Loading goals">
    {[1, 2].map(i => (
      <div key={i} className="card-secondary p-5 space-y-4">
        <div className="w-40 h-3 skeleton rounded-full" />
        <div className="w-full h-1.5 skeleton rounded-full" />
        <div className="w-28 h-7 skeleton rounded-lg" />
      </div>
    ))}
  </div>
)

// === MAIN COMPONENT ===
export const GoalsView: React.FC = () => {
  const [goals, setGoals] = useState<Goal[]>([])
  const [tasks, setTasks] = useState<Task[]>([])
  const [habits, setHabits] = useState<Habit[]>([])
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [title, setTitle] = useState('')
  const [category, setCategory] = useState('Career')
  const [progress, setProgress] = useState(0)
  const [busyId, setBusyId] = useState<number | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setLoadError(null)
    try {
      const [goalRes, taskRes, habitRes] = await Promise.all([
        goalService.getGoals(),
        taskService.getTasks().catch(() => []),
        habitService.getHabits().catch(() => []),
      ])
      setGoals(Array.isArray(goalRes) ? goalRes : [])
      setTasks(Array.isArray(taskRes) ? taskRes : [])
      setHabits(Array.isArray(habitRes) ? habitRes : [])
    } catch (e) {
      setGoals([])
      setLoadError(extractErrorMessage(e, 'Failed to load goals.'))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  // Connected work is derived from the task/habit goal_id fields.
  const linkedByGoal = useMemo(() => {
    const map = new Map<number, { tasks: Task[]; habits: Habit[] }>()
    goals.forEach(g => map.set(g.id, { tasks: [], habits: [] }))
    tasks.forEach(t => {
      if (t.goal_id != null && map.has(t.goal_id)) map.get(t.goal_id)!.tasks.push(t)
    })
    habits.forEach(h => {
      if (h.goal_id != null && map.has(h.goal_id)) map.get(h.goal_id)!.habits.push(h)
    })
    return map
  }, [goals, tasks, habits])

  const create = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!title.trim()) return

    setSubmitting(true)
    setFormError(null)
    try {
      await goalService.createGoal({
        title: title.trim(),
        category: category.trim() || 'general',
        progress: Number(progress),
      })
      setTitle('')
      setProgress(0)
      await load()
    } catch (e) {
      setFormError(extractErrorMessage(e, 'Could not create the goal.'))
    } finally {
      setSubmitting(false)
    }
  }

  const del = async (id: number) => {
    if (!window.confirm('Delete this goal? Linked tasks and habits will be unlinked.')) return
    setBusyId(id)
    try {
      await goalService.deleteGoal(id)
      await load()
    } catch (e) {
      setLoadError(extractErrorMessage(e, 'Could not delete the goal.'))
    } finally {
      setBusyId(null)
    }
  }

  const bump = async (g: Goal, v: number) => {
    const clamped = Math.max(0, Math.min(100, v))
    const isCompleted = clamped >= 100
    setBusyId(g.id)
    setGoals(prev => prev.map(x => x.id === g.id ? { ...x, progress: clamped, is_completed: isCompleted } : x))
    try {
      await goalService.updateGoal(g.id, { progress: clamped, is_completed: isCompleted })
      await load()
    } catch (e) {
      setGoals(prev => prev.map(x => x.id === g.id ? g : x))
      setLoadError(extractErrorMessage(e, 'Could not update progress.'))
    } finally {
      setBusyId(null)
    }
  }

  const unlinkTask = async (task: Task) => {
    setBusyId(task.goal_id ?? null)
    try {
      // Explicit null clears the relationship; omitted fields are untouched.
      await taskService.updateTask(task.id, { goal_id: null })
      await load()
    } catch (e) {
      setLoadError(extractErrorMessage(e, 'Could not unlink the task.'))
    } finally {
      setBusyId(null)
    }
  }

  const unlinkHabit = async (habit: Habit) => {
    setBusyId(habit.goal_id ?? null)
    try {
      await habitService.updateHabit(habit.id, { goal_id: null })
      await load()
    } catch (e) {
      setLoadError(extractErrorMessage(e, 'Could not unlink the habit.'))
    } finally {
      setBusyId(null)
    }
  }

  return (
    <div className="relative space-y-6 animate-fadeInUp">
      {/* === HEADER ===
          No 40px tinted icon tile: the page heading is typography. Every view
          used to open with one, so the shell, not the content, was what the eye
          met first. The label above the title carries the same orientation the
          tile did, at zero cost. */}
      <div className="stagger-in">
        <p className="section-header-label !m-0 !p-0">
          <Target className="w-3.5 h-3.5 !text-[rgb(var(--accent))]" aria-hidden="true" />
          Objectives
        </p>
        <h1 className="typo-h1 mt-2">Goals</h1>
        <p className="typo-meta mt-1.5">
          Long-term objectives, their progress, and the work attached to them.
        </p>
      </div>

      {/* === CREATE FORM === */}
      <CreateForm
        title={title}
        setTitle={setTitle}
        category={category}
        setCategory={setCategory}
        progress={progress}
        setProgress={setProgress}
        submitting={submitting}
        error={formError}
        onSubmit={create}
      />

      {/* === GOALS GRID === */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 stagger-in" style={{ animationDelay: '160ms' }}>
        {loading ? (
          <GoalSkeleton />
        ) : goals.length === 0 ? (
          <EmptyState error={loadError} onRetry={load} />
        ) : (
          goals.map((goal, i) => (
            <GoalCard
              key={goal.id}
              goal={goal}
              linkedTasks={linkedByGoal.get(goal.id)?.tasks || []}
              linkedHabits={linkedByGoal.get(goal.id)?.habits || []}
              onUpdateProgress={bump}
              onDelete={del}
              onUnlinkTask={unlinkTask}
              onUnlinkHabit={unlinkHabit}
              index={i}
              busyId={busyId}
            />
          ))
        )}
      </div>
    </div>
  )
}