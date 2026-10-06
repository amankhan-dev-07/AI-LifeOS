import React, { useEffect, useMemo, useState } from 'react'
import { createPortal } from 'react-dom'
import { Bell, BellOff, Check, Loader2, AlertCircle, Trash2, X, Clock, Pencil } from 'lucide-react'
import { useReminders } from '../context/RemindersContext'
import { usePreferences } from '../context/PreferencesContext'
import { extractErrorMessage } from '../utils/apiError'
import {
  defaultLocalInputValue,
  formatLocalDateTime,
  formatUntil,
  localInputToNaiveUtc,
  naiveUtcToLocalInput,
} from '../utils/datetime'
import type { Reminder, ReminderStatus } from '../types'

/**
 * The entity a reminder is being attached to. This is deliberately a closed
 * union of direct references — never a generic `entity_type`/`entity_id`
 * pair, which would let a reminder point at something it cannot validate.
 */
type LinkTarget =
  | { kind: 'task'; id: number; label: string }
  | { kind: 'planner_event'; id: number; label: string }
  | null

interface ReminderModalProps {
  open: boolean
  onClose: () => void
  /** Pre-fills the form when opened from a task or planner event. */
  target?: LinkTarget
}

/**
 * Semantic status tints. Previously hard-coded Tailwind hues, which meant the
 * reminder rows were the one surface in the app that stayed dark-only. Tokens
 * are space-separated RGB channels, so the tint is applied as an inline style —
 * Tailwind's `/20` opacity modifier cannot wrap a `rgb(var(--token))` value.
 */
const statusTint = (token: string): React.CSSProperties => ({
  color: `rgb(var(${token}))`,
  backgroundColor: `rgb(var(${token}) / 0.1)`,
  borderColor: `rgb(var(${token}) / 0.28)`,
})

const STATUS_TINT: Record<ReminderStatus, React.CSSProperties> = {
  pending: statusTint('--accent-tertiary'),
  completed: statusTint('--success'),
  cancelled: {
    color: 'rgb(var(--text-tertiary))',
    backgroundColor: 'rgb(var(--surface))',
    borderColor: 'rgb(var(--border))',
  },
}

/**
 * The single reminder surface: create, edit, complete, cancel and delete.
 *
 * It is opened as an overlay from the header bell's "Reminders" entry and from
 * the per-task / per-event "Remind me" buttons, so the same form and list back
 * every entry point rather than each view owning its own logic.
 */
