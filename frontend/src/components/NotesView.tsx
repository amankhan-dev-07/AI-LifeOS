import React, { useCallback, useEffect, useMemo, useState } from 'react'
import {
  BookOpen, Plus, Trash2, Search, Filter, Edit2, FileText, Tag, Loader2,
  AlertCircle, Pin, PinOff, Archive, ArchiveRestore, Clock, Sparkles, Check,
} from 'lucide-react'
import { goalService, noteService, taskService } from '../services/services'
import { extractErrorMessage } from '../utils/apiError'
import { runLegacyMigration, getLegacyMigrationSummary } from '../utils/legacyMigration'
import { useAuth } from '../context/AuthContext'
import type { Note } from '../types'

/**
 * Note card.
 *
 * Two changes beyond colour:
 *
 * 1. The card was a `<button>` containing four `<button>` elements — invalid
 *    HTML, and screen readers announce the nested controls unreliably. It is now
 *    a `<div>` card whose body is one button (select) with the action buttons
 *    as siblings, so each control has exactly one role and one label.
 *
 * 2. The entrance used a `setTimeout` + `setState` per card and an
 *    `animate-fadeInUp3D` keyframe (translateZ + rotateX, which forces a 3D
 *    layer). The stagger is now a pure-CSS `animation-delay`.
 */
interface NoteCardProps {
  note: Note
  isSelected: boolean
  onSelect: () => void
  onEdit: () => void
  onDelete: () => void
  onTogglePin: () => void
  onToggleArchive: () => void
  index: number
  busyId: number | null
}

const NoteCard: React.FC<NoteCardProps> = ({ note, isSelected, onSelect, onEdit, onDelete, onTogglePin, onToggleArchive, index, busyId }) => {
  const isBusy = busyId === note.id

  const formatDate = (iso: string) => {
    const date = new Date(iso)
    if (Number.isNaN(date.getTime())) return ''
    const diff = Date.now() - date.getTime()
    const days = Math.floor(diff / 86400000)
    if (days <= 0) return 'Today'
    if (days === 1) return 'Yesterday'
    if (days < 7) return `${days}d ago`
    return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })
  }

  return (
    <div
      className={`row-item !p-4 !gap-3 !items-start stagger-in-fast ${
        isSelected ? '!border-l-2 !border-l-[rgb(var(--accent))] !pl-[15px] !bg-[rgb(var(--surface-3))]' : ''
      } ${note.is_archived ? '!opacity-60' : ''}`}
      style={{ animationDelay: `${index * 40}ms` }}
    >
      <div className="flex items-start justify-between gap-2 min-w-0">
        <div className="flex-1 min-w-0">
          <p className="typo-micro mb-1.5">
            <span className="!normal-case !tracking-[0.06em] !font-normal text-[rgb(var(--accent-tertiary))]">{note.tag}</span>
            {note.is_pinned && (
              <>
                <span className="w-1 h-1 rounded-full bg-[rgb(var(--border-strong))] inline-block align-middle mx-1.5" aria-hidden="true" />
                <span className="!normal-case !tracking-[0.06em] !font-normal text-[rgb(var(--warning))]">Pinned</span>
              </>
            )}
            {note.is_archived && (
              <>
                <span className="w-1 h-1 rounded-full bg-[rgb(var(--border-strong))] inline-block align-middle mx-1.5" aria-hidden="true" />
                <span className="!normal-case !tracking-[0.06em] !font-normal text-[rgb(var(--text-tertiary))]">Archived</span>
              </>
            )}
          </p>
          <button
            onClick={onSelect}
            className="text-left focus-ring rounded w-full py-2"
          >
            <h3 className="typo-body !font-semibold !leading-tight !text-[rgb(var(--text-primary))] line-clamp-1 block">
              {note.title}
            </h3>
            <p className="typo-body-sm line-clamp-3 whitespace-pre-wrap">
              {note.content || <span className="text-[rgb(var(--text-muted))]">No content</span>}
            </p>
          </button>
        </div>

        <div className="flex items-center gap-1 shrink-0">
          <button
            onClick={onTogglePin}
            disabled={isBusy}
            aria-label={note.is_pinned ? `Unpin ${note.title}` : `Pin ${note.title}`}
            title={note.is_pinned ? 'Unpin' : 'Pin'}
            className="btn-icon !w-7 !h-7 focus-ring hover:!text-[rgb(var(--warning))] hover:!bg-[rgb(var(--warning)/0.1)] disabled:opacity-50"
          >
            {note.is_pinned ? <PinOff className="w-3.5 h-3.5" /> : <Pin className="w-3.5 h-3.5" />}
          </button>
          <button
            onClick={onToggleArchive}
            disabled={isBusy}
            aria-label={note.is_archived ? `Unarchive ${note.title}` : `Archive ${note.title}`}
            title={note.is_archived ? 'Unarchive' : 'Archive'}
            className="btn-icon !w-7 !h-7 focus-ring hover:!text-[rgb(var(--accent))] hover:!bg-[rgb(var(--accent)/0.1)] disabled:opacity-50"
          >
            {note.is_archived ? <ArchiveRestore className="w-3.5 h-3.5" /> : <Archive className="w-3.5 h-3.5" />}
          </button>
          <button
            onClick={onEdit}
            disabled={isBusy}
            aria-label={`Edit ${note.title}`}
            title="Edit note"
            className="btn-icon !w-7 !h-7 focus-ring hover:!text-[rgb(var(--accent))] hover:!bg-[rgb(var(--accent)/0.1)] disabled:opacity-50"
          >
            <Edit2 className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={onDelete}
            disabled={isBusy}
            aria-label={`Delete ${note.title}`}
            title="Delete note"
            className="btn-icon !w-7 !h-7 focus-ring hover:!text-[rgb(var(--danger))] hover:!bg-[rgb(var(--danger)/0.1)] disabled:opacity-50"
          >
            {isBusy ? <Loader2 className="w-3.5 h-3.5 animate-spin" aria-hidden="true" /> : <Trash2 className="w-3.5 h-3.5" />}
          </button>
        </div>
      </div>

      <div className="mt-auto pt-2 border-t border-[rgb(var(--border-subtle))]">
        <span className="typo-meta">
          <span className="w-1 h-1 rounded-full bg-[rgb(var(--text-muted))] inline-block align-middle mr-1.5" aria-hidden="true" />
          Updated {formatDate(note.updated_at)}
        </span>
      </div>
    </div>
  )
}

