import React, { useEffect, useRef, useState } from 'react'
import { Bell, Check, CheckCheck, Loader2, AlertCircle, Inbox, ExternalLink } from 'lucide-react'
import { useNotifications } from '../context/NotificationsContext'
import { parseNaiveUtc } from '../utils/datetime'
import { ReminderModal } from './ReminderModal'

/**
 * Semantic status tints, resolved from the token layer rather than baked-in
 * Tailwind hues. The previous map hard-coded cyan/emerald/amber/rose, which is
 * why the panel read as a second, unrelated colour system next to the rest of
 * the app — and why none of it survived a light-theme pass.
 *
 * The helper returns inline styles because the tokens are space-separated RGB
 * channels (`139 92 246`); Tailwind's `/50` opacity modifier cannot wrap a
 * `rgb(var(--token))` value the way it wraps a hex one.
 */
const tint = (token: string) => ({
  color: `rgb(var(${token}))`,
  backgroundColor: `rgb(var(${token}) / 0.1)`,
  borderColor: `rgb(var(${token}) / 0.28)`,
})

const TYPE_TINT: Record<string, React.CSSProperties> = {
  info: tint('--accent-tertiary'),
  success: tint('--success'),
  warning: tint('--warning'),
  error: tint('--danger'),
}

/**
 * Notification links are LifeOS tab paths (`/tasks`, `/planner`, `/habits`),
 * not router paths — the app navigates by switching the active tab. Unknown
 * or absent links resolve to null so a stale link can never navigate nowhere.
 */
const TAB_FOR_LINK: Record<string, string> = {
  '/tasks': 'tasks',
  '/planner': 'planner',
  '/planner-events': 'planner',
  '/habits': 'habits',
  '/notes': 'notes',
  '/finance': 'finance',
}

