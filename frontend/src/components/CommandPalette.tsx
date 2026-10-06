import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  Activity,
  BookOpen,
  CalendarDays,
  Cpu,
  DollarSign,
  LoaderCircle,
  type LucideIcon,
  RefreshCw,
  Search,
  Settings,
  Sparkles,
  SquareCheck,
  Target,
  User,
  X,
} from 'lucide-react'
import { searchService } from '../services/services'
import type { SearchEntityType, SearchResult } from '../types'

const MIN_QUERY_LENGTH = 2
const SEARCH_DEBOUNCE_MS = 250
const SEARCH_LIMIT = 20

/** Navigation shortcuts. These are pure client actions — never a backend call. */
const NAV_COMMANDS = [
  { name: 'Go to Dashboard', tab: 'dashboard', icon: Cpu, desc: 'Overview & insights' },
  { name: 'View Tasks', tab: 'tasks', icon: SquareCheck, desc: 'Everything on your plate' },
  { name: 'Manage Goals', tab: 'goals', icon: Target, desc: 'Objectives & progress' },
  { name: 'Daily Habits', tab: 'habits', icon: Activity, desc: 'Streaks & routines' },
  { name: 'Finance', tab: 'finance', icon: DollarSign, desc: 'Income & expenses' },
  { name: 'Notes', tab: 'notes', icon: BookOpen, desc: 'Your written notes' },
  { name: 'AI Assistant', tab: 'ai', icon: Cpu, desc: 'Ask about your data' },
  { name: 'Profile', tab: 'profile', icon: User, desc: 'Your account' },
  { name: 'Settings', tab: 'settings', icon: Settings, desc: 'Preferences' },
]

const ENTITY_META: Record<SearchEntityType, { label: string; icon: LucideIcon }> = {
  task: { label: 'Task', icon: SquareCheck },
  goal: { label: 'Goal', icon: Target },
  habit: { label: 'Habit', icon: Activity },
  note: { label: 'Note', icon: BookOpen },
  planner_event: { label: 'Planner', icon: CalendarDays },
  transaction: { label: 'Finance', icon: DollarSign },
}

/** Rows the keyboard can land on, in visual order. */
type PaletteCommand = { kind: 'command'; id: string; tab: string; label: string; desc: string; icon: LucideIcon }
type PaletteResult = { kind: 'result'; id: string; result: SearchResult; index: number }
type PaletteItem = PaletteCommand | PaletteResult

/** Group results by entity type, preserving the backend's ordering. */
function groupResults(items: PaletteItem[]): Array<{ type: SearchEntityType; items: PaletteResult[] }> {
  const groups: Array<{ type: SearchEntityType; items: PaletteResult[] }> = []

  for (const item of items) {
    if (item.kind !== 'result') continue
    const existing = groups.find(group => group.type === item.result.entity_type)
    if (existing) existing.items.push(item)
    else groups.push({ type: item.result.entity_type, items: [item] })
  }

  return groups
}

function isAbort(error: unknown): boolean {
  if (error instanceof DOMException) return error.name === 'AbortError'

  return typeof error === 'object' && error !== null && 'code' in error && error.code === 'ERR_CANCELED'
}

