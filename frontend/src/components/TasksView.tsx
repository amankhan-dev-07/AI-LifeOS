import React, { useCallback, useEffect, useMemo, useState } from 'react'
import { CheckSquare, Plus, Trash2, Loader2, Terminal, Target, Clock, AlertCircle, Unlink } from 'lucide-react'
import { goalService, taskService } from '../services/services'
import { extractErrorMessage } from '../utils/apiError'
import { RemindMeButton } from './RemindMeButton'
import type { Goal, Task } from '../types'

// === PRIORITY BADGE ===
//
// The glyph is static. It used to carry `animate-pulse` on an 800ms/2s loop
// forever per row, so a screen of 20 tasks ran 20 concurrent compositor
// animations to convey a value that never changed.
//
// It is now a dot plus a word rather than an emoji plus a word. The emoji
// (⚡ ▲ ● ○) rendered at the platform's own colour and metrics — outside the
// token system — and on a 20-row list that was 20 off-palette glyphs.
const PriorityBadge: React.FC<{ priority: Task['priority'] }> = ({ priority }) => {
  const configs: Record<Task['priority'], { dot: string; text: string }> = {
    urgent: { dot: 'bg-[rgb(var(--danger))]', text: 'text-[rgb(var(--danger))]' },
    high: { dot: 'bg-[rgb(var(--warning))]', text: 'text-[rgb(var(--warning))]' },
    medium: { dot: 'bg-[rgb(var(--text-tertiary))]', text: 'text-[rgb(var(--text-tertiary))]' },
    low: { dot: 'bg-[rgb(var(--text-muted))]', text: 'text-[rgb(var(--text-muted))]' },
  }
  const c = configs[priority]
  return (
    <span className={`inline-flex items-center gap-1.5 text-[11px] font-medium capitalize ${c.text}`}>
      <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${c.dot}`} aria-hidden="true" />
      {priority}
    </span>
  )
}

// === GOAL ASSIGNMENT CONTROL ===
const GoalSelect: React.FC<{
  value: number | null
  goals: Goal[]
  onChange: (goalId: number | null) => void
  disabled: boolean
  useInputClass?: boolean
}> = ({ value, goals, onChange, disabled, useInputClass = false }) => {
  if (!value) {
    // No goal is auto-assigned: the user picks explicitly from the dropdown.
    return (
      <select
        value=""
        disabled={disabled || goals.length === 0}
        onChange={e => e.target.value && onChange(Number(e.target.value))}
        aria-label="Assign to a goal"
        className={`h-7 pl-5 pr-10 rounded-full text-[10px] font-mono bg-[rgb(var(--surface) / 0.6)] border border-dashed border-[rgb(var(--border))] text-[rgb(var(--text-tertiary))] hover:text-[rgb(var(--accent))] hover:border-[rgb(var(--accent) / 0.4)] focus-ring disabled:opacity-50 cursor-pointer input ${useInputClass ? '' : ''}`}
        title={goals.length === 0 ? 'Create a goal first' : 'Assign to a goal'}
      >
        <option value="">{goals.length === 0 ? 'No goals yet' : '+ Link goal'}</option>
        {goals.map(g => <option key={g.id} value={g.id}>{g.title}</option>)}
      </select>
    )
  }

  const current = goals.find(g => g.id === value)

  return (
    <span className="inline-flex items-center gap-1.5">
      <select
        value={value}
        disabled={disabled}
        onChange={e => onChange(Number(e.target.value))}
        aria-label={`Goal for this task, currently ${current?.title ?? 'unknown'}`}
        className={`h-7 pl-2 pr-10 rounded-full text-[10px] font-mono bg-[rgb(var(--accent) / 0.12)] border border-[rgb(var(--accent) / 0.3)] text-[rgb(var(--accent))] focus-ring cursor-pointer input ${useInputClass ? '' : ''}`}
      >
        {goals.map(g => <option key={g.id} value={g.id}>{g.title}</option>)}
      </select>
      <button
        onClick={() => onChange(null)}
        disabled={disabled}
        aria-label={`Remove ${current?.title ?? 'goal'} link`}
        title="Remove from goal"
        className="inline-flex items-center justify-center w-7 h-7 rounded-full text-[10px] font-mono bg-[rgb(var(--surface) / 0.6)] border border-[rgb(var(--border))] text-[rgb(var(--text-tertiary))] hover:text-[rgb(var(--danger))] hover:border-[rgb(var(--danger) / 0.3)] transition-colors duration-200 focus-ring disabled:opacity-50"
      >
        <Unlink className="w-3 h-3" />
      </button>
    </span>
  )
}

// === TASK ROW ===
interface TaskRowProps {
  task: Task
  goals: Goal[]
  onToggle: (task: Task) => void
  onDelete: (id: number) => void
  onSetGoal: (task: Task, goalId: number | null) => void
  index: number
  busyId: number | null
}

const TaskRow: React.FC<TaskRowProps> = ({ task, goals, onToggle, onDelete, onSetGoal, index, busyId }) => {
  const isBusy = busyId === task.id
  const isCompleted = task.status === 'completed'

  return (
    // A hairline-separated row rather than its own card. Each task previously
    // carried a border, a shadow, a radius and a lift-on-hover, nested inside a
    // card that carried the same — a list of 25 tasks was 26 boxes.
    <div
      className={`row-item !items-center !p-3.5 stagger-in-fast ${isCompleted ? 'opacity-60' : ''}`}
      style={{ animationDelay: `${index * 40}ms` }}
    >
      <label className="flex items-center gap-3 min-w-0 flex-1 cursor-pointer group">
        <div className="relative shrink-0">
          <input
            type="checkbox"
            checked={isCompleted}
            onChange={() => onToggle(task)}
            disabled={isBusy}
            className="sr-only peer"
          />
          <div
            className={`w-5 h-5 rounded-md border-2 transition-colors duration-200 flex items-center justify-center ${
              isCompleted
                ? 'bg-[rgb(var(--accent))] border-[rgb(var(--accent))]'
                : 'border-[rgb(var(--border-strong))] group-hover:border-[rgb(var(--accent) / 0.6)] peer-focus-visible:ring-2 peer-focus-visible:ring-[rgb(var(--accent) / 0.4)] bg-[rgb(var(--surface-4))]'
            }`}
          >
            {isCompleted && (
              <svg className="w-3.5 h-3.5 text-[rgb(var(--text-inverse))] stroke-current" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3">
                <polyline points="20 6 9 17 4 12" />
              </svg>
            )}
            {isBusy && !isCompleted && (
              <Loader2 className="w-3.5 h-3.5 text-[rgb(var(--accent))] animate-spin" />
            )}
          </div>
        </div>

        <div className="min-w-0">
          <p
            className={`typo-body-sm !font-medium !leading-tight truncate transition-colors ${
              isCompleted
                ? 'line-through text-[rgb(var(--text-tertiary))]'
                : 'text-[rgb(var(--text-primary))]'
            }`}
          >
            {task.title}
          </p>
          <div className="mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-1.5">
            <PriorityBadge priority={task.priority} />
            <span className="w-1 h-1 rounded-full bg-[rgb(var(--border-strong))]" aria-hidden="true" />
            <span className="inline-flex items-center gap-1 text-[11px] font-mono text-[rgb(var(--text-tertiary))]">
              <Clock className="w-3 h-3" aria-hidden="true" /> {task.estimated_minutes ?? 45}m
            </span>
            <GoalSelect value={task.goal_id ?? null} goals={goals} onChange={(goalId) => onSetGoal(task, goalId)} disabled={isBusy} useInputClass />
          </div>
        </div>
      </label>

      <div className="flex items-center gap-1 shrink-0">
        <RemindMeButton target={{ kind: 'task', id: task.id, label: task.title }} />
        <button
          onClick={() => onDelete(task.id)}
          disabled={isBusy}
          aria-label={`Delete ${task.title}`}
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
  priority: Task['priority']
  setPriority: (v: Task['priority']) => void
  goalId: number | null
  setGoalId: (v: number | null) => void
  estimatedMinutes: number
  setEstimatedMinutes: (v: number) => void
  goals: Goal[]
  submitting: boolean
  error: string | null
  onSubmit: (e: React.FormEvent) => void
}

const CreateForm: React.FC<CreateFormProps> = ({
  title, setTitle, priority, setPriority, goalId, setGoalId,
  estimatedMinutes, setEstimatedMinutes, goals, submitting, error, onSubmit,
}) => (
  /* A working area, not a content card: level-2 fill, hairline border, no
     shadow. The gradient hairline along the top edge is gone — a jade→nothing
     line above a box that is already the app's only accent fill on this page
     read as a second, competing call to action. */
  <form
    onSubmit={onSubmit}
    className="card-input p-5 space-y-4 stagger-in"
    style={{ animationDelay: '80ms' }}
  >
    <div className="flex items-center justify-between">
      <h3 className="typo-label !text-[rgb(var(--text-primary))]">New task</h3>
      <Target className="w-4 h-4 text-[rgb(var(--text-muted))]" aria-hidden="true" />
    </div>

    <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
      <div className="relative md:col-span-2">
        <input
          value={title}
          onChange={e => setTitle(e.target.value)}
          placeholder="Task title…"
          aria-label="Task title"
          required
          className="input input-icon-left"
        />
        <CheckSquare className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-[rgb(var(--text-muted))] pointer-events-none" aria-hidden="true" />
      </div>
      <div className="relative">
        <select
          value={priority}
          onChange={e => setPriority(e.target.value as Task['priority'])}
          aria-label="Priority"
          className="input"
        >
          <option value="low">Low</option>
          <option value="medium">Medium</option>
          <option value="high">High</option>
          <option value="urgent">Urgent</option>
        </select>
      </div>
      <div className="relative">
        <input
          type="number"
          min={1}
          max={1440}
          value={estimatedMinutes}
          onChange={e => setEstimatedMinutes(Number(e.target.value))}
          aria-label="Estimated minutes"
          className="input input-icon-left"
        />
        <Clock className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-[rgb(var(--text-muted))] pointer-events-none" aria-hidden="true" />
      </div>
      <div className="relative md:col-span-4">
        <select
          value={goalId ?? ''}
          onChange={e => setGoalId(e.target.value ? Number(e.target.value) : null)}
          aria-label="Linked goal"
          className="input"
        >
          <option value="">No linked goal</option>
          {goals.map(g => <option key={g.id} value={g.id}>{g.title}</option>)}
        </select>
      </div>
    </div>

    {error && (
      <p role="alert" className="text-[13px] text-[rgb(var(--danger))] flex items-center gap-1.5">
        <AlertCircle className="w-3.5 h-3.5 shrink-0" aria-hidden="true" /> {error}
      </p>
    )}

    <div className="flex justify-end pt-1">
      <button
        type="submit"
        disabled={submitting || !title.trim()}
        className="btn-primary focus-ring"
      >
        {submitting ? <Loader2 className="w-4 h-4 animate-spin" aria-hidden="true" /> : <Plus className="w-4 h-4" aria-hidden="true" />} Add task
      </button>
    </div>
  </form>
)

// === FILTER TABS ===
//
// A segmented control at control height, sharing the input system. The old
// version was a bordered container holding three pills whose active state was a
// 12%-accent fill *plus* an accent border — the same double-signal problem the
// sidebar had. Active is now a solid level-4 fill plus primary text.
const FilterTabs: React.FC<{
  filter: 'all' | 'todo' | 'completed'
  onChange: (f: 'all' | 'todo' | 'completed') => void
}> = ({ filter, onChange }) => (
  <div
    role="tablist"
    aria-label="Filter tasks"
    className="inline-flex p-1 rounded-lg bg-[rgb(var(--surface-2))] border border-[rgb(var(--border))] stagger-in"
    style={{ animationDelay: '120ms' }}
  >
    {(['all', 'todo', 'completed'] as const).map(f => (
      <button
        key={f}
        role="tab"
        aria-selected={filter === f}
        onClick={() => onChange(f)}
        className={`h-9 px-3.5 rounded-md text-[13px] font-medium capitalize transition-colors duration-200 focus-ring ${
          filter === f
            ? 'bg-[rgb(var(--surface-4))] text-[rgb(var(--text-primary))] shadow-[var(--depth-1)]'
            : 'text-[rgb(var(--text-tertiary))] hover:text-[rgb(var(--text-primary))]'
        }`}
      >
        {f}
      </button>
    ))}
  </div>
)

// === EMPTY STATE ===
const EmptyState: React.FC<{
  filter: 'all' | 'todo' | 'completed'
  error: string | null
  onRetry: () => void
}> = ({ filter, error, onRetry }) => (
  <div className="py-10 flex flex-col items-center justify-center text-center stagger-in">
    {error ? (
      <AlertCircle className="w-8 h-8 text-[rgb(var(--danger))] mb-4" aria-hidden="true" />
    ) : (
      <span className="grid place-items-center w-12 h-12 rounded-xl bg-[rgb(var(--surface-2))] border border-[rgb(var(--border-subtle))] mb-4">
        <Terminal className="w-5 h-5 text-[rgb(var(--accent))]" aria-hidden="true" />
      </span>
    )}
    <h3 className="typo-card-title !text-lg">
      {error
        ? 'Could not load your tasks'
        : filter === 'completed'
          ? 'No completed tasks'
          : filter === 'todo'
            ? 'No pending tasks'
            : 'No tasks yet'}
    </h3>
    <p className="typo-body-sm mt-2 max-w-[42ch]">
      {error
        ? error
        : filter === 'completed'
          ? 'Completed tasks appear here so you can review what is already done.'
          : filter === 'todo'
            ? 'All caught up. Create a task above whenever something new comes in.'
            : 'Create your first task above to start organizing your work.'}
    </p>
    {error && (
      <button onClick={onRetry} className="btn-primary btn-sm mt-5 focus-ring">
        <Loader2 className="w-4 h-4" aria-hidden="true" /> Try again
      </button>
    )}
  </div>
)

// === LOADING SKELETON ===
//
// The old skeleton wrapped itself in `animate-pulse`, which dims the whole
// block on a 2s loop *and* conflicted with the per-child shimmer — two
// simultaneous animations on the same subtree. `.skeleton` alone gives the
// same "loading" signal at a fraction of the cost.
const TaskSkeleton: React.FC = () => (
  <div className="row-stack" aria-busy="true" aria-label="Loading tasks">
    {[1, 2, 3].map(i => (
      <div key={i} className="flex items-center gap-3 px-4 py-3.5">
        <div className="w-5 h-5 rounded-md skeleton" />
        <div className="flex-1 space-y-2">
          <div className="h-4 w-3/4 skeleton rounded" />
          <div className="h-3 w-1/2 skeleton rounded" />
        </div>
        <div className="w-10 h-10 skeleton rounded-lg" />
      </div>
    ))}
  </div>
)

// === MAIN COMPONENT ===
export const TasksView: React.FC = () => {
  const [tasks, setTasks] = useState<Task[]>([])
  const [goals, setGoals] = useState<Goal[]>([])
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [title, setTitle] = useState('')
  const [priority, setPriority] = useState<Task['priority']>('medium')
  const [goalId, setGoalId] = useState<number | null>(null)
  const [estimatedMinutes, setEstimatedMinutes] = useState(45)
  const [filter, setFilter] = useState<'all' | 'todo' | 'completed'>('all')
  const [busyId, setBusyId] = useState<number | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setLoadError(null)
    try {
      const [taskRes, goalRes] = await Promise.all([
        taskService.getTasks(),
        goalService.getGoals().catch(() => []),
      ])
      setTasks(Array.isArray(taskRes) ? taskRes : [])
      setGoals(Array.isArray(goalRes) ? goalRes : [])
    } catch (e) {
      setTasks([])
      setLoadError(extractErrorMessage(e, 'Failed to load tasks.'))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!title.trim()) return

    setSubmitting(true)
    setFormError(null)
    try {
      await taskService.createTask({
        title: title.trim(),
        priority,
        status: 'todo',
        goal_id: goalId,
        estimated_minutes: estimatedMinutes,
      })
      setTitle('')
      setPriority('medium')
      setGoalId(null)
      setEstimatedMinutes(45)
      await load()
    } catch (e) {
      setFormError(extractErrorMessage(e, 'Could not create the task.'))
    } finally {
      setSubmitting(false)
    }
  }

  // Send only the changed field so the backend's PATCH/PUT semantics treat
  // omitted fields as "unchanged" and explicit null as "clear".
  const toggle = async (task: Task) => {
    setBusyId(task.id)
    try {
      await taskService.updateTask(task.id, { status: task.status === 'completed' ? 'todo' : 'completed' })
      await load()
    } catch (e) {
      setLoadError(extractErrorMessage(e, 'Could not update the task.'))
    } finally {
      setBusyId(null)
    }
  }

  const setGoal = async (task: Task, nextGoalId: number | null) => {
    setBusyId(task.id)
    // Optimistic update; rolled back to server truth on failure.
    setTasks(prev => prev.map(t => (t.id === task.id ? { ...t, goal_id: nextGoalId } : t)))
    try {
      await taskService.updateTask(task.id, { goal_id: nextGoalId })
      await load()
    } catch (e) {
      setTasks(prev => prev.map(t => (t.id === task.id ? { ...t, goal_id: task.goal_id } : t)))
      setLoadError(extractErrorMessage(e, 'Could not update the goal link.'))
    } finally {
      setBusyId(null)
    }
  }

  const del = async (id: number) => {
    setBusyId(id)
    try {
      await taskService.deleteTask(id)
      await load()
    } catch (e) {
      setLoadError(extractErrorMessage(e, 'Could not delete the task.'))
    } finally {
      setBusyId(null)
    }
  }

  const filtered = useMemo(() => tasks.filter(t =>
    filter === 'todo' ? t.status !== 'completed' :
    filter === 'completed' ? t.status === 'completed' : true
  ), [tasks, filter])

  return (
    <div className="relative space-y-6 animate-fadeInUp">
      {/* === HEADER ===
          Page title in display type with a supporting sentence — no 40px tinted
          icon tile beside the H1. The tile repeated the accent at the same
          moment as the page's only primary action (Add task), so the two jade
          marks competed for the first glance down the page. */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 stagger-in">
        <div className="min-w-0">
          <p className="section-header-label !m-0 !p-0">Work</p>
          <h1 className="typo-h1 mt-1.5">Tasks</h1>
          <p className="typo-meta mt-1.5">
            Everything you have open, with priority and goal links.
          </p>
        </div>
        <FilterTabs filter={filter} onChange={setFilter} />
      </div>

      {/* === CREATE FORM === */}
      <CreateForm
        title={title}
        setTitle={setTitle}
        priority={priority}
        setPriority={setPriority}
        goalId={goalId}
        setGoalId={setGoalId}
        estimatedMinutes={estimatedMinutes}
        setEstimatedMinutes={setEstimatedMinutes}
        goals={goals}
        submitting={submitting}
        error={formError}
        onSubmit={handleCreate}
      />

      {/* === TASK LIST ===
          The container is the card; the rows inside are not. */}
      <div className="stagger-in" style={{ animationDelay: '160ms' }}>
        {loading ? (
          <TaskSkeleton />
        ) : filtered.length === 0 ? (
          <div className="card-secondary">
            <EmptyState filter={filter} error={loadError} onRetry={load} />
          </div>
        ) : (
          <div className="row-stack">
            {loadError && (
              <div role="alert" className="flex items-start gap-2 text-[13px] text-[rgb(var(--danger))] px-4 py-3 border-b border-[rgb(var(--border-subtle))]">
                <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" aria-hidden="true" /> {loadError}
              </div>
            )}
            {filtered.map((task, i) => (
              <TaskRow
                key={task.id}
                task={task}
                goals={goals}
                onToggle={toggle}
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