// === NOTE EDITOR ===
interface NoteEditorProps {
  note: Note | null
  goals: { id: number; title: string }[]
  tasks: { id: number; title: string }[]
  submitting: boolean
  error: string | null
  onSave: (values: { title: string; content: string; tag: string; goalId: number | null; taskId: number | null }) => void
  onCancel: () => void
  isNew: boolean
}

const NoteEditor: React.FC<NoteEditorProps> = ({ note, goals, tasks, submitting, error, onSave, onCancel, isNew }) => {
  const [title, setTitle] = useState(note?.title || '')
  const [content, setContent] = useState(note?.content || '')
  const [tag, setTag] = useState(note?.tag || 'General')
  const [goalId, setGoalId] = useState(note?.goal_id ? String(note.goal_id) : '')
  const [taskId, setTaskId] = useState(note?.task_id ? String(note.task_id) : '')

  useEffect(() => {
    setTitle(note?.title || '')
    setContent(note?.content || '')
    setTag(note?.tag || 'General')
    setGoalId(note?.goal_id ? String(note.goal_id) : '')
    setTaskId(note?.task_id ? String(note.task_id) : '')
  }, [note])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!title.trim()) return
    onSave({
      title: title.trim(),
      content: content.trim(),
      tag: tag.trim() || 'General',
      goalId: goalId ? Number(goalId) : null,
      taskId: taskId ? Number(taskId) : null,
    })
  }

  return (
    <form onSubmit={handleSubmit} className="card-input p-5 space-y-4 stagger-in">
      <p className="typo-label">{isNew ? 'New note' : 'Edit note'}</p>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <div className="relative">
          <input
            value={title}
            onChange={e => setTitle(e.target.value)}
            placeholder="Note title…"
            aria-label="Note title"
            required
            className="input input-icon-left"
          />
          <FileText className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[rgb(var(--text-tertiary))] pointer-events-none" aria-hidden="true" />
        </div>
        <div className="relative">
          <input
            value={tag}
            onChange={e => setTag(e.target.value)}
            placeholder="Tag (e.g. Ideas, Engineering)"
            aria-label="Tag"
            className="input input-icon-left"
          />
          <Tag className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[rgb(var(--text-tertiary))] pointer-events-none" aria-hidden="true" />
        </div>
        <div className="relative">
          <select
            value={goalId}
            onChange={e => setGoalId(e.target.value)}
            aria-label="Linked goal"
            className="input input-icon-left"
          >
            <option value="">No linked goal</option>
            {goals.map(g => <option key={g.id} value={g.id}>{g.title}</option>)}
          </select>
          <Sparkles className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[rgb(var(--text-tertiary))] pointer-events-none" aria-hidden="true" />
        </div>
        <div className="relative">
          <select
            value={taskId}
            onChange={e => setTaskId(e.target.value)}
            aria-label="Linked task"
            className="input input-icon-left"
          >
            <option value="">No linked task</option>
            {tasks.map(t => <option key={t.id} value={t.id}>{t.title}</option>)}
          </select>
          <FileText className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[rgb(var(--text-tertiary))] pointer-events-none" aria-hidden="true" />
        </div>
      </div>

      <div className="relative z-10">
        <textarea
          value={content}
          onChange={e => setContent(e.target.value)}
          rows={6}
          placeholder="Note content…"
          aria-label="Note content"
          className="input pl-4"
        />
      </div>

      {error && (
        <p role="alert" className="text-[13px] text-[rgb(var(--danger))] flex items-center gap-1.5">
          <AlertCircle className="w-3.5 h-3.5 shrink-0" aria-hidden="true" /> {error}
        </p>
      )}

      <div className="flex justify-end gap-2">
        <button type="button" onClick={onCancel} className="btn-secondary focus-ring">
          Cancel
        </button>
        <button
          type="submit"
          disabled={submitting || !title.trim()}
          className="btn-primary focus-ring disabled:opacity-50"
        >
          {submitting ? <Loader2 className="w-4 h-4 animate-spin" aria-hidden="true" /> : <Plus className="w-4 h-4" aria-hidden="true" />}
          {isNew ? 'Save note' : 'Update note'}
        </button>
      </div>
    </form>
  )
}

