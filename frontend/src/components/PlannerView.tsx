import React, { useCallback, useEffect, useMemo, useState } from 'react'
import {
  Calendar, Clock, Target, Activity, CheckCircle2, TrendingUp, Loader2, AlertCircle,
  Plus, Trash2, Pencil, ChevronLeft, ChevronRight, Check, Flag,
} from 'lucide-react'
import { plannerService, taskService, habitService, goalService } from '../services/services'
import { extractErrorMessage } from '../utils/apiError'
import { RemindMeButton } from './RemindMeButton'
import { dateKeyOfNaive, formatLongDate, formatTimeOnly, shiftDateKey, toLocalDateKey, toNaiveIso } from '../utils/datetime'
import type { Goal, Habit, PlannerEvent, PlannerEventType, Task } from '../types'

/**
 * Event-type palette.
 *
 * Four semantic types need four distinguishable treatments, but they are now
 * drawn from the token set (accent / accent-secondary / accent-tertiary /
 * neutral) rather than four unrelated Tailwind hues. The mapping stays
 * one-to-one so a Task block and a Focus block never read the same.
 */
const EVENT_TYPES: {
  value: PlannerEventType
  label: string
  color: string
  dot: string
}[] = [
  {
    value: 'task',
    label: 'Task',
    color: 'text-[rgb(var(--accent-tertiary))]',
    dot: 'bg-[rgb(var(--accent-tertiary))]',
  },
  {
    value: 'habit',
    label: 'Habit',
    color: 'text-[rgb(var(--accent))]',
    dot: 'bg-[rgb(var(--accent))]',
  },
  {
    value: 'focus_block',
    label: 'Focus',
    color: 'text-[rgb(var(--warning))]',
    dot: 'bg-[rgb(var(--warning))]',
  },
  {
    value: 'custom',
    label: 'Custom',
    color: 'text-[rgb(var(--text-tertiary))]',
    dot: 'bg-[rgb(var(--text-tertiary))]',
  },
]

const typeConfig = (value: string) => EVENT_TYPES.find(t => t.value === value) || EVENT_TYPES[3]

// === TIMELINE MARKER ===
//
// Was a `setTimeout` + `setState` scale-in per marker, plus a `white/20` inner
// gradient. The marker now fades in on a CSS delay and takes its colour from the
// event-type token.
const TimelineMarker: React.FC<{ type: PlannerEventType; index: number }> = ({ type, index }) => {
  const c = typeConfig(type)

  return (
    <div className="relative flex items-start gap-3 shrink-0 w-5">
      <div
        className={`relative w-3 h-3 rounded-full animate-fadeIn ${c.dot}`}
        style={{ animationDelay: `${index * 60}ms` }}
        aria-hidden="true"
      />
      <div className="absolute top-3 bottom-0 left-1.5 w-px bg-[rgb(var(--border-subtle))]" aria-hidden="true" />
    </div>
  )
}

// === TIMELINE ENTRY ===
interface PlanEntryProps {
  event: PlannerEvent
  index: number
  busyId: number | null
  onToggleComplete: (event: PlannerEvent) => void
  onEdit: (event: PlannerEvent) => void
  onDelete: (event: PlannerEvent) => void
}