export const CommandPalette: React.FC<{
  isOpen: boolean
  onClose: () => void
  setActiveTab: (t: string) => void
}> = ({ isOpen, onClose, setActiveTab }) => {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<SearchResult[]>([])
  const [isSearching, setIsSearching] = useState(false)
  const [searchError, setSearchError] = useState<string | null>(null)
  const [activeIndex, setActiveIndex] = useState(0)
  const [retryToken, setRetryToken] = useState(0)

  const inputRef = useRef<HTMLInputElement>(null)
  const listRef = useRef<HTMLDivElement>(null)
  const abortRef = useRef<AbortController | null>(null)
  const requestIdRef = useRef(0)

  useEffect(() => {
    if (isOpen) setTimeout(() => inputRef.current?.focus(), 20)
  }, [isOpen])

  useEffect(() => {
    if (!isOpen) {
      setQuery('')
      setResults([])
      setSearchError(null)
      setIsSearching(false)
      setActiveIndex(0)
      abortRef.current?.abort()
    }
  }, [isOpen])

  const trimmed = query.trim()
  const shouldSearch = trimmed.length >= MIN_QUERY_LENGTH

  // Debounced global search. The request only fires once typing pauses, and
  // any in-flight request is aborted when a newer query supersedes it.
  useEffect(() => {
    if (!isOpen || !shouldSearch) {
      abortRef.current?.abort()
      setResults([])
      setSearchError(null)
      setIsSearching(false)
      return
    }

    const controller = new AbortController()
    abortRef.current = controller
    requestIdRef.current += 1
    const requestId = requestIdRef.current

    const timer = setTimeout(async () => {
      setIsSearching(true)
      setSearchError(null)

      try {
        const response = await searchService.search(trimmed, {
          limit: SEARCH_LIMIT,
          signal: controller.signal,
        })
        // Ignore a response that a newer query has already superseded.
        if (requestId !== requestIdRef.current) return
        setResults(response.results ?? [])
      } catch (error) {
        if (isAbort(error) || requestId !== requestIdRef.current) return
        setResults([])
        setSearchError('Search failed. Check your connection and try again.')
      } finally {
        if (requestId === requestIdRef.current) setIsSearching(false)
      }
    }, SEARCH_DEBOUNCE_MS)

    return () => {
      clearTimeout(timer)
      controller.abort()
    }
  }, [trimmed, shouldSearch, isOpen, retryToken])

  const filteredCommands = useMemo(() => {
    const needle = trimmed.toLowerCase()
    if (!needle) return NAV_COMMANDS
    return NAV_COMMANDS.filter(
      command => command.name.toLowerCase().includes(needle) || command.desc.toLowerCase().includes(needle)
    )
  }, [trimmed])

  // Search results lead the list — they are what the user typed for — followed
// by the matching navigation commands. `index` is the position in `items`, so
// keyboard selection and click selection stay in lockstep.
  const items = useMemo<PaletteItem[]>(
    () => [
      ...results.map((result, index) => ({
        kind: 'result' as const,
        id: `result:${result.entity_type}:${result.id}`,
        result,
        index,
      })),
      ...filteredCommands.map(command => ({
        kind: 'command' as const,
        id: `command:${command.tab}`,
        tab: command.tab,
        label: command.name,
        desc: command.desc,
        icon: command.icon,
      })),
    ],
    [filteredCommands, results]
  )

  const commandIndex = useMemo(() => {
    const map = new Map<string, number>()
    items.forEach((item, index) => map.set(item.id, index))
    return map
  }, [items])

  const groups = useMemo(() => groupResults(items), [items])

  const openItem = useCallback(
    (item: PaletteItem) => {
      if (item.kind === 'command') {
        setActiveTab(item.tab)
      } else {
        setActiveTab(item.result.route)
      }
      onClose()
    },
    [onClose, setActiveTab]
  )

  useEffect(() => {
    // Keep the selection in range as results stream in and out.
    setActiveIndex(index => (index >= items.length ? 0 : index))
  }, [items.length])

  useEffect(() => {
    setActiveIndex(0)
  }, [trimmed])

  useEffect(() => {
    if (activeIndex > 0) {
      listRef.current?.querySelector('[data-active="true"]')?.scrollIntoView({ block: 'nearest' })
    }
  }, [activeIndex])

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-[10vh] p-4">
      <button aria-hidden onClick={onClose} className="modal-backdrop absolute inset-0" />
      <div
        role="dialog"
        aria-modal="true"
        aria-label="Command palette"
        className="relative w-full max-w-[560px] rounded-[20px] overflow-hidden modal-content animate-fadeIn"
      >
        <div className="flex items-center gap-3 px-4 py-3.5 border-b border-[rgb(var(--border))]">
          <span className="w-8 h-8 grid place-items-center rounded-xl bg-[rgb(var(--accent-tertiary)/0.1)] border border-[rgb(var(--accent-tertiary)/0.25)] text-[rgb(var(--accent-tertiary))]">
            {isSearching ? (
              <LoaderCircle className="w-4 h-4 animate-spin" />
            ) : (
              <Search className="w-4 h-4" />
            )}
          </span>
          <input
            ref={inputRef}
            value={query}
            onChange={e => setQuery(e.target.value)}
            onKeyDown={e => {
              if (e.key === 'ArrowDown') {
                e.preventDefault()
                setActiveIndex(index => (items.length === 0 ? 0 : (index + 1) % items.length))
              } else if (e.key === 'ArrowUp') {
                e.preventDefault()
                setActiveIndex(index => (items.length === 0 ? 0 : (index - 1 + items.length) % items.length))
              } else if (e.key === 'Enter') {
                e.preventDefault()
                const item = items[activeIndex]
                if (item) openItem(item)
              } else if (e.key === 'Escape') {
                e.preventDefault()
                onClose()
              }
            }}
            placeholder="Search your LifeOS or jump to a view…"
            aria-label="Global search"
            className="flex-1 bg-transparent text-sm text-[rgb(var(--text-primary))] placeholder:text-[rgb(var(--text-muted))] focus:outline-none"
          />
          <kbd className="hidden sm:inline-flex px-1.5 py-1 rounded-md bg-[rgb(var(--surface))] border border-[rgb(var(--border))] text-[10px] font-mono text-[rgb(var(--text-secondary))]">ESC</kbd>
          <button
            onClick={onClose}
            className="w-10 h-10 grid place-items-center rounded-xl hover:bg-[rgb(var(--surface-hover))] text-[rgb(var(--text-tertiary))] transition-colors focus-ring"
            aria-label="Close command palette"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Cap at 60vh on mobile so the panel never exceeds the viewport,
            keep 420px on larger screens. */}
        <div ref={listRef} className="p-2 max-h-[60vh] sm:max-h-[420px] overflow-y-auto scroll-y">
          {searchError ? (
            <div role="alert" className="flex flex-col items-center gap-3 py-10 text-center">
              <p className="text-sm text-[rgb(var(--danger))]">{searchError}</p>
              <button
                onClick={() => setRetryToken(token => token + 1)}
                className="inline-flex items-center gap-2 h-9 px-3 rounded-xl text-xs font-mono bg-[rgb(var(--surface))] border border-[rgb(var(--border))] text-[rgb(var(--text-secondary))] hover:border-[rgb(var(--accent)/0.4)] hover:text-[rgb(var(--accent))] transition-colors focus-ring"
              >
                <RefreshCw className="w-3.5 h-3.5" /> Retry
              </button>
            </div>
          ) : (
            <>
              {groups.length > 0 && (
                <div className="space-y-2">
                  {groups.map(group => {
                    const meta = ENTITY_META[group.type]
                    const GroupIcon = meta.icon
                    return (
                      <div key={group.type}>
                        <p className="px-3 py-1.5 flex items-center gap-2 text-[10px] font-mono uppercase tracking-widest text-[rgb(var(--text-tertiary))]">
                          <GroupIcon className="w-3 h-3" />
                          {meta.label}
                          <span className="opacity-60">{group.items.length}</span>
                        </p>
                        {group.items.map(item => {
                          const index = item.index
                          const result = item.result
                          const active = index === activeIndex
                          return (
                            <button
                              key={item.id}
                              data-active={active}
                              onMouseEnter={() => setActiveIndex(index)}
                              onClick={() => openItem(item)}
                              className={`w-full flex items-center justify-between gap-3 px-3 py-2.5 rounded-xl border text-left transition-colors focus-ring ${
                                active
                                  ? 'bg-[rgb(var(--accent-soft))] border-[rgb(var(--accent)/0.35)]'
                                  : 'border-transparent hover:bg-[rgb(var(--surface))] hover:border-[rgb(var(--border))]'
                              }`}
                            >
                              <span className="min-w-0">
                                <span className="block text-sm font-medium text-[rgb(var(--text-primary))] truncate">{result.title}</span>
                                {(result.snippet || result.context) && (
                                  <span className="block text-xs text-[rgb(var(--text-tertiary))] mt-1 truncate">
                                    {result.snippet || result.context}
                                  </span>
                                )}
                              </span>
                              <span className="hidden shrink-0 sm:inline-flex items-center gap-1 text-[10px] font-mono px-2 py-1 rounded-full bg-[rgb(var(--surface))] border border-[rgb(var(--border))] text-[rgb(var(--text-tertiary))]">
                                {result.tag || result.category || result.frequency || result.status || meta.label}
                              </span>
                            </button>
                          )
                        })}
                      </div>
                    )
                  })}
                </div>
              )}

              {filteredCommands.length > 0 && (
                <div className={groups.length > 0 ? 'mt-3' : ''}>
                  <p className="px-3 pt-2 pb-1 text-[10px] font-mono uppercase tracking-widest text-[rgb(var(--text-tertiary))]">
                    {shouldSearch ? 'Matching commands' : 'Navigate'}
                  </p>
                  {filteredCommands.map(command => {
                    const index = commandIndex.get(`command:${command.tab}`) ?? 0
                    const Icon = command.icon
                    const active = index === activeIndex
                    return (
                      <button
                        key={command.tab}
                        data-active={active}
                        onMouseEnter={() => setActiveIndex(index)}
                        onClick={() => openItem(items[index])}
                        className={`w-full flex items-center justify-between gap-3 px-3 py-2.5 rounded-xl border text-left transition-colors focus-ring group ${
                          active
                            ? 'bg-[rgb(var(--accent-soft))] border-[rgb(var(--accent)/0.35)]'
                            : 'border-transparent hover:bg-[rgb(var(--surface))] hover:border-[rgb(var(--border))]'
                        }`}
                      >
                        <span className="flex items-center gap-3 min-w-0">
                          <span className="w-9 h-9 grid place-items-center rounded-xl bg-[rgb(var(--surface))] border border-[rgb(var(--border))] group-hover:border-[rgb(var(--accent)/0.3)]">
                            <Icon className="w-4 h-4 text-[rgb(var(--text-tertiary))] group-hover:text-[rgb(var(--accent))]" />
                          </span>
                          <span className="min-w-0">
                            <span className="block text-sm font-medium leading-none text-[rgb(var(--text-primary))]">{command.name}</span>
                            <span className="block text-xs font-mono text-[rgb(var(--text-tertiary))] mt-1">{command.desc}</span>
                          </span>
                        </span>
                        <span className="hidden sm:inline-flex items-center gap-1 text-[11px] font-mono px-2 py-1 rounded-full bg-[rgb(var(--surface))] border border-[rgb(var(--border))] text-[rgb(var(--text-tertiary))] group-hover:text-[rgb(var(--accent))]">Jump →</span>
                      </button>
                    )
                  })}
                </div>
              )}

              {groups.length === 0 && filteredCommands.length === 0 && (
                <div className="py-10 text-center text-sm font-mono text-[rgb(var(--text-tertiary))]">
                  {shouldSearch ? `No matches for “${trimmed}”` : `Type at least ${MIN_QUERY_LENGTH} characters to search`}
                </div>
              )}
            </>
          )}
        </div>

        <div className="px-4 py-3 border-t border-[rgb(var(--border))] flex items-center justify-between gap-2 text-[11px] font-mono text-[rgb(var(--text-tertiary))]">
          <span className="flex items-center gap-2">
            <Sparkles className="w-3.5 h-3.5 text-accent" /> ↑↓ navigate • ↵ open • ESC close
          </span>
          <span className="hidden sm:inline">⌘K anywhere</span>
        </div>
      </div>
    </div>
  )
}