// === SEARCH / FILTER BAR ===
interface SearchFilterProps {
  search: string
  setSearch: (v: string) => void
  filterTag: string
  setFilterTag: (v: string) => void
  allTags: string[]
  noteCount: number
  filteredCount: number
  showArchived: boolean
  setShowArchived: (v: boolean) => void
}

const SearchFilter: React.FC<SearchFilterProps> = ({
  search, setSearch, filterTag, setFilterTag, allTags, noteCount, filteredCount, showArchived, setShowArchived
}) => (
  <section aria-label="Search and filter" className="card-secondary p-5 stagger-in" style={{ animationDelay: '80ms' }}>
    <p className="typo-label mb-3">Find notes</p>

    <div className="relative mb-3">
      <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[rgb(var(--text-tertiary))] pointer-events-none" aria-hidden="true" />
      <input
        value={search}
        onChange={e => setSearch(e.target.value)}
        placeholder="Search notes…"
        aria-label="Search notes"
        className="input input-icon-left"
      />
    </div>

    <div className="flex flex-wrap items-center gap-2">
      <Filter className="w-4 h-4 text-[rgb(var(--text-tertiary))] shrink-0" aria-hidden="true" />
      <span className="typo-micro">Filter:</span>
      <button
        onClick={() => setFilterTag('')}
        aria-pressed={filterTag === ''}
        className={`h-8 px-3 rounded-full typo-micro font-medium border transition-colors focus-ring ${
          filterTag === ''
            ? 'bg-[rgb(var(--surface-4))] text-[rgb(var(--accent))] shadow-[var(--depth-1)] border-[rgb(var(--border-subtle))]'
            : 'bg-[rgb(var(--surface-3))] text-[rgb(var(--text-secondary))] border-[rgb(var(--border))] hover:border-[rgb(var(--border-hover))]'
        }`}
      >
        All
      </button>
      {allTags.map(t => (
        <button
          key={t}
          onClick={() => setFilterTag(filterTag === t ? '' : t)}
          aria-pressed={filterTag === t}
          className={`h-8 px-3 rounded-full typo-micro font-medium border transition-colors focus-ring ${
            filterTag === t
              ? 'bg-[rgb(var(--surface-4))] text-[rgb(var(--accent))] shadow-[var(--depth-1)] border-[rgb(var(--border-subtle))]'
              : 'bg-[rgb(var(--surface-3))] text-[rgb(var(--text-secondary))] border-[rgb(var(--border))] hover:border-[rgb(var(--border-hover))]'
          }`}
        >
          {t}
        </button>
      ))}
      <button
        onClick={() => setShowArchived(!showArchived)}
        aria-pressed={showArchived}
        className={`ml-auto h-8 px-3 rounded-full typo-micro font-medium border transition-colors focus-ring ${
          showArchived
            ? 'bg-[rgb(var(--surface-4))] text-[rgb(var(--accent))] shadow-[var(--depth-1)] border-[rgb(var(--border-subtle))]'
            : 'bg-[rgb(var(--surface-3))] text-[rgb(var(--text-tertiary))] border-[rgb(var(--border))] hover:border-[rgb(var(--border-hover))]'
        }`}
      >
        {showArchived ? 'Showing archived' : 'Show archived'}
      </button>
    </div>

    {(search || filterTag) && (
      <div className="flex items-center justify-between gap-3 mt-3 pt-3 border-t border-[rgb(var(--border-subtle))]">
        <span className="typo-micro">Showing {filteredCount} of {noteCount} notes</span>
        {search && (
          <button
            onClick={() => setSearch('')}
            className="typo-micro text-accent hover:underline flex items-center gap-1 focus-ring rounded px-1"
          >
            <span>Clear search</span>
            <Search className="w-3 h-3" aria-hidden="true" />
          </button>
        )}
      </div>
    )}
  </section>
)