const PlanEntry: React.FC<PlanEntryProps> = ({ event, index, busyId, onToggleComplete, onEdit, onDelete }) => {
  const config = typeConfig(event.event_type)
  const isBusy = busyId === event.id

  return (
    <button
      type="button"
      className={`row-item !p-4 flex-col md:flex-row !items-start md:!items-center !gap-4 stagger-in-fast ${
        event.is_completed ? '!opacity-60' : ''
      }`}
      style={{ animationDelay: `${100 + index * 50}ms` }}
    >
      <TimelineMarker type={event.event_type} index={index} />

      <div className="flex-1 min-w-0 flex flex-col md:flex-row md:items-center gap-3">
        {/* Time gutter */}
        <div className="flex items-center gap-3 shrink-0 md:w-[11rem]">
          <span className="typo-numeric text-[14px] font-semibold shrink-0 w-[5rem] text-right border-r border-r-[rgb(var(--border-subtle))] pr-3 group-hover:border-r-[rgb(var(--accent))] transition-colors">
            {formatTimeOnly(event.start_time)}
          </span>
          <span className="typo-micro text-[9px] !tracking-normal w-[5.5rem] text-left">
            {formatTimeOnly(event.end_time)}
          </span>
        </div>

        {/* Content */}
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 mb-1.5 flex-wrap">
            <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${config.dot}`} aria-hidden="true" />
            <span className={`typo-micro !normal-case !tracking-[0.06em] !font-normal ${config.color}`}>{config.label}</span>
            {event.task_id && (
              <span className="typo-micro text-[9px] !normal-case !tracking-normal text-[rgb(var(--accent-tertiary))]">Task #{event.task_id}</span>
            )}
            {event.habit_id && (
              <span className="typo-micro text-[9px] !normal-case !tracking-normal text-[rgb(var(--accent))]">Habit #{event.habit_id}</span>
            )}
          </div>

          <h3
            className={`typo-body !font-semibold !leading-tight !text-[rgb(var(--text-primary))] mb-1 ${
              event.is_completed ? 'line-through' : ''
            }`}
          >
            {event.title}
          </h3>

          {event.description && (
            <p className="typo-body-sm line-clamp-2">{event.description}</p>
          )}
        </div>

        {/* Actions */}
        <div className="flex items-center gap-1.5 shrink-0">
          <button
            onClick={(e) => { e.stopPropagation(); onToggleComplete(event) }}
            disabled={isBusy}
            aria-pressed={event.is_completed}
            aria-label={event.is_completed ? `Mark ${event.title} as not completed` : `Mark ${event.title} as completed`}
            title={event.is_completed ? 'Mark as not completed' : 'Mark as completed'}
            className={`btn-icon focus-ring ${event.is_completed
              ? '!text-[rgb(var(--success))] hover:!bg-[rgb(var(--success)/0.1)]'
              : '!text-[rgb(var(--text-tertiary))] hover:!text-[rgb(var(--success))] hover:!bg-[rgb(var(--success)/0.1)]'
            } disabled:opacity-50`}
          >
            {isBusy ? <Loader2 className="w-4 h-4 animate-spin" aria-hidden="true" /> : <Check className="w-4 h-4" />}
          </button>
          <button
            onClick={(e) => { e.stopPropagation(); onEdit(event) }}
            disabled={isBusy}
            aria-label={`Edit ${event.title}`}
            className="btn-icon focus-ring hover:!text-[rgb(var(--accent))] disabled:opacity-50"
          >
            <Pencil className="w-4 h-4" />
          </button>
          <RemindMeButton target={{ kind: 'planner_event', id: event.id, label: event.title }} />
          <button
            onClick={(e) => { e.stopPropagation(); onDelete(event) }}
            disabled={isBusy}
            aria-label={`Delete ${event.title}`}
            className="btn-icon focus-ring hover:!text-[rgb(var(--danger))] hover:!bg-[rgb(var(--danger)/0.1)] disabled:opacity-50"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      </div>
    </button>
  )
}

// === GOAL CARD ===
const GoalCard: React.FC<{ goal: Goal; index: number }> = ({ goal, index }) => (
  <div
    className="row-item !p-3 stagger-in-fast"
    style={{ animationDelay: `${200 + index * 60}ms` }}
  >
    <div className="flex items-center gap-3 min-w-0">
      <Target className="w-3.5 h-3.5 shrink-0 text-[rgb(var(--accent-secondary))]" aria-hidden="true" />
      <div className="min-w-0">
        <h4 className="typo-body-sm !font-semibold !leading-tight !text-[rgb(var(--text-primary))] truncate">
          {goal.title}
        </h4>
        {goal.category && (
          <span className="typo-micro mt-1 !normal-case !tracking-[0.06em] !font-normal text-[rgb(var(--accent-secondary))]">{goal.category}</span>
        )}
      </div>
      {goal.target_date && (
        <span className="typo-micro shrink-0 text-[9px] !normal-case !tracking-normal text-[rgb(var(--text-tertiary))]">
          Due {new Date(goal.target_date).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}
        </span>
      )}
    </div>
  </div>
)

/**
 * Stat block.
 *
 * This ran a `requestAnimationFrame` loop calling `setState` on every frame for
 * each of the four tiles — about 144 renders just to count four integers — and
 * each tile's icon floated forever on an infinite animation. The value is now
 * rendered directly and the icon is static.
 *
 * The 40px icon tile and display-serif number are gone. A stat is now a single
 * figure with a label beneath it, sitting on a surface-2 card — the same visual
 * language as the Attention Center tiles.
 */
const StatBlock: React.FC<{
  label: string
  value: number
  icon: React.ComponentType<{ className?: string }>
  index: number
}> = ({ label, value, icon: Icon, index }) => (
  <div className="card-secondary p-5 text-center stagger-in-fast" style={{ animationDelay: `${300 + index * 60}ms` }}>
    <Icon className="w-5 h-5 mx-auto text-[rgb(var(--text-tertiary))]" aria-hidden="true" />
    <div className="typo-numeric mt-2 text-[22px] font-bold leading-none text-[rgb(var(--text-primary))]">
      {value}
    </div>
    <span className="typo-micro mt-1 block">{label}</span>
  </div>
)

// === EMPTY STATE ===
const EmptyPlanState: React.FC<{ onCreate: () => void }> = ({ onCreate }) => (
  <div className="card-secondary p-8 flex flex-col items-center justify-center text-center stagger-in">
    <span className="grid place-items-center w-12 h-12 rounded-xl mb-4 bg-[rgb(var(--surface-4))] border border-[rgb(var(--border-subtle))] text-[rgb(var(--text-tertiary))]" aria-hidden="true">
      <Calendar className="w-5 h-5" />
    </span>
    <h3 className="typo-card-title">No events scheduled</h3>
    <p className="typo-body-sm mt-1.5 max-w-sm">
      Block out time for a task, a habit, a focus session, or anything custom. Everything you
      add here is saved to your account.
    </p>
    <button onClick={onCreate} className="btn-primary btn-sm mt-5 focus-ring">
      <Plus className="w-4 h-4" aria-hidden="true" /> Add first event
    </button>
  </div>
)

// === LOADING SKELETON ===
const PlannerSkeleton: React.FC = () => (
  <div className="row-stack" aria-busy="true" aria-label="Loading planner events">
    {[1, 2, 3].map(i => (
      <div key={i} className="row-item !p-4">
        <div className="w-3 h-3 rounded-full skeleton mt-2 shrink-0" />
        <div className="flex-1 min-w-0 space-y-2">
          <div className="w-40 h-4 skeleton rounded" />
          <div className="w-28 h-3 skeleton rounded" />
        </div>
        <div className="w-20 h-8 skeleton rounded-lg shrink-0" />
      </div>
    ))}
  </div>
)

// === ERROR STATE ===
const ErrorState: React.FC<{ message: string; onRetry: () => void }> = ({ message, onRetry }) => (
  <div className="card-secondary p-8 flex flex-col items-center justify-center text-center stagger-in">
    <span className="grid place-items-center w-10 h-10 rounded-xl mb-3 bg-[rgb(var(--danger)/0.1)] border border-[rgb(var(--danger)/0.25)] text-[rgb(var(--danger))]" aria-hidden="true">
      <AlertCircle className="w-5 h-5" />
    </span>
    <h3 className="typo-card-title">Could not load your planner</h3>
    <p className="typo-body-sm mt-1.5 max-w-sm">{message}</p>
    <button onClick={onRetry} className="btn-primary btn-sm mt-5 focus-ring">
      <Loader2 className="w-4 h-4" aria-hidden="true" /> Try again
    </button>
  </div>
)

// === EVENT FORM (create + edit) ===
interface EventFormProps {
  dateKey: string
  event: PlannerEvent | null
  tasks: Task[]
  habits: Habit[]
  submitting: boolean
  error: string | null
  onSubmit: (values: {
    title: string
    description: string
    startTime: string
    endTime: string
    eventType: PlannerEventType
    taskId: number | null
    habitId: number | null
  }) => void
  onCancel: () => void
}

const EventForm: React.FC<EventFormProps> = ({ dateKey, event, tasks, habits, submitting, error, onSubmit, onCancel }) => {
  const [title, setTitle] = useState(event?.title || '')
  const [description, setDescription] = useState(event?.description || '')
  const [eventType, setEventType] = useState<PlannerEventType>(event?.event_type || 'task')
  const [startTime, setStartTime] = useState(event ? formatTimeOnly(event.start_time) : '09:00')
  const [endTime, setEndTime] = useState(event ? formatTimeOnly(event.end_time) : '10:00')
  const [taskId, setTaskId] = useState<string>(event?.task_id ? String(event.task_id) : '')
  const [habitId, setHabitId] = useState<string>(event?.habit_id ? String(event.habit_id) : '')

  const timeConflict = endTime <= startTime

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!title.trim() || timeConflict) return
    onSubmit({
      title: title.trim(),
      description: description.trim(),
      startTime,
      endTime,
      eventType,
      taskId: taskId ? Number(taskId) : null,
      habitId: habitId ? Number(habitId) : null,
    })
  }

  return (
    <form onSubmit={handleSubmit} className="card-input p-5 space-y-4 stagger-in" style={{ animationDelay: '120ms' }}>
      <p className="typo-label">{event ? 'Edit event' : `Add event · ${formatLongDate(dateKey)}`}</p>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <div className="relative md:col-span-2">
          <input
            value={title}
            onChange={e => setTitle(e.target.value)}
            placeholder="Event title…"
            aria-label="Event title"
            required
            className="input input-icon-left"
          />
          <Calendar className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[rgb(var(--text-tertiary))] pointer-events-none" aria-hidden="true" />
        </div>

        <div className="relative">
          <select
            value={eventType}
            onChange={e => setEventType(e.target.value as PlannerEventType)}
            aria-label="Event type"
            className="input input-icon-left"
          >
            {EVENT_TYPES.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
          </select>
          <Flag className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[rgb(var(--text-tertiary))] pointer-events-none" aria-hidden="true" />
        </div>

        <div className="relative">
          <select
            value={eventType === 'habit' ? (habitId || '') : (taskId || '')}
            onChange={e => {
              const value = e.target.value
              if (eventType === 'habit') { setHabitId(value); setTaskId('') }
              else { setTaskId(value); setHabitId('') }
            }}
            aria-label={eventType === 'habit' ? 'Linked habit' : 'Linked task'}
            className="input input-icon-left"
          >
            <option value="">
              {eventType === 'habit' ? 'Link habit (optional)' : eventType === 'task' ? 'Link task (optional)' : 'Not linked'}
            </option>
            {(eventType === 'habit'
              ? habits.map(h => ({ id: h.id, title: h.title }))
              : tasks.map(t => ({ id: t.id, title: t.title }))
            ).map(o => <option key={o.id} value={o.id}>{o.title}</option>)}
          </select>
          <Activity className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[rgb(var(--text-tertiary))] pointer-events-none" aria-hidden="true" />
        </div>

        <div className="relative">
          <input
            type="time"
            value={startTime}
            onChange={e => setStartTime(e.target.value)}
            aria-label="Start time"
            required
            className="input input-icon-left"
          />
          <Clock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[rgb(var(--text-tertiary))] pointer-events-none" aria-hidden="true" />
        </div>

        <div className="relative">
          <input
            type="time"
            value={endTime}
            onChange={e => setEndTime(e.target.value)}
            aria-label="End time"
            required
            className="input input-icon-left"
          />
          <Clock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[rgb(var(--text-tertiary))] pointer-events-none" aria-hidden="true" />
        </div>
      </div>

      <div className="relative z-10">
        <textarea
          value={description}
          onChange={e => setDescription(e.target.value)}
          rows={2}
          placeholder="Description (optional)…"
          aria-label="Description"
          className="input pl-4"
        />
      </div>

      {timeConflict && (
        <p role="alert" className="text-[13px] text-[rgb(var(--warning))]">
          End time must be after start time.
        </p>
      )}
      {error && (
        <p role="alert" className="text-[13px] text-[rgb(var(--danger))]">
          {error}
        </p>
      )}

      <div className="flex justify-end gap-2">
        <button type="button" onClick={onCancel} className="btn-secondary focus-ring">
          Cancel
        </button>
        <button
          type="submit"
          disabled={submitting || timeConflict || !title.trim()}
          className="btn-primary focus-ring disabled:opacity-50"
        >
          {submitting ? <Loader2 className="w-4 h-4 animate-spin" aria-hidden="true" /> : <Plus className="w-4 h-4" aria-hidden="true" />}
          {event ? 'Save changes' : 'Add event'}
        </button>
      </div>
    </form>
  )
}

// === MAIN COMPONENT ===
export const PlannerView: React.FC = () => {
  const [dateKey, setDateKey] = useState(() => toLocalDateKey(new Date()))
  const [events, setEvents] = useState<PlannerEvent[]>([])
  const [tasks, setTasks] = useState<Task[]>([])
  const [habits, setHabits] = useState<Habit[]>([])
  const [goals, setGoals] = useState<Goal[]>([])

  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [busyId, setBusyId] = useState<number | null>(null)

  const [filterType, setFilterType] = useState<PlannerEventType | ''>('')
  const [showForm, setShowForm] = useState(false)
  const [editingEvent, setEditingEvent] = useState<PlannerEvent | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setLoadError(null)
    try {
      const data = await plannerService.getEvents({
        startDate: `${dateKey}T00:00:00`,
        endDate: `${dateKey}T23:59:59`,
        eventType: filterType || null,
      })
      setEvents(data)
    } catch (e) {
      setEvents([])
      setLoadError(extractErrorMessage(e, 'Failed to load planner events.'))
    } finally {
      setLoading(false)
    }
  }, [dateKey, filterType])

  // Events for the selected day. Sidebar data (tasks/habits/goals) is loaded
  // once and reused across day and filter changes.
  useEffect(() => { load() }, [load])

  useEffect(() => {
    let active = true
    const loadContext = async () => {
      try {
        const [taskRes, habitRes, goalRes] = await Promise.all([
          taskService.getTasks().catch(() => []),
          habitService.getHabits().catch(() => []),
          goalService.getGoals().catch(() => []),
        ])
        if (!active) return
        setTasks(Array.isArray(taskRes) ? taskRes : [])
        setHabits(Array.isArray(habitRes) ? habitRes : [])
        setGoals(Array.isArray(goalRes) ? goalRes : [])
      } catch {
        // Context lists are optional; the timeline still works without them.
      }
    }
    loadContext()
    return () => { active = false }
  }, [])

  const sortedEvents = useMemo(() => {
    return [...events].sort((a, b) => a.start_time.localeCompare(b.start_time))
  }, [events])

  const summary = useMemo(() => {
    const completed = sortedEvents.filter(e => e.is_completed).length
    return {
      total: sortedEvents.length,
      completed,
      pending: sortedEvents.length - completed,
      openTasks: tasks.filter(t => t.status !== 'completed').length,
      activeGoals: goals.filter(g => !g.is_completed).length,
    }
  }, [sortedEvents, tasks, goals])

  const closeForm = () => {
    setShowForm(false)
    setEditingEvent(null)
    setFormError(null)
  }

  const handleSubmit = async (values: {
    title: string
    description: string
    startTime: string
    endTime: string
    eventType: PlannerEventType
    taskId: number | null
    habitId: number | null
  }) => {
    setSubmitting(true)
    setFormError(null)
    try {
      const payload = {
        title: values.title,
        description: values.description || null,
        event_type: values.eventType,
        task_id: values.taskId,
        habit_id: values.habitId,
      }

      if (editingEvent) {
        await plannerService.updateEvent(editingEvent.id, {
          ...payload,
          event_date: toNaiveIso(dateKeyOfNaive(editingEvent.event_date), '00:00:00'),
          start_time: toNaiveIso(dateKeyOfNaive(editingEvent.event_date), values.startTime),
          end_time: toNaiveIso(dateKeyOfNaive(editingEvent.event_date), values.endTime),
        })
      } else {
        await plannerService.createEvent({
          ...payload,
          event_date: toNaiveIso(dateKey, '00:00:00'),
          start_time: toNaiveIso(dateKey, values.startTime),
          end_time: toNaiveIso(dateKey, values.endTime),
        })
      }

      closeForm()
      await load()
    } catch (e) {
      setFormError(extractErrorMessage(e, 'Could not save the event.'))
    } finally {
      setSubmitting(false)
    }
  }

  const toggleComplete = async (event: PlannerEvent) => {
    setBusyId(event.id)
    try {
      await plannerService.updateEvent(event.id, { is_completed: !event.is_completed })
      await load()
    } catch (e) {
      setLoadError(extractErrorMessage(e, 'Could not update the event.'))
    } finally {
      setBusyId(null)
    }
  }

  const handleDelete = async (event: PlannerEvent) => {
    setBusyId(event.id)
    try {
      await plannerService.deleteEvent(event.id)
      if (editingEvent?.id === event.id) closeForm()
      await load()
    } catch (e) {
      setLoadError(extractErrorMessage(e, 'Could not delete the event.'))
    } finally {
      setBusyId(null)
    }
  }

  return (
    <div className="relative space-y-6 animate-fadeInUp">
      {/* === HERO HEADER ===
          The old header was the single most expensive animation surface in the
          app: three `blur-3xl` orbs on infinite floats, a fourth hero orb, a
          `coreBreathe` glow on the 48px calendar tile, and a gradient hairline.
          None of it changed or conveyed information. A single static radial wash
          and a `section-header` now carry the same orientation. */}
      <div className="stagger-in relative">
        <div className="card-hero p-6 md:p-7 relative overflow-hidden">
          <div
            className="absolute inset-0 pointer-events-none"
            style={{
              background:
                'radial-gradient(ellipse 60% 140% at 100% 0%, rgb(var(--accent) / 0.07) 0%, transparent 60%)',
            }}
          />

          <div className="relative z-10 flex flex-col lg:flex-row lg:items-end justify-between gap-4">
            <div className="relative z-10">
              <p className="section-header-label !m-0 !p-0">
                <Calendar className="w-3.5 h-3.5 !text-[rgb(var(--accent))]" aria-hidden="true" />
                Schedule
              </p>
              <h1 className="typo-h1 mt-2">Your schedule</h1>
              <p className="typo-meta mt-1.5 max-w-[60ch]">
                Persistent time blocks for tasks, habits, focus sessions, and anything custom.
                Stored in your account.
              </p>
            </div>
            <div className="flex items-center gap-3 shrink-0">
              <span className="hidden lg:block typo-body-sm text-[rgb(var(--text-secondary))]">{formatLongDate(dateKey)}</span>
              <span className="btn-icon !w-10 !h-10 !rounded-xl bg-[rgb(var(--accent))] text-[rgb(var(--text-inverse))] shrink-0">
                <Calendar className="w-5 h-5" aria-hidden="true" />
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* === DAY NAVIGATION + FILTERS === */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 stagger-in" style={{ animationDelay: '40ms' }}>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setDateKey(k => shiftDateKey(k, -1))}
            aria-label="Previous day"
            className="btn-icon focus-ring hover:!text-[rgb(var(--text-primary))]"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>
          <span className="typo-body-sm text-[rgb(var(--text-secondary))] min-w-[160px] text-center">{formatLongDate(dateKey)}</span>
          <button
            onClick={() => setDateKey(k => shiftDateKey(k, 1))}
            aria-label="Next day"
            className="btn-icon focus-ring hover:!text-[rgb(var(--text-primary))]"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
          <button
            onClick={() => setDateKey(toLocalDateKey(new Date()))}
            className="btn-ghost btn-sm !text-[rgb(var(--text-secondary))] hover:!text-[rgb(var(--accent))] focus-ring"
          >
            Today
          </button>
        </div>

        <div
          role="group"
          aria-label="Filter by event type"
          className="flex items-center gap-1 p-1 rounded-xl bg-[rgb(var(--surface-3))] border border-[rgb(var(--border-subtle))] w-fit overflow-x-auto"
        >
          <button
            onClick={() => setFilterType('')}
            aria-pressed={filterType === ''}
            className={`h-9 px-3.5 rounded-lg text-xs font-mono whitespace-nowrap transition-colors duration-200 focus-ring ${
              filterType === ''
                ? 'bg-[rgb(var(--surface-4))] text-[rgb(var(--accent))] shadow-[var(--depth-1)]'
                : 'text-[rgb(var(--text-tertiary))] hover:text-[rgb(var(--text-primary))]'
            }`}
          >
            All
          </button>
          {EVENT_TYPES.map(t => (
            <button
              key={t.value}
              onClick={() => setFilterType(filterType === t.value ? '' : t.value)}
              aria-pressed={filterType === t.value}
              className={`h-9 px-3.5 rounded-lg text-xs font-mono whitespace-nowrap transition-colors duration-200 focus-ring ${
                filterType === t.value
                  ? 'bg-[rgb(var(--surface-4))] text-[rgb(var(--accent))] shadow-[var(--depth-1)]'
                  : 'text-[rgb(var(--text-tertiary))] hover:text-[rgb(var(--text-primary))]'
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>

      {/* === DAILY SUMMARY === */}
      <div className="stagger-in" style={{ animationDelay: '80ms' }}>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <StatBlock label="Open Tasks" value={summary.openTasks} icon={CheckCircle2} index={0} />
          <StatBlock label="Active Goals" value={summary.activeGoals} icon={Target} index={1} />
          <StatBlock label="Events Today" value={summary.total} icon={TrendingUp} index={2} />
          <StatBlock label="Completed" value={summary.completed} icon={CheckCircle2} index={3} />
        </div>
      </div>

      {/* === CREATE / EDIT FORM === */}
      {(showForm || editingEvent) && (
        <EventForm
          key={editingEvent ? `edit-${editingEvent.id}` : `new-${dateKey}`}
          dateKey={dateKey}
          event={editingEvent}
          tasks={tasks}
          habits={habits}
          submitting={submitting}
          error={formError}
          onSubmit={handleSubmit}
          onCancel={closeForm}
        />
      )}

      {/* === MAIN CONTENT GRID === */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* === TIMELINE (LEFT 2/3) === */}
        <div className="lg:col-span-2 space-y-6">
          <div className="stagger-in" style={{ animationDelay: '160ms' }}>
            <section aria-label="Timeline" className="card-secondary p-5">
              <div className="section-header">
                <div className="min-w-0">
                  <p className="section-header-label">
                    <Clock className="w-3.5 h-3.5 !text-[rgb(var(--accent))]" aria-hidden="true" />
                    Timeline
                  </p>
                  <h2 className="section-header-title mt-2">Today's events</h2>
                </div>
                <button
                  onClick={() => { setEditingEvent(null); setShowForm(v => !v); setFormError(null) }}
                  aria-expanded={showForm}
                  className="btn-primary btn-sm focus-ring"
                >
                  <Plus className="w-4 h-4" aria-hidden="true" /> Add event
                </button>
              </div>

              {loading ? (
                <PlannerSkeleton />
              ) : loadError && sortedEvents.length === 0 ? (
                <ErrorState message={loadError} onRetry={load} />
              ) : sortedEvents.length === 0 ? (
                <EmptyPlanState onCreate={() => { setEditingEvent(null); setShowForm(true) }} />
              ) : (
                <div className="row-stack mt-4">
                  {loadError && (
                    <div role="alert" className="typo-body-sm text-[rgb(var(--danger))] flex items-center gap-2 px-1">
                      <AlertCircle className="w-4 h-4 shrink-0" aria-hidden="true" /> {loadError}
                    </div>
                  )}
                  {sortedEvents.map((event, i) => (
                    <PlanEntry
                      key={event.id}
                      event={event}
                      index={i}
                      busyId={busyId}
                      onToggleComplete={toggleComplete}
                      onEdit={(e) => { setShowForm(false); setEditingEvent(e); setFormError(null) }}
                      onDelete={handleDelete}
                    />
                  ))}
                </div>
              )}
            </section>
          </div>
        </div>

        {/* === ACTIVE GOALS + HABITS (RIGHT 1/3) === */}
        <div className="space-y-5">
          <section aria-label="Active goals" className="card-secondary p-5 stagger-in" style={{ animationDelay: '240ms' }}>
            <div className="section-header">
              <div className="min-w-0">
                <p className="section-header-label">
                  <Target className="w-3.5 h-3.5 !text-[rgb(var(--accent-secondary))]" aria-hidden="true" />
                  Objectives
                </p>
                <h2 className="section-header-title mt-2">Active goals</h2>
              </div>
            </div>

            {goals.length === 0 ? (
              <div className="text-center py-6">
                <Target className="w-8 h-8 text-[rgb(var(--text-muted))] mx-auto mb-2" aria-hidden="true" />
                <p className="typo-body-sm">No goals yet. Create goals to give your schedule direction.</p>
              </div>
            ) : (
              <div className="row-stack mt-2">
                {goals.filter(g => !g.is_completed).map((goal, i) => (
                  <GoalCard key={goal.id} goal={goal} index={i} />
                ))}
              </div>
            )}
          </section>

          {/* Habits context */}
          <section aria-label="Active habits" className="card-secondary p-5 stagger-in" style={{ animationDelay: '320ms' }}>
            <div className="section-header">
              <div className="min-w-0">
                <p className="section-header-label">
                  <Activity className="w-3.5 h-3.5 !text-[rgb(var(--accent))]" aria-hidden="true" />
                  Routines
                </p>
                <h2 className="section-header-title mt-2">Active habits</h2>
              </div>
            </div>

            {habits.length === 0 ? (
              <p className="typo-body-sm">No habits configured.</p>
            ) : (
              <div className="row-stack mt-2">
                {habits.map(habit => (
                  <div key={habit.id} className="row-item !p-3 !items-center !gap-3">
                    <span className="typo-body-sm !font-medium !text-[rgb(var(--text-primary))] truncate flex-1">
                      {habit.title}
                    </span>
                    <span className="typo-micro shrink-0 text-[9px] !normal-case !tracking-normal text-[rgb(var(--accent))]">
                      {habit.current_streak} day streak
                    </span>
                  </div>
                ))}
              </div>
            )}
          </section>
        </div>
      </div>
    </div>
  )
}