// Backend timestamps are naive UTC — parse them as UTC rather than letting
// `new Date(string)` guess the local zone and shift the "time ago".
const relativeTime = (iso: string) => {
  const parsed = parseNaiveUtc(iso)
  const seconds = Math.floor((Date.now() - parsed.getTime()) / 1000)
  if (Number.isNaN(seconds)) return ''
  if (seconds < 60) return 'just now'
  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) return `${minutes}m ago`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}h ago`
  return parsed.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
}

/**
 * Header notification dropdown, backed entirely by /notifications.
 *
 * Refresh cadence lives in NotificationsContext (interval + visibility/focus),
 * so this component simply renders whatever state the context holds — including
 * notifications delivered by the backend scheduler while the tab was open.
 */
export const NotificationBell: React.FC<{ onNavigate?: (tab: string) => void }> = ({ onNavigate }) => {
  const { notifications, unreadCount, loading, error, markRead, markAllRead, reload } = useNotifications()
  const [open, setOpen] = useState(false)
  const [remindersOpen, setRemindersOpen] = useState(false)
  const panelRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return
    const onClickAway = (e: MouseEvent) => {
      if (panelRef.current && !panelRef.current.contains(e.target as Node)) setOpen(false)
    }
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false)
    }
    document.addEventListener('mousedown', onClickAway)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('mousedown', onClickAway)
      document.removeEventListener('keydown', onKey)
    }
  }, [open])

  const sorted = [...notifications].sort(
    (a, b) => parseNaiveUtc(b.created_at).getTime() - parseNaiveUtc(a.created_at).getTime(),
  )

  /**
   * Opening a linked notification marks it read and moves the user to the
   * relevant LifeOS tab. Marking first means a refresh mid-navigation still
   * shows the notification as read — the backend confirmed it before we move.
   */
  const openNotification = async (id: number, link: string | null) => {
    await markRead(id);

    const tab = link ? TAB_FOR_LINK[link] : undefined;
    if (tab && onNavigate) {
      onNavigate(tab);
      setOpen(false);
    }
  }

  return (
    // `md:relative` rather than `relative`, and only for the panel's benefit.
    //
    // This div is the containing block the dropdown is measured against. With
    // `relative` here, `right-0` pinned the panel's right edge to a 36px-wide
    // box sitting near the right of the mobile top bar, so a 340px panel hung
    // off the *left* edge of the viewport and its first ~65px were clipped.
    // `max-w-[calc(100vw-2rem)]` could not save it — that clamp limits width,
    // and the width was never the problem; the anchor was.
    //
    // Dropping `relative` below `md` lets the absolutely-positioned panel fall
    // through to the mobile top bar, which is `sticky` and therefore also a
    // containing block, and which spans the viewport. The panel can then be
    // inset from the viewport itself. From `md` up, `relative` is restored and
    // the original `right-0` / `w-[340px]` desktop anchoring is unchanged.
    //
    // The unread badge is unaffected: it is positioned against the inner
    // <button>, which carries its own `relative`.
    <div className="md:relative" ref={panelRef}>
      <button
        onClick={() => setOpen((v) => !v)}
        aria-label={`Notifications${unreadCount > 0 ? `, ${unreadCount} unread` : ''}`}
        aria-expanded={open}
        aria-haspopup="true"
        className="btn-icon relative focus-ring"
      >
        <Bell className="w-[18px] h-[18px]" />
        {unreadCount > 0 && (
          // The old badge carried a permanent cyan outer glow that repainted the
          // whole button on every frame it was visible. A flat accent fill
          // reads just as clearly against both themes.
          <span
            className="absolute -top-0.5 -right-0.5 min-w-[1.15rem] h-5 px-1 grid place-items-center rounded-full bg-[rgb(var(--accent))] border-2 border-[rgb(var(--bg))] text-[10px] font-mono font-bold text-[rgb(var(--text-inverse))]"
          >
            {unreadCount > 99 ? '99+' : unreadCount}
          </span>
        )}
      </button>

      {open && (
        // Mobile: inset from the viewport edges by the top bar's own px-4
        // gutter. Desktop: back to the original `right-0` anchor against the
        // bell. `max-w` and `w-full` together mean "fill the inset box, never
        // exceed it" — at 375px the panel spans 375 - 2x16 = 343px, which is
        // wide enough for the row layout to breathe and still 3px narrower
        // than the old 340px was of the 375px viewport.
        //
        // These are `//` rather than a JSX `{/* */}` comment on purpose. This
        // comment sits inside the `{open && ( ... )}` expression, where the
        // parser is in JavaScript expression context, not JSX children
        // context — there a `{/* */}` block is read as an empty object
        // literal, leaving `open && ({})` followed by a stray `<div>`, which
        // is a syntax error.
        <div
          role="dialog"
          aria-label="Notifications"
          className="absolute inset-x-4 mt-2 w-full max-w-[340px] md:inset-x-auto md:right-0 md:w-[340px] card p-0 overflow-hidden z-50 animate-revealLayer"
        >
          <div className="absolute top-0 left-0 right-0 h-px bg-[rgb(var(--accent)/0.35)] pointer-events-none" />

          <div className="relative z-10 flex items-center justify-between gap-2 px-4 py-3 border-b border-[rgb(var(--border))]">
            <h3 className="text-xs font-mono tracking-widest text-[rgb(var(--text-tertiary))]">NOTIFICATIONS</h3>
            <div className="flex items-center gap-1">
              <button
                onClick={() => { setOpen(false); setRemindersOpen(true) }}
                className="inline-flex items-center gap-1 h-8 px-1.5 text-[11px] font-mono text-accent text-accent-hover transition-colors focus-ring rounded"
              >
                <Bell className="w-3.5 h-3.5" /> Reminders
              </button>
              <button
                onClick={reload}
                aria-label="Refresh notifications"
                className="w-8 h-8 grid place-items-center text-[rgb(var(--text-muted))] hover:text-[rgb(var(--accent))] transition-colors focus-ring rounded"
              >
                <Loader2 className="w-3.5 h-3.5" />
              </button>
              {unreadCount > 0 && (
                <button
                  onClick={() => markAllRead()}
                  className="inline-flex items-center gap-1 h-8 px-1.5 text-[11px] font-mono text-accent text-accent-hover transition-colors focus-ring rounded"
                >
                  <CheckCheck className="w-3.5 h-3.5" /> Mark all read
                </button>
              )}
            </div>
          </div>

          <div className="relative z-10 max-h-[380px] overflow-y-auto scroll-y">
            {loading ? (
              <div className="py-10 flex flex-col items-center gap-2 text-[rgb(var(--text-muted))]">
                <Loader2 className="w-5 h-5 animate-spin" />
                <span className="text-xs font-mono">Loading…</span>
              </div>
            ) : error ? (
              <div className="py-10 flex flex-col items-center gap-2 text-center px-4" role="alert">
                <AlertCircle className="w-5 h-5 text-[rgb(var(--danger))]" />
                <span className="text-xs text-[rgb(var(--danger))]">{error}</span>
              </div>
            ) : sorted.length === 0 ? (
              <div className="py-10 flex flex-col items-center gap-2 text-center px-4">
                <Inbox className="w-6 h-6 text-[rgb(var(--text-muted))]" />
                <span className="text-xs text-[rgb(var(--text-tertiary))]">You're all caught up.</span>
              </div>
            ) : (
              <ul className="divide-y divide-[rgb(var(--border-subtle))]">
                {sorted.map((n) => (
                  <li key={n.id}>
                    <div
                      role={n.link && TAB_FOR_LINK[n.link] ? 'button' : undefined}
                      tabIndex={n.link && TAB_FOR_LINK[n.link] ? 0 : undefined}
                      onClick={() => openNotification(n.id, n.link)}
                      onKeyDown={(e) => {
                        if (n.link && TAB_FOR_LINK[n.link] && (e.key === 'Enter' || e.key === ' ')) {
                          e.preventDefault()
                          void openNotification(n.id, n.link)
                        }
                      }}
                      className={`flex items-start gap-3 px-4 py-3 transition-colors hover:bg-[rgb(var(--surface))] ${n.is_read ? 'opacity-60' : ''} ${n.link && TAB_FOR_LINK[n.link] ? 'cursor-pointer focus-ring' : ''}`}
                    >
                      <span
                        className="w-7 h-7 shrink-0 grid place-items-center rounded-lg border"
                        style={TYPE_TINT[n.type] || TYPE_TINT.info}
                      >
                        {n.type === 'success' ? <Check className="w-3.5 h-3.5" />
                          : n.type === 'error' ? <AlertCircle className="w-3.5 h-3.5" />
                          : <Bell className="w-3.5 h-3.5" />}
                      </span>

                      <div className="min-w-0 flex-1">
                        <p className="text-sm font-medium leading-tight text-[rgb(var(--text-primary))] truncate">{n.title}</p>
                        <p className="mt-1 text-xs leading-relaxed text-[rgb(var(--text-secondary))] line-clamp-2">{n.message}</p>
                        <div className="mt-1.5 flex items-center gap-2 text-[10px] font-mono text-[rgb(var(--text-muted))]">
                          <span>{relativeTime(n.created_at)}</span>
                          {n.link && (
                            <span className="inline-flex items-center gap-1 text-[rgb(var(--accent-tertiary))] truncate">
                              <ExternalLink className="w-3 h-3" />{n.link}
                            </span>
                          )}
                        </div>
                      </div>

                      {!n.is_read && (
                        <button
                          onClick={(e) => { e.stopPropagation(); void markRead(n.id) }}
                          aria-label={`Mark "${n.title}" as read`}
                          className="shrink-0 w-11 h-11 -my-1 grid place-items-center rounded-lg bg-[rgb(var(--surface))] border border-[rgb(var(--border))] text-[rgb(var(--text-muted))] hover:text-[rgb(var(--accent))] hover:border-[rgb(var(--border-hover))] transition-colors focus-ring"
                        >
                          <Check className="w-3.5 h-3.5" />
                        </button>
                      )}
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      )}

      <ReminderModal open={remindersOpen} onClose={() => setRemindersOpen(false)} />
    </div>
  )
}