// === EMPTY STATE ===
const EmptyState: React.FC<{ onCreate: () => void; hasSearch: boolean }> = ({ onCreate, hasSearch }) => (
  <div className="card-secondary p-8 flex flex-col items-center justify-center text-center stagger-in">
    <span className="grid place-items-center w-12 h-12 rounded-xl mb-4 bg-[rgb(var(--surface-4))] border border-[rgb(var(--border-subtle))] text-[rgb(var(--text-tertiary))]" aria-hidden="true">
      <BookOpen className="w-5 h-5" />
    </span>
    <h3 className="typo-card-title">{hasSearch ? 'No matching notes' : 'No notes yet'}</h3>
    <p className="typo-body-sm mt-1.5 max-w-sm">
      {hasSearch
        ? 'Try adjusting your search or filter to find what you are looking for.'
        : 'Write down a thought, a decision, or something you want to remember. Notes can be linked to a goal or a task.'}
    </p>
    {!hasSearch && (
      <button onClick={onCreate} className="btn-primary btn-sm mt-5 focus-ring">
        <Plus className="w-4 h-4" aria-hidden="true" /> Create first note
      </button>
    )}
  </div>
)

// === LOADING SKELETON ===
const NotesSkeleton: React.FC = () => (
  <div className="row-stack stagger-in-fast" aria-busy="true" aria-label="Loading notes">
    {[1, 2, 3].map(i => (
      <div key={i} className="row-item !p-4">
        <div className="flex-1 min-w-0 space-y-2">
          <div className="w-40 h-4 skeleton rounded" />
          <div className="w-full h-3 skeleton rounded" />
          <div className="w-5/6 h-3 skeleton rounded" />
        </div>
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
    <h3 className="typo-card-title">Could not load your notes</h3>
    <p className="typo-body-sm mt-1.5 max-w-sm">{message}</p>
    <button onClick={onRetry} className="btn-primary btn-sm mt-5 focus-ring">
      <Loader2 className="w-4 h-4" aria-hidden="true" /> Try again
    </button>
  </div>
)

// === MAIN COMPONENT ===
export const NotesView: React.FC = () => {
  const { user } = useAuth()
  const [notes, setNotes] = useState<Note[]>([])
  const [search, setSearch] = useState('')
  const [filterTag, setFilterTag] = useState('')
  const [showArchived, setShowArchived] = useState(false)
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [editingNote, setEditingNote] = useState<Note | null>(null)
  const [creating, setCreating] = useState(true)
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)
  const [busyId, setBusyId] = useState<number | null>(null)
  const [migrationNotice, setMigrationNotice] = useState<string | null>(null)

  const [goals, setGoals] = useState<{ id: number; title: string }[]>([])
  const [tasks, setTasks] = useState<{ id: number; title: string }[]>([])

  const load = useCallback(async () => {
    setLoading(true)
    setLoadError(null)
    try {
      // The tag filter is applied client-side so the tag chips stay derivable
      // from the currently loaded set (a server-filtered list would collapse
      // the chip row to just the selected tag).
      const data = await noteService.getNotes({ isArchived: showArchived })
      setNotes(data)
    } catch (e) {
      setNotes([])
      setLoadError(extractErrorMessage(e, 'Failed to load notes.'))
    } finally {
      setLoading(false)
    }
  }, [showArchived])

  useEffect(() => { load() }, [load])

  // Optional link targets for the editor.
  useEffect(() => {
    let active = true
    const loadLinks = async () => {
      const [goalRes, taskRes] = await Promise.all([
        goalService.getGoals().catch(() => []),
        taskService.getTasks().catch(() => []),
      ])
      if (!active) return
      setGoals(Array.isArray(goalRes) ? goalRes.map(g => ({ id: g.id, title: g.title })) : [])
      setTasks(Array.isArray(taskRes) ? taskRes.map(t => ({ id: t.id, title: t.title })) : [])
    }
    loadLinks()
    return () => { active = false }
  }, [])

  // One-time import of any legacy localStorage notes into this account.
  useEffect(() => {
    if (!user?.id) return
    let active = true
    const migrate = async () => {
      try {
        const result = await runLegacyMigration(user.id, user.id)
        if (!active) return
        const summary = getLegacyMigrationSummary(result)
        if (summary) {
          setMigrationNotice(summary)
          setLoadError(null)
          await load()
        }
      } catch {
        /* migration is best-effort */
      }
    }
    migrate()
    return () => { active = false }
  }, [user?.id])

  const allTags = useMemo(() => [...new Set(notes.map(n => n.tag))].sort(), [notes])

  const filteredNotes = useMemo(() => {
    return notes.filter(note => {
      const matchesSearch = !search ||
        note.title.toLowerCase().includes(search.toLowerCase()) ||
        note.content.toLowerCase().includes(search.toLowerCase()) ||
        note.tag.toLowerCase().includes(search.toLowerCase())
      const matchesTag = !filterTag || note.tag === filterTag
      return matchesSearch && matchesTag
    })
  }, [notes, search, filterTag])

  const selectedNote = useMemo(
    () => notes.find(n => n.id === selectedId) || null,
    [notes, selectedId],
  )

  const handleCreate = async (values: { title: string; content: string; tag: string; goalId: number | null; taskId: number | null }) => {
    setSubmitting(true)
    setFormError(null)
    try {
      const created = await noteService.createNote({
        title: values.title,
        content: values.content,
        tag: values.tag,
        goal_id: values.goalId,
        task_id: values.taskId,
      })
      await load()
      setSelectedId(created.id)
      setEditingNote(null)
      setCreating(false)
    } catch (e) {
      setFormError(extractErrorMessage(e, 'Could not save the note.'))
    } finally {
      setSubmitting(false)
    }
  }

  const handleUpdate = async (values: { title: string; content: string; tag: string; goalId: number | null; taskId: number | null }) => {
    if (!editingNote) return
    setSubmitting(true)
    setFormError(null)
    try {
      const updated = await noteService.updateNote(editingNote.id, {
        title: values.title,
        content: values.content,
        tag: values.tag,
        goal_id: values.goalId,
        task_id: values.taskId,
      })
      await load()
      setSelectedId(updated.id)
      setEditingNote(null)
    } catch (e) {
      setFormError(extractErrorMessage(e, 'Could not update the note.'))
    } finally {
      setSubmitting(false)
    }
  }

  const handleDelete = async (note: Note) => {
    if (!window.confirm(`Delete "${note.title}"? This cannot be undone.`)) return
    setBusyId(note.id)
    try {
      await noteService.deleteNote(note.id)
      if (selectedId === note.id) setSelectedId(null)
      if (editingNote?.id === note.id) setEditingNote(null)
      await load()
    } catch (e) {
      setLoadError(extractErrorMessage(e, 'Could not delete the note.'))
    } finally {
      setBusyId(null)
    }
  }

  const togglePin = async (note: Note) => {
    setBusyId(note.id)
    try {
      await noteService.updateNote(note.id, { is_pinned: !note.is_pinned })
      await load()
    } catch (e) {
      setLoadError(extractErrorMessage(e, 'Could not update the note.'))
    } finally {
      setBusyId(null)
    }
  }

  const toggleArchive = async (note: Note) => {
    setBusyId(note.id)
    try {
      await noteService.updateNote(note.id, { is_archived: !note.is_archived })
      if (selectedId === note.id) setSelectedId(null)
      await load()
    } catch (e) {
      setLoadError(extractErrorMessage(e, 'Could not update the note.'))
    } finally {
      setBusyId(null)
    }
  }

  const startNew = () => {
    setEditingNote(null)
    setCreating(true)
    setSelectedId(null)
    setFormError(null)
  }

  const startEdit = (note: Note) => {
    setEditingNote(note)
    setCreating(false)
    setFormError(null)
  }

  return (
    <div className="relative space-y-6 animate-fadeInUp">
      {/* === HEADER ===
          No 40px icon tile: a label carries the orientation, the title is
          typography. */}
      <div className="stagger-in">
        <p className="section-header-label !m-0 !p-0">
          <BookOpen className="w-3.5 h-3.5 !text-[rgb(var(--accent))]" aria-hidden="true" />
          Content
        </p>
        <h1 className="typo-h1 mt-2">Notes</h1>
        <p className="typo-meta mt-1.5">
          Thoughts, decisions, and references — optionally linked to a goal or task.
        </p>
      </div>

      {migrationNotice && (
        <div
          role="status"
          className="card px-4 py-3 rounded-xl border border-[rgb(var(--accent-tertiary) / 0.3)] bg-[rgb(var(--accent-tertiary) / 0.08)] flex items-center gap-2 text-sm text-[rgb(var(--accent-tertiary))] animate-fadeInUp"
        >
          <Check className="w-4 h-4 shrink-0" />
          {migrationNotice}
          <button
            onClick={() => setMigrationNotice(null)}
            className="ml-auto text-xs font-mono opacity-70 hover:opacity-100 focus-ring rounded px-1"
          >
            dismiss
          </button>
        </div>
      )}

      {/* === LAYOUT: LIST + EDITOR === */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* LEFT: NOTES LIST */}
        <div className="lg:col-span-1 space-y-5">
          <SearchFilter
            search={search}
            setSearch={setSearch}
            filterTag={filterTag}
            setFilterTag={setFilterTag}
            allTags={allTags}
            noteCount={notes.length}
            filteredCount={filteredNotes.length}
            showArchived={showArchived}
            setShowArchived={setShowArchived}
          />

          <section aria-label="Notes list" className="stagger-in" style={{ animationDelay: '160ms' }}>
            {loading ? (
              <NotesSkeleton />
            ) : loadError && notes.length === 0 ? (
              <ErrorState message={loadError} onRetry={load} />
            ) : filteredNotes.length === 0 ? (
              <EmptyState onCreate={startNew} hasSearch={!!search || !!filterTag} />
            ) : (
              <div className="row-stack">
                {filteredNotes.map((note, i) => (
                  <NoteCard
                    key={note.id}
                    note={note}
                    isSelected={selectedId === note.id}
                    onSelect={() => { setSelectedId(note.id); setEditingNote(null); setCreating(false) }}
                    onEdit={() => startEdit(note)}
                    onDelete={() => handleDelete(note)}
                    onTogglePin={() => togglePin(note)}
                    onToggleArchive={() => toggleArchive(note)}
                    index={i}
                    busyId={busyId}
                  />
                ))}
              </div>
            )}
          </section>
        </div>

        {/* RIGHT: EDITOR / DETAIL */}
        <div className="lg:col-span-2 space-y-6">
          {editingNote || creating ? (
            <NoteEditor
              note={editingNote}
              goals={goals}
              tasks={tasks}
              submitting={submitting}
              error={formError}
              onSave={editingNote ? handleUpdate : handleCreate}
              onCancel={() => { setEditingNote(null); setCreating(false); setFormError(null) }}
              isNew={!editingNote}
            />
          ) : selectedNote ? (
            <section aria-label="Note detail" className="card-hero p-5 md:p-6 stagger-in space-y-5" style={{ animationDelay: '240ms' }}>
              <div className="flex items-start justify-between gap-4 flex-wrap">
                <div className="min-w-0">
                  <p className="typo-micro mb-2">
                    <span className="!normal-case !tracking-[0.06em] !font-normal text-[rgb(var(--accent-tertiary))]">{selectedNote.tag}</span>
                    {selectedNote.is_pinned && (
                      <>
                        <span className="w-1 h-1 rounded-full bg-[rgb(var(--border-strong))] inline-block align-middle mx-1.5" aria-hidden="true" />
                        <span className="!normal-case !tracking-[0.06em] !font-normal text-[rgb(var(--warning))]">Pinned</span>
                      </>
                    )}
                    {selectedNote.is_archived && (
                      <>
                        <span className="w-1 h-1 rounded-full bg-[rgb(var(--border-strong))] inline-block align-middle mx-1.5" aria-hidden="true" />
                        <span className="!normal-case !tracking-[0.06em] !font-normal text-[rgb(var(--text-tertiary))]">Archived</span>
                      </>
                    )}
                    <span className="typo-meta ml-auto">
                      <span className="w-1 h-1 rounded-full bg-[rgb(var(--text-muted))] inline-block align-middle mr-1.5" aria-hidden="true" />
                      Updated {new Date(selectedNote.updated_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })}
                    </span>
                  </p>
                  <h2 className="typo-card-title">{selectedNote.title}</h2>
                </div>
                <div className="flex items-center gap-2 shrink-0 flex-wrap">
                  <button
                    onClick={() => togglePin(selectedNote)}
                    className="btn-secondary btn-sm focus-ring"
                  >
                    {selectedNote.is_pinned ? <PinOff className="w-4 h-4" aria-hidden="true" /> : <Pin className="w-4 h-4" aria-hidden="true" />}
                    {selectedNote.is_pinned ? 'Unpin' : 'Pin'}
                  </button>
                  <button
                    onClick={() => toggleArchive(selectedNote)}
                    className="btn-secondary btn-sm focus-ring"
                  >
                    {selectedNote.is_archived ? <ArchiveRestore className="w-4 h-4" aria-hidden="true" /> : <Archive className="w-4 h-4" aria-hidden="true" />}
                    {selectedNote.is_archived ? 'Unarchive' : 'Archive'}
                  </button>
                  <button
                    onClick={() => startEdit(selectedNote)}
                    className="btn-secondary btn-sm focus-ring"
                  >
                    <Edit2 className="w-4 h-4" aria-hidden="true" /> Edit
                  </button>
                  <button
                    onClick={() => handleDelete(selectedNote)}
                    className="btn-danger btn-sm focus-ring"
                  >
                    <Trash2 className="w-4 h-4" aria-hidden="true" /> Delete
                  </button>
                </div>
              </div>

              <div className="pt-4 border-t border-[rgb(var(--border-subtle))]">
                <div className="max-w-none typo-body whitespace-pre-wrap leading-relaxed break-words text-[rgb(var(--text-secondary))]">
                  {selectedNote.content || <span className="text-[rgb(var(--text-muted))]">No content</span>}
                </div>
              </div>

              <div className="pt-4 border-t border-[rgb(var(--border-subtle))] flex items-center justify-between gap-3 typo-meta">
                <span>Created {new Date(selectedNote.created_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })}</span>
                <span>ID: {selectedNote.id}</span>
              </div>
            </section>
          ) : (
            <div className="card-secondary p-10 flex flex-col items-center justify-center text-center">
              <BookOpen className="w-8 h-8 text-[rgb(var(--text-muted))] mb-3" aria-hidden="true" />
              <h3 className="typo-card-title">No note selected</h3>
              <p className="typo-body-sm mt-1.5 mb-4">
                Select a note to read it, or create a new one.
              </p>
              <button onClick={startNew} className="btn-primary focus-ring">
                <Plus className="w-4 h-4" aria-hidden="true" /> New note
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}