export const ReminderModal: React.FC<ReminderModalProps> = ({ open, onClose, target }) => {
  const { reminders, loading, error, createReminder, updateReminder, deleteReminder, reload } = useReminders()
  // The one zone and 12/24h choice every reminder timestamp is converted with,
  // so the value in the input, the value stored and the value shown can never
  // disagree about which wall clock the user meant.
  const { timezone, timeFormat } = usePreferences()

  const [title, setTitle] = useState('')
  const [message, setMessage] = useState('')
  const [remindAt, setRemindAt] = useState(() => defaultLocalInputValue(60, timezone))
  // Editing is per-row state, not a modal-wide mode, so the list stays
  // browsable while a reminder is being edited.
  const [editing, setEditing] = useState<Reminder | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)
  const [busyId, setBusyId] = useState<number | null>(null)
  const [filter, setFilter] = useState<'all' | 'pending' | 'completed'>('pending')

  // Reset the form whenever the modal opens, seeded from the context the user
  // opened it from.
  useEffect(() => {
    if (!open) return

    setEditing(null)
    setFormError(null)
    setTitle(target ? `Reminder: ${target.label}` : '')
    setMessage('')
    setRemindAt(defaultLocalInputValue(target ? 30 : 60, timezone))
  }, [open, target, timezone])

  // Load the row being edited into the form.
  useEffect(() => {
    if (!editing) return

    setTitle(editing.title)
    setMessage(editing.message ?? '')
    setRemindAt(naiveUtcToLocalInput(editing.remind_at, timezone) || defaultLocalInputValue(60, timezone))
  }, [editing, timezone])

  // Escape closes the overlay, matching the other modal surfaces in the app.
  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [open, onClose])

  const filtered = useMemo(
    () =>
      [...reminders]
        .filter((r) => (filter === 'all' ? true : r.status === filter))
        .sort((a, b) => a.remind_at.localeCompare(b.remind_at) || a.id - b.id),
    [reminders, filter],
  )

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!title.trim() || !remindAt) return

    setSubmitting(true)
    setFormError(null)
    try {
      const payload = {
        title: title.trim(),
        message: message.trim() || null,
        // `datetime-local` gives wall-clock time with no offset, in the user's
        // zone. This is the ONLY conversion local -> UTC: it happens here, and
        // the backend stores the result verbatim.
        remind_at: localInputToNaiveUtc(remindAt, timezone),
      }

      if (editing) {
        await updateReminder(editing.id, payload)
      } else {
        await createReminder({
          ...payload,
          task_id: target?.kind === 'task' ? target.id : null,
          planner_event_id: target?.kind === 'planner_event' ? target.id : null,
        })
      }

      // Success only after the backend confirms the write; the form then
      // returns to create-mode so a second reminder can be scheduled without
      // reopening the modal.
      setEditing(null)
      setTitle('')
      setMessage('')
      setRemindAt(defaultLocalInputValue(60, timezone))
      // The list is re-read so a reminder created from another surface (Tasks,
      // Planner) appears here without this component knowing about it.
      await reload()
    } catch (err) {
      setFormError(extractErrorMessage(err, 'Could not save the reminder.'))
    } finally {
      setSubmitting(false)
    }
  }

  const act = async (reminder: Reminder, action: 'complete' | 'cancel' | 'delete') => {
    setBusyId(reminder.id)
    setFormError(null)
    try {
      if (action === 'delete') {
        await deleteReminder(reminder.id)
      } else if (action === 'complete') {
        await updateReminder(reminder.id, { is_completed: true, is_cancelled: false })
      } else {
        await updateReminder(reminder.id, { is_completed: false, is_cancelled: true })
      }
    } catch (err) {
      setFormError(extractErrorMessage(err, 'Could not update the reminder.'))
    } finally {
      setBusyId(null)
    }
  }

  if (!open) return null

  // Portalled to <body> on purpose. In TasksView and PlannerView the trigger
  // sits inside a card row, and any transformed/3D ancestor — the old
  // `.card-25d` class carried `transform-style: preserve-3d` — becomes the
  // containing block for `position: fixed` descendants and clips them to its
  // bounds, so a `fixed inset-0` overlay rendered in place only ever painted
  // inside the task card. Rendering at the document root removes every
  // ancestor from that chain — including the scroll container — so the
  // overlay is positioned against the real viewport. The portal stays even
  // though the 3D card class is gone: a scroll container ancestor would
  // reintroduce the same clipping.
  return createPortal(
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Reminders"
      className="fixed inset-0 z-[100] flex items-start justify-center p-4 sm:pt-[8vh] overflow-y-auto overscroll-contain"
    >
      <button aria-label="Close reminders" onClick={onClose} className="modal-backdrop fixed inset-0" />

      {/* `my-auto` centers the panel within the overlay's scroll area, and
          `max-h` caps it to the usable viewport height, so the whole dialog is
          reachable on both short desktop windows and small screens. */}
      <div className="relative w-full max-w-2xl modal-content p-6 animate-scaleInBounce my-auto max-h-[80vh] sm:max-h-[84vh] flex flex-col">
        <div className="absolute top-0 left-0 right-0 h-px bg-[rgb(var(--accent)/0.35)] pointer-events-none rounded-t-2xl" />

        {/* === HEADER === */}
        <div className="relative z-10 flex items-start justify-between gap-3 mb-5 shrink-0">
          <div className="flex items-center gap-3 min-w-0">
            <span className="w-10 h-10 rounded-xl bg-[rgb(var(--accent-tertiary)/0.1)] border border-[rgb(var(--accent-tertiary)/0.28)] grid place-items-center text-[rgb(var(--accent-tertiary))] shrink-0">
              <Bell className="w-5 h-5" />
            </span>
            <div className="min-w-0">
              <h2 className="font-display font-semibold text-base text-[rgb(var(--text-primary))]">
                {editing ? 'Edit reminder' : target ? 'Set a reminder' : 'Reminders'}
              </h2>
              {target && !editing && (
                <p className="text-xs font-mono text-[rgb(var(--text-tertiary))] truncate">Linked to {target.label}</p>
              )}
            </div>
          </div>
          <button
            onClick={onClose}
            aria-label="Close reminders"
            className="shrink-0 w-10 h-10 grid place-items-center rounded-lg bg-[rgb(var(--surface))] border border-[rgb(var(--border))] text-[rgb(var(--text-muted))] hover:text-[rgb(var(--text-primary))] transition-colors focus-ring"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* === FORM === */}
        <form onSubmit={handleSubmit} className="relative z-10 shrink-0 space-y-3 pb-5 border-b border-[rgb(var(--border))]">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div className="relative sm:col-span-2">
              <input
                value={title}
                onChange={e => setTitle(e.target.value)}
                placeholder="Reminder title…"
                aria-label="Reminder title"
                required
                maxLength={200}
                className="input input-icon-left w-full pr-4 py-2.5 text-sm"
              />
              <Bell className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[rgb(var(--text-muted))]" />
            </div>

            <div className="relative">
              <input
                type="datetime-local"
                value={remindAt}
                onChange={e => setRemindAt(e.target.value)}
                required
                aria-label="Reminder time"
                className="input input-icon-left w-full pr-3 py-2.5 text-sm font-mono"
              />
              <Clock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[rgb(var(--text-muted))]" />
            </div>

            <input
              value={message}
              onChange={e => setMessage(e.target.value)}
              placeholder="Message (optional)…"
              aria-label="Reminder message (optional)"
              className="input w-full px-4 py-2.5 text-sm"
            />
          </div>

          {formError && (
            <p role="alert" className="text-xs font-mono text-[rgb(var(--danger))] flex items-center gap-1.5">
              <AlertCircle className="w-3.5 h-3.5" /> {formError}
            </p>
          )}

          <div className="flex justify-end gap-2">
            {editing && (
              <button
                type="button"
                onClick={() => {
                  setEditing(null)
                  setTitle('')
                  setMessage('')
                  setRemindAt(defaultLocalInputValue(60, timezone))
                }}
                className="btn-secondary h-10 px-4 text-sm"
              >
                Reset
              </button>
            )}
            <button
              type="submit"
              disabled={submitting || !title.trim()}
              className="btn-primary h-10 px-5 inline-flex items-center gap-2 text-sm"
            >
              {submitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Check className="w-4 h-4" />}
              {editing ? 'Save changes' : 'Schedule'}
            </button>
          </div>
        </form>

        {/* === LIST === */}
        <div className="relative z-10 flex-1 min-h-0 min-w-0 flex flex-col pt-4">
          <div className="flex items-center justify-between gap-2 mb-3">
            <div role="tablist" aria-label="Filter reminders" className="inline-flex p-1 rounded-lg bg-[rgb(var(--surface-2))] border border-[rgb(var(--border))]">
              {(['pending', 'completed', 'all'] as const).map((f) => (
                <button
                  key={f}
                  role="tab"
                  aria-selected={filter === f}
                  onClick={() => setFilter(f)}
                  className={`h-8 px-3 rounded-md text-[11px] font-mono capitalize transition-colors duration-200 focus-ring ${
                    filter === f
                      ? 'bg-[rgb(var(--surface-4))] text-[rgb(var(--text-primary))] shadow-[var(--depth-1)]'
                      : 'text-[rgb(var(--text-tertiary))] hover:text-[rgb(var(--text-primary))]'
                  }`}
                >
                  {f}
                </button>
              ))}
            </div>
            <button
              onClick={reload}
              aria-label="Refresh reminders"
              className="btn-ghost btn-sm h-8 focus-ring"
            >
              Refresh
            </button>
          </div>

          <div className="flex-1 min-h-0 overflow-y-auto scroll-y">
            {loading && reminders.length === 0 ? (
              <div className="py-10 flex flex-col items-center gap-2">
                <Loader2 className="w-5 h-5 animate-spin text-[rgb(var(--accent))]" />
                <span className="text-xs font-mono text-[rgb(var(--text-tertiary))]">Loading…</span>
              </div>
            ) : error && reminders.length === 0 ? (
              <div className="py-10 flex flex-col items-center gap-2 text-center px-4" role="alert">
                <AlertCircle className="w-6 h-6 text-[rgb(var(--danger))]" />
                <span className="text-xs text-[rgb(var(--danger))]">{error}</span>
                <button onClick={reload} className="text-xs font-mono text-accent text-accent-hover focus-ring rounded">
                  Try again
                </button>
              </div>
            ) : filtered.length === 0 ? (
              <div className="py-10 flex flex-col items-center gap-2 text-center px-4">
                <BellOff className="w-6 h-6 text-[rgb(var(--text-muted))]" />
                <span className="text-xs text-[rgb(var(--text-tertiary))]">
                  {filter === 'completed'
                    ? 'No completed reminders yet.'
                    : 'No reminders scheduled yet — add one with the form above.'}
                </span>
              </div>
            ) : (
              <ul className="space-y-2">
                {filtered.map((reminder) => {
                  const isBusy = busyId === reminder.id
                  const isPending = reminder.status === 'pending'
                  // Editing is a per-row action rather than a modal-level mode:
                  // the list stays browsable while a reminder is being edited.
                  const isEditing = editing?.id === reminder.id

                  return (
                    <li
                      key={reminder.id}
                      className="flex items-start gap-3 p-3 rounded-xl bg-[rgb(var(--surface))] border transition-colors"
                      style={isEditing ? {
                        borderColor: 'rgb(var(--accent) / 0.45)',
                        backgroundColor: 'rgb(var(--accent) / 0.06)',
                      } : { borderColor: 'rgb(var(--border))' }}
                    >
                      <div className="min-w-0 flex-1">
                        <p className={`text-sm font-medium leading-tight truncate ${isPending ? 'text-[rgb(var(--text-primary))]' : 'text-[rgb(var(--text-tertiary))] line-through'}`}>
                          {reminder.title}
                        </p>
                        {reminder.message && (
                          <p className="mt-1 text-xs text-[rgb(var(--text-secondary))] line-clamp-2">{reminder.message}</p>
                        )}
                        <div className="mt-1.5 flex flex-wrap items-center gap-1.5">
                          <span className="badge" style={STATUS_TINT[reminder.status]}>{reminder.status}</span>
                          <span className="inline-flex items-center gap-1 text-[10px] font-mono text-[rgb(var(--text-tertiary))]">
                            <Clock className="w-3 h-3" />
                            {formatLocalDateTime(reminder.remind_at, timeFormat, timezone)}
                            {isPending && <span className="text-accent">({formatUntil(reminder.remind_at)})</span>}
                          </span>
                          {reminder.task_id && (
                            <span
                              className="badge"
                              style={{
                                color: 'rgb(var(--accent-tertiary))',
                                backgroundColor: 'rgb(var(--accent-tertiary) / 0.1)',
                                borderColor: 'rgb(var(--accent-tertiary) / 0.28)',
                              }}
                            >
                              Task #{reminder.task_id}
                            </span>
                          )}
                          {reminder.planner_event_id && (
                            <span
                              className="badge"
                              style={{
                                color: 'rgb(var(--accent))',
                                backgroundColor: 'rgb(var(--accent) / 0.1)',
                                borderColor: 'rgb(var(--accent) / 0.28)',
                              }}
                            >
                              Event #{reminder.planner_event_id}
                            </span>
                          )}
                        </div>
                      </div>

                      <div className="flex items-center gap-1 shrink-0">
                        {isPending && (
                          <>
                            <button
                              onClick={() => act(reminder, 'complete')}
                              disabled={isBusy}
                              aria-label={`Mark "${reminder.title}" complete`}
                              title="Mark complete"
                              className="w-10 h-10 grid place-items-center rounded-lg bg-[rgb(var(--surface))] border border-[rgb(var(--border))] text-[rgb(var(--text-muted))] hover:text-[rgb(var(--success))] hover:border-[rgb(var(--success)/0.35)] transition-colors focus-ring disabled:opacity-50"
                            >
                              <Check className="w-4 h-4" />
                            </button>
                            <button
                              onClick={() => act(reminder, 'cancel')}
                              disabled={isBusy}
                              aria-label={`Cancel "${reminder.title}"`}
                              title="Cancel"
                              className="w-10 h-10 grid place-items-center rounded-lg bg-[rgb(var(--surface))] border border-[rgb(var(--border))] text-[rgb(var(--text-muted))] hover:text-[rgb(var(--warning))] hover:border-[rgb(var(--warning)/0.35)] transition-colors focus-ring disabled:opacity-50"
                            >
                              <BellOff className="w-4 h-4" />
                            </button>
                          </>
                        )}
                        <button
                          onClick={() => (isEditing ? setEditing(null) : setEditing(reminder))}
                          disabled={isBusy}
                          aria-label={isEditing ? `Stop editing "${reminder.title}"` : `Edit "${reminder.title}"`}
                          title={isEditing ? 'Cancel edit' : 'Edit'}
                          className="w-10 h-10 grid place-items-center rounded-lg border transition-colors focus-ring disabled:opacity-50"
                          style={isEditing ? {
                            backgroundColor: 'rgb(var(--accent) / 0.12)',
                            borderColor: 'rgb(var(--accent) / 0.35)',
                            color: 'rgb(var(--accent))',
                          } : {
                            backgroundColor: 'rgb(var(--surface))',
                            borderColor: 'rgb(var(--border))',
                            color: 'rgb(var(--text-muted))',
                          }}
                        >
                          <Pencil className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => act(reminder, 'delete')}
                          disabled={isBusy}
                          aria-label={`Delete "${reminder.title}"`}
                          title="Delete"
                          className="w-10 h-10 grid place-items-center rounded-lg bg-[rgb(var(--surface))] border border-[rgb(var(--border))] text-[rgb(var(--text-muted))] hover:text-[rgb(var(--danger))] hover:border-[rgb(var(--danger)/0.35)] hover:bg-[rgb(var(--danger)/0.08)] transition-colors focus-ring disabled:opacity-50"
                        >
                          {isBusy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Trash2 className="w-4 h-4" />}
                        </button>
                      </div>
                    </li>
                  )
                })}
              </ul>
            )}
          </div>
        </div>
      </div>
    </div>,
    document.body
  )
}