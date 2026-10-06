import React, { useMemo } from 'react'
import { CalendarDays, ArrowUpRight, AlertCircle, Clock, Sparkles } from 'lucide-react'
import { usePreferences } from '../../context/PreferencesContext'
import { formatLocalDateTime } from '../../utils/datetime'
import type { IntelligenceResponse, UpcomingItem, UpcomingKind } from '../../types'

/**
 * Today / Next.
 *
 * A focused view of the intelligence payload's `upcoming` list, which the
 * backend already merges and orders by due instant across tasks and the
 * planner. No re-prioritization happens here: the list arrives sorted, and the
 * only transformation applied is a cap for display.
 *
 * The ordering rule the backend used — overdue first, then due-soon, then
 * planned blocks — is a deterministic ordering over existing data, not a
 * generated score, so no AI judgment is introduced in the UI.
 */

const KIND_STYLES: Record<UpcomingKind, { chip: string; icon: React.ComponentType<{ className?: string }>; label: string }> = {
  overdue: {
    chip: 'bg-[rgb(var(--danger) / 0.12)] text-[rgb(var(--danger))] border-[rgb(var(--danger) / 0.3)]',
    icon: AlertCircle,
    label: 'Overdue',
  },
  due_soon: {
    chip: 'bg-[rgb(var(--warning) / 0.12)] text-[rgb(var(--warning))] border-[rgb(var(--warning) / 0.3)]',
    icon: Clock,
    label: 'Due soon',
  },
  planner_event: {
    chip: 'bg-[rgb(var(--accent-tertiary) / 0.12)] text-[rgb(var(--accent-tertiary))] border-[rgb(var(--accent-tertiary) / 0.3)]',
    icon: CalendarDays,
    label: 'Planned',
  },
  reminder: {
    chip: 'bg-[rgb(var(--accent) / 0.12)] text-[rgb(var(--accent))] border-[rgb(var(--accent) / 0.3)]',
    icon: Sparkles,
    label: 'Reminder',
  },
}

const MAX_ROWS = 6

interface TodayActionsProps {
  data: IntelligenceResponse
  onNavigate: (route: string) => void
}

export const TodayActions: React.FC<TodayActionsProps> = ({ data, onNavigate }) => {
  const { timezone, timeFormat } = usePreferences()

  const items = useMemo(() => data.upcoming.slice(0, MAX_ROWS), [data.upcoming])
  const remaining = Math.max(0, data.upcoming.length - MAX_ROWS)

  return (
    <section aria-label="Today and next" className="card-secondary p-6 stagger-in">
      <div className="section-header">
        <div className="min-w-0">
          <p className="section-header-label">
            <CalendarDays className="w-3.5 h-3.5 !text-[rgb(var(--accent))]" />
            Next up
          </p>
          <h2 className="section-header-title mt-2">Today &amp; next</h2>
        </div>
        {items.length > 0 && (
          <button
            onClick={() => onNavigate('tasks')}
            className="shrink-0 inline-flex items-center gap-1 text-[13px] font-medium text-accent text-accent-hover transition-colors focus-ring rounded"
          >
            All tasks
            <ArrowUpRight className="w-3.5 h-3.5" />
          </button>
        )}
      </div>

      {items.length === 0 ? (
        <EmptyToday onNavigate={onNavigate} hasData={data.has_data} />
      ) : (
        /* Rows share one container and are divided by hairlines. Each row used
           to be its own `card-interactive` — its own border, shadow, radius and
           lift-on-hover — so six upcoming items rendered as six boxes inside a
           seventh box. */
        <div className="row-stack mt-4">
          {items.map((item, i) => (
            <UpcomingRow
              key={item.id}
              item={item}
              index={i}
              timezone={timezone}
              timeFormat={timeFormat}
              onNavigate={onNavigate}
            />
          ))}
        </div>
      )}

      {remaining > 0 && (
        <button
          onClick={() => onNavigate('tasks')}
          className="btn-secondary btn-sm w-full mt-3 focus-ring"
        >
          {remaining} more coming up
        </button>
      )}
    </section>
  )
}

const UpcomingRow: React.FC<{
  item: UpcomingItem
  index: number
  timezone: string
  timeFormat: '12h' | '24h'
  onNavigate: (route: string) => void
}> = ({ item, index, timezone, timeFormat, onNavigate }) => {
  const meta = KIND_STYLES[item.kind] ?? KIND_STYLES.planner_event
  const Icon = meta.icon

  return (
    <button
      onClick={() => item.route && onNavigate(item.route)}
      disabled={!item.route}
      aria-label={`${meta.label}: ${item.title}`}
      className="row-item w-full text-left !cursor-pointer stagger-in-fast focus-ring disabled:cursor-default"
      style={{ animationDelay: `${index * 40}ms` }}
    >
      <span className={`w-9 h-9 shrink-0 grid place-items-center rounded-lg border ${meta.chip}`} aria-hidden="true">
        <Icon className="w-4 h-4" />
      </span>

      <div className="min-w-0 flex-1">
        <p className="typo-body-sm !text-[rgb(var(--text-primary))] !font-medium !leading-tight truncate">
          {item.title}
        </p>
        <div className="mt-1.5 flex flex-wrap items-center gap-x-2.5 gap-y-1">
          {/* The kind is a text label, not a second tinted pill. The row already
              carries the icon tile in the kind's own colour, so a matching
              coloured chip beside it doubled the signal on one 44px row. */}
          <span className="typo-micro !tracking-[0.1em]">{meta.label}</span>
          <span className="w-1 h-1 rounded-full bg-[rgb(var(--border-strong))]" aria-hidden="true" />
          <span className="text-[11px] font-mono text-[rgb(var(--text-tertiary))]">
            {formatLocalDateTime(item.due_at, timeFormat, timezone)}
          </span>
        </div>
      </div>

      {item.route && <ArrowUpRight className="w-4 h-4 text-[rgb(var(--text-muted))] shrink-0" aria-hidden="true" />}
    </button>
  )
}

const EmptyToday: React.FC<{ onNavigate: (route: string) => void; hasData: boolean }> = ({
  onNavigate,
  hasData,
}) => (
  <div className="text-center py-8">
    <p className="typo-body !font-medium">
      {hasData ? 'Nothing scheduled in the next 7 days' : 'Your day is wide open'}
    </p>
    <p className="typo-meta mt-1.5 max-w-[44ch] mx-auto mb-5">
      {hasData
        ? 'No overdue tasks, nothing due within three days, and no blocks in your planner. Add a due date to a task or schedule a block to fill this in.'
        : 'Add a task with a due date, or block out time in the planner. Anything upcoming shows up here automatically.'}
    </p>
    <div className="flex items-center justify-center gap-2 flex-wrap">
      <button onClick={() => onNavigate('tasks')} className="btn-secondary btn-sm focus-ring">
        Go to tasks <ArrowUpRight className="w-3.5 h-3.5" />
      </button>
      <button onClick={() => onNavigate('planner')} className="btn-secondary btn-sm focus-ring">
        Open planner <ArrowUpRight className="w-3.5 h-3.5" />
      </button>
    </div>
  </div>
)