import React, { useCallback, useEffect, useMemo, useState } from 'react'
import {
  AlertCircle,
  ArrowUpRight,
  Brain,
  CalendarDays,
  CheckCircle2,
  DollarSign,
  Loader2,
  RefreshCw,
  Target,
  TrendingDown,
  TriangleAlert,
} from 'lucide-react'
import { intelligenceService } from '../services/services'
import { usePreferences } from '../context/PreferencesContext'
import { extractErrorMessage } from '../utils/apiError'
import { formatLocalDateTime } from '../utils/datetime'
import type {
  Insight,
  InsightPriority,
  IntelligenceResponse,
  UpcomingItem,
} from '../types'

/**
 * LifeOS Intelligence.
 *
 * Everything rendered here arrives from `GET /intelligence`, derived from the
 * authenticated user's own persisted records. There is no local computation of
 * findings, no hardcoded sample data, and no placeholder text: an empty
 * account gets an empty state that says so, not a demo insight.
 *
 * Reuses the app's existing primitives (`card`, `btn-secondary`,
 * `focus-ring`, `font-display`, the token colours) rather than introducing a
 * second visual language. Animation is limited to the existing fade/stagger
 * utilities — no new keyframes, because this panel sits on the dashboard and
 * must stay cheap on an older laptop.
 *
 * Two modes, distinguished by whether a `data` prop is supplied:
 *
 *   - **Shared (dashboard).** `data` is passed in by the caller, which already
 *     fetched `/intelligence` for the whole command center. In this mode the
 *     panel makes no request of its own and renders *only* the low-priority
 *     Observations block. The attention summary, the needs-attention rows, the
 *     upcoming list and the finance block are all rendered by the dashboard's
 *     own sections (Right Now, Attention Center, Today & Next, Finance), so
 *     rendering them again here would duplicate them.
 *   - **Standalone.** No `data` prop: the panel fetches for itself and renders
 *     the complete view, unchanged from Phase 6.
 */

type IconComponent = React.ComponentType<{ className?: string }>

/**
 * Icon + token per insight type.
 *
 * These were eight distinct Tailwind hues — rose, sky, amber, violet, cyan,
 * orange, emerald, teal — which is why this panel read as a different product
 * from the rest of the dashboard. Nine kinds of finding genuinely do need to be
 * distinguishable, but the *label* under every row already carries the name, so
 * colour is a secondary cue, not the only one. The palette is therefore pulled
 * in to the semantic tokens: danger for overdue, warning for at-risk, the
 * accent family for the neutral-but-notable kinds.
 */
const tint = (token: string): React.CSSProperties => ({
  color: `rgb(var(${token}))`,
  backgroundColor: `rgb(var(${token}) / 0.1)`,
  borderColor: `rgb(var(${token}) / 0.28)`,
})

const TYPE_META: Record<string, { icon: IconComponent; token: string; label: string }> = {
  overdue: { icon: AlertCircle, token: '--danger', label: 'Overdue' },
  upcoming: { icon: CalendarDays, token: '--accent-tertiary', label: 'Upcoming' },
  goal_risk: { icon: Target, token: '--warning', label: 'Goal risk' },
  habit_consistency: { icon: TrendingDown, token: '--accent', label: 'Habits' },
  planning: { icon: CalendarDays, token: '--accent-tertiary', label: 'Planning' },
  task_load: { icon: TriangleAlert, token: '--warning', label: 'Load' },
  finance: { icon: DollarSign, token: '--success', label: 'Finance' },
  reminder: { icon: CheckCircle2, token: '--success', label: 'Reminders' },
  data_quality: { icon: Brain, token: '--text-tertiary', label: 'Setup' },
}

/** Border accent per priority. Colour only — no badge-count "score". */
const PRIORITY_ACCENT: Record<InsightPriority, string> = {
  high: 'rgb(var(--danger) / 0.75)',
  medium: 'rgb(var(--warning) / 0.65)',
  low: 'rgb(var(--border-strong))',
}

const LEVEL_STYLES: Record<string, { token: string }> = {
  clear: { token: '--success' },
  watch: { token: '--warning' },
  busy: { token: '--danger' },
}

// =========================================================
// Insight row
// =========================================================
const InsightRow: React.FC<{
  insight: Insight
  index: number
  onNavigate: (route: string) => void
}> = ({ insight, index, onNavigate }) => {
  const meta = TYPE_META[insight.type] ?? TYPE_META.data_quality
  const Icon = meta.icon

  return (
    <div
      className="relative pl-3 pr-3 py-3 rounded-xl bg-[rgb(var(--surface))] border border-[rgb(var(--border))] border-l-2 stagger-in-fast"
      style={{ animationDelay: `${index * 35}ms`, borderLeftColor: PRIORITY_ACCENT[insight.priority] }}
    >
      <div className="flex items-start gap-3">
        <span className="w-8 h-8 shrink-0 grid place-items-center rounded-lg border" style={tint(meta.token)}>
          <Icon className="w-4 h-4" />
        </span>

        <div className="min-w-0 flex-1">
          <div className="flex items-start justify-between gap-3">
            <p className="text-sm font-medium leading-tight text-[rgb(var(--text-primary))] truncate">{insight.title}</p>
            {insight.metric && (
              <span className="shrink-0 text-[11px] font-mono px-2 py-0.5 rounded-md bg-[rgb(var(--bg))] border border-[rgb(var(--border))] text-[rgb(var(--text-secondary))] max-w-[9rem] truncate">
                {insight.metric}
              </span>
            )}
          </div>

          {/* The explanation is the point of this layer — it says *why* the row
              exists, in counts and dates the user can check themselves. */}
          <p className="mt-1 text-xs leading-relaxed text-[rgb(var(--text-secondary))]">{insight.detail}</p>

          <div className="mt-2 flex items-center gap-3">
            <span className="text-[10px] font-mono uppercase tracking-widest text-[rgb(var(--text-muted))]">{meta.label}</span>
            {insight.route && insight.action_label && (
              <button
                onClick={() => onNavigate(insight.route as string)}
                className="inline-flex items-center gap-1 h-8 px-1 text-[11px] font-mono text-accent hover:underline focus-ring rounded"
              >
                {insight.action_label}
                <ArrowUpRight className="w-3 h-3" />
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

// =========================================================
// Upcoming row
// =========================================================
const UpcomingRow: React.FC<{
  item: UpcomingItem
  index: number
  timezone: string
  timeFormat: '12h' | '24h'
  onNavigate: (route: string) => void
}> = ({ item, index, timezone, timeFormat, onNavigate }) => {
  const kindTokens: Record<string, string> = {
    overdue: '--danger',
    due_soon: '--warning',
    planner_event: '--accent-tertiary',
  }

  const kindLabels: Record<string, string> = {
    overdue: 'Overdue',
    due_soon: 'Due soon',
    planner_event: 'Planned',
  }

  return (
    <div
      className="flex items-center justify-between gap-3 py-2.5 px-3 rounded-xl bg-[rgb(var(--surface))] border border-[rgb(var(--border))] stagger-in-fast"
      style={{ animationDelay: `${index * 30}ms` }}
    >
      <div className="flex items-center gap-3 min-w-0">
        <span
          className="shrink-0 text-[10px] font-mono px-2 py-0.5 rounded-md border"
          style={tint(kindTokens[item.kind] ?? '--accent-tertiary')}
        >
          {kindLabels[item.kind] ?? item.kind}
        </span>
        <span className="text-sm text-[rgb(var(--text-primary))] truncate">{item.title}</span>
      </div>

      <div className="flex items-center gap-2 shrink-0">
        <span className="text-[11px] font-mono text-[rgb(var(--text-tertiary))] hidden sm:inline">
          {formatLocalDateTime(item.due_at, timeFormat, timezone)}
        </span>
        {item.route && (
          <button
            onClick={() => onNavigate(item.route as string)}
            aria-label={`Open ${item.title}`}
            className="w-9 h-9 grid place-items-center rounded-lg text-[rgb(var(--text-muted))] hover:text-[rgb(var(--accent))] hover:bg-[rgb(var(--surface-hover))] transition-colors focus-ring"
          >
            <ArrowUpRight className="w-3.5 h-3.5" />
          </button>
        )}
      </div>
    </div>
  )
}

// =========================================================
// Empty state
// =========================================================
const EmptyState: React.FC<{ onNavigate: (route: string) => void }> = ({ onNavigate }) => (
  <div className="py-10 px-4 text-center">
    <span className="inline-grid place-items-center w-12 h-12 rounded-2xl bg-[rgb(var(--surface))] border border-[rgb(var(--border))] text-[rgb(var(--text-muted))] mb-3">
      <Brain className="w-6 h-6" />
    </span>
    <p className="text-sm font-medium text-[rgb(var(--text-primary))]">No insights yet</p>
    <p className="mt-1.5 text-xs leading-relaxed text-[rgb(var(--text-tertiary))] max-w-[42ch] mx-auto">
      Insights are derived from your own tasks, goals, habits, planner and finance records. Add your
      first task and this panel will summarise what needs attention.
    </p>
    <button
      onClick={() => onNavigate('tasks')}
      className="btn-secondary mt-4 h-10 px-4 inline-flex items-center gap-2 text-xs font-mono"
    >
      Go to tasks <ArrowUpRight className="w-3.5 h-3.5" />
    </button>
  </div>
)

// =========================================================
// Panel
// =========================================================
export const IntelligencePanel: React.FC<{
  setActiveTab: (tab: string) => void
  /** Supplied by the dashboard when it already owns the `/intelligence` fetch. */
  data?: IntelligenceResponse | null
}> = ({ setActiveTab, data: sharedData }) => {
  const { timezone, timeFormat } = usePreferences()
  const [ownData, setOwnData] = useState<IntelligenceResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // In shared mode the caller owns the request; this panel must not issue a
  // second one for the same payload.
  const isShared = sharedData !== undefined
  const data = isShared ? sharedData : ownData

  // Fetched once per mount and on explicit refresh — the same page-lifecycle
  // pattern the rest of the dashboard uses. No polling, no second global store.
  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      setOwnData(await intelligenceService.getOverview())
    } catch (e) {
      // Keep any previously loaded snapshot on screen; a failed refresh should
      // not blank out insights the user is already reading.
      setError(extractErrorMessage(e, 'Could not load intelligence.'))
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }, [])

  useEffect(() => {
    if (!isShared) load()
  }, [load, isShared])

  const refresh = useCallback(() => {
    setRefreshing(true)
    void load()
  }, [load])

  const handleNavigate = useCallback(
    (route: string) => {
      if (route) setActiveTab(route)
    },
    [setActiveTab],
  )

  const attentionInsights = useMemo(() => {
    if (!data) return []
    // Everything that is not a low-priority observation: the rows a user
    // should actually act on. Low-priority items (finance summary, streaks,
    // setup gaps) stay available below.
    return data.insights.filter((insight) => insight.priority !== 'low')
  }, [data])

  const observationInsights = useMemo(() => {
    if (!data) return []
    return data.insights.filter((insight) => insight.priority === 'low')
  }, [data])

  const level = data?.summary.level ?? 'clear'
  const levelStyle = LEVEL_STYLES[level] ?? LEVEL_STYLES.clear

  return (
    <div className="card p-6 stagger-in relative overflow-hidden">
      {/* One static wash instead of the old cyan→violet gradient overlay: the
          gradient could not survive a theme switch (cyan on ivory is
          unreadable) and it repainted the full card on every resize. */}
      <div
        className="absolute inset-0 pointer-events-none"
        style={{ background: 'radial-gradient(ellipse 70% 100% at 100% 0%, rgb(var(--accent) / 0.08) 0%, transparent 60%)' }}
      />

      <div className="relative z-10">
        {/* === HEADER === */}
        <div className="flex items-center justify-between gap-3 mb-5">
          <div className="flex items-center gap-2.5 min-w-0">
            <span className="w-8 h-8 shrink-0 grid place-items-center rounded-xl bg-[rgb(var(--accent)/0.1)] border border-[rgb(var(--accent)/0.28)] text-[rgb(var(--accent))]">
              <Brain className="w-4 h-4" />
            </span>
            <div className="min-w-0">
              <h3 className="font-display font-semibold text-base leading-none text-[rgb(var(--text-primary))]">
                LifeOS Intelligence
              </h3>
              <p className="mt-1 text-[11px] font-mono text-[rgb(var(--text-tertiary))] truncate">
                {data ? `Derived ${formatLocalDateTime(data.generated_at, timeFormat, timezone)}` : 'Analysing your data…'}
              </p>
            </div>
          </div>

          {/* Refresh lives here only when this panel owns the request. In shared
              mode the dashboard's "Right Now" refresh drives the whole page, and
              a second refresh button would be a dead control. */}
          {!isShared && (
            <button
              onClick={refresh}
              disabled={loading || refreshing}
              aria-label="Refresh intelligence"
              className="shrink-0 w-10 h-10 grid place-items-center rounded-xl bg-[rgb(var(--surface))] border border-[rgb(var(--border))] text-[rgb(var(--text-secondary))] hover:text-[rgb(var(--accent))] hover:border-[rgb(var(--border-hover))] transition-colors focus-ring disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
            </button>
          )}
        </div>

        {/* === LOADING === */}
        {loading && !data && (
          <div className="py-12 text-center">
            <Loader2 className="w-6 h-6 mx-auto mb-3 animate-spin text-[rgb(var(--accent))]" />
            {/* The spinner already conveys "working"; this line used to carry a
                second, independent pulse animation on top of it. */}
            <p className="text-sm font-mono text-[rgb(var(--text-tertiary))]">Deriving insights…</p>
          </div>
        )}

        {/* === ERROR === */}
        {!isShared && error && (
          <div role="alert" className="mb-5 px-4 py-3.5 rounded-xl border border-[rgb(var(--danger)/0.28)] bg-[rgb(var(--danger)/0.08)] flex items-center justify-between gap-3">
            <span className="flex items-center gap-2 text-sm text-[rgb(var(--danger))] min-w-0">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span className="truncate">{error}</span>
            </span>
            <button
              onClick={refresh}
              className="btn-secondary shrink-0 h-10 px-4 inline-flex items-center gap-2 text-xs font-mono"
            >
              Retry
            </button>
          </div>
        )}

        {/* === EMPTY — the dashboard has its own onboarding state, so this only
            applies to standalone use. === */}
        {!isShared && data && !data.has_data && !loading && (
          <EmptyState onNavigate={handleNavigate} />
        )}

        {/* === POPULATED === */}
        {data && data.has_data && (
          <div className="space-y-5">
            {/* Attention summary — dashboard renders this as "Right Now". */}
            {!isShared && (
            <div className="px-4 py-3.5 rounded-xl bg-[rgb(var(--surface))] border border-[rgb(var(--border))]">
              <div className="flex items-center gap-2.5">
                <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: `rgb(var(${levelStyle.token}))` }} />
                <span className="text-sm font-semibold" style={{ color: `rgb(var(${levelStyle.token}))` }}>
                  {data.summary.headline}
                </span>
              </div>
              <p className="mt-1.5 text-xs leading-relaxed text-[rgb(var(--text-secondary))]">{data.summary.detail}</p>

              <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-[11px] font-mono text-[rgb(var(--text-tertiary))]">
                <span>{data.summary.overdue_count} overdue</span>
                <span>{data.summary.due_soon_count} due soon</span>
                <span>{data.summary.incomplete_task_count} open</span>
                {data.summary.unread_notification_count > 0 && (
                  <span>{data.summary.unread_notification_count} unread</span>
                )}
              </div>
            </div>
            )}

            {/* Insights needing attention — dashboard renders this as the
                Attention Center. */}
            {!isShared && (
              <div>
                <h4 className="text-[11px] font-mono tracking-widest uppercase text-[rgb(var(--text-tertiary))] mb-2.5">
                  Needs attention
                </h4>
                {attentionInsights.length === 0 ? (
                  <p className="text-xs text-[rgb(var(--text-tertiary))] py-3">
                    Nothing needs attention right now.
                  </p>
                ) : (
                  <div className="space-y-2">
                    {attentionInsights.map((insight, i) => (
                      <InsightRow
                        key={insight.id}
                        insight={insight}
                        index={i}
                        onNavigate={handleNavigate}
                      />
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Upcoming — dashboard renders this as "Today & next". */}
            {!isShared && data.upcoming.length > 0 && (
              <div>
                <h4 className="text-[11px] font-mono tracking-widest uppercase text-[rgb(var(--text-tertiary))] mb-2.5">
                  Upcoming
                </h4>
                <div className="space-y-2">
                  {data.upcoming.map((item, i) => (
                    <UpcomingRow
                      key={item.id}
                      item={item}
                      index={i}
                      timezone={timezone}
                      timeFormat={timeFormat}
                      onNavigate={handleNavigate}
                    />
                  ))}
                </div>
              </div>
            )}

            {/* Observations (low priority) — the one block that no dashboard
                section covers, so it renders in both modes. */}
            {observationInsights.length > 0 && (
              <div>
                <h4 className="text-[11px] font-mono tracking-widest uppercase text-[rgb(var(--text-tertiary))] mb-2.5">
                  Observations
                </h4>
                <div className="space-y-2">
                  {observationInsights.map((insight, i) => (
                    <InsightRow
                      key={insight.id}
                      insight={insight}
                      index={i}
                      onNavigate={handleNavigate}
                    />
                  ))}
                </div>
              </div>
            )}

            {/* Finance — dashboard renders this as its own Finance section. */}
            {!isShared && data.finance && (
              <div className="px-4 py-3.5 rounded-xl bg-[rgb(var(--surface))] border border-[rgb(var(--border))]">
                <div className="flex items-center justify-between gap-3 mb-3">
                  <span className="text-[11px] font-mono tracking-widest uppercase text-[rgb(var(--text-tertiary))]">
                    Finance · {data.finance.period_start.slice(0, 7)}
                  </span>
                  <button
                    onClick={() => handleNavigate('finance')}
                    className="h-8 px-1 text-[11px] font-mono text-accent hover:underline focus-ring rounded"
                  >
                    Open →
                  </button>
                </div>
                <div className="grid grid-cols-3 gap-3">
                  <div>
                    <p className="text-[10px] font-mono text-[rgb(var(--text-tertiary))]">Income</p>
                    <p className="mt-1 font-mono text-sm text-[rgb(var(--success))]">{data.finance.income_total}</p>
                  </div>
                  <div>
                    <p className="text-[10px] font-mono text-[rgb(var(--text-tertiary))]">Expenses</p>
                    <p className="mt-1 font-mono text-sm text-[rgb(var(--danger))]">{data.finance.expense_total}</p>
                  </div>
                  <div>
                    <p className="text-[10px] font-mono text-[rgb(var(--text-tertiary))]">Entries</p>
                    <p className="mt-1 font-mono text-sm text-[rgb(var(--text-primary))]">{data.finance.transaction_count}</p>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

export default IntelligencePanel