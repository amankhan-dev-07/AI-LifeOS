import React, { useMemo } from 'react'
import { Calendar, ArrowUpRight, AlertTriangle } from 'lucide-react'
import { usePreferences } from '../../context/PreferencesContext'
import { toZonedDateKey, dateKeyOfNaive, formatTimeOnly } from '../../utils/datetime'
import type { IntelligenceResponse, UpcomingItem } from '../../types'

/**
 * Planner.
 *
 * Reads the `planner_event` entries out of the intelligence `upcoming` list —
 * the same records the Planner view manages — and splits them into "today" and
 * "later" against the user's own timezone.
 *
 * This is a read of existing planner data, not a second calendar. Nothing here
 * creates, edits or moves a block; every row navigates to the Planner view,
 * which owns that.
 */

const MAX_TODAY = 5

interface PlannerTodayProps {
  data: IntelligenceResponse
  onNavigate: (route: string) => void
}

export const PlannerToday: React.FC<PlannerTodayProps> = ({ data, onNavigate }) => {
  const { timezone } = usePreferences()

  const { todayKey, events } = useMemo(() => {
    const key = toZonedDateKey(new Date(), timezone)
    const plannerItems = data.upcoming.filter((item) => item.kind === 'planner_event')
    return { todayKey: key, events: plannerItems }
  }, [data.upcoming, timezone])

  // Which day a planner block belongs to.
  //
  // The Planner writes `start_time` as a wall-clock time in the user's zone,
  // persisted verbatim (`dateKey + "T09:00"`) with no UTC conversion — the same
  // convention `dateKeyOfNaive` exists to read without re-parsing through the
  // local zone. Grouping those through `new Date(...)` would instead treat the
  // string as UTC and shift it by the machine's offset, moving an evening block
  // onto the following day. So the day is read from the stored date part, then
  // compared against today in the user's own zone.
  const split = useMemo(() => {
    const today: UpcomingItem[] = []
    const later: UpcomingItem[] = []

    events.forEach((item) => {
      if (dateKeyOfNaive(item.due_at) === todayKey) today.push(item)
      else later.push(item)
    })

    return { today, later }
  }, [events, todayKey])

  // Whether the schedule is overloaded is the rule engine's call, not the
  // dashboard's. It is read from the `planning` insight, and the rule's own
  // wording is used verbatim, so the threshold stays the one defined in Phase 6
  // rather than a second copy drifting out of sync.
  const busyDetail = data.insights.find(
    (insight) => insight.type === 'planning' && insight.priority !== 'low'
  )?.detail

  return (
    <section aria-label="Today's plan" className="card-secondary p-6 stagger-in">
      <div className="section-header">
        <div className="min-w-0">
          <p className="section-header-label">
            <Calendar className="w-3.5 h-3.5 !text-[rgb(var(--accent-tertiary))]" />
            {split.today.length} block{split.today.length !== 1 ? 's' : ''} today
          </p>
          <h2 className="section-header-title mt-2">Today&rsquo;s plan</h2>
        </div>
        <button
          onClick={() => onNavigate('planner')}
          className="shrink-0 inline-flex items-center gap-1 text-[13px] font-medium text-accent text-accent-hover transition-colors focus-ring rounded"
        >
          Planner
          <ArrowUpRight className="w-3.5 h-3.5" />
        </button>
      </div>

      {busyDetail && split.today.length > 0 && (
        <p className="mt-3 flex items-start gap-1.5 text-[11px] leading-snug text-[rgb(var(--warning))]" title={busyDetail}>
          <AlertTriangle className="w-3.5 h-3.5 mt-px shrink-0" aria-hidden="true" />
          <span className="min-w-0">{busyDetail}</span>
        </p>
      )}

      {split.today.length === 0 ? (
        <Empty onNavigate={onNavigate} hasEvents={events.length > 0} />
      ) : (
        /* TIME-LED ROWS: the start time is the largest element on each row, set
           in tabular figures down the left gutter, with the block title beside
           it. The previous layout put an icon tile first and the time as small
           metadata, so a list of blocks read as a list of items rather than as a
           timeline — which is the one thing this panel exists to communicate. */
        <div className="mt-4">
          {split.today.slice(0, MAX_TODAY).map((item, i) => (
            <PlannerRow key={item.id} item={item} index={i} onNavigate={onNavigate} />
          ))}
        </div>
      )}

      {split.today.length > MAX_TODAY && (
        <button
          onClick={() => onNavigate('planner')}
          className="btn-secondary btn-sm w-full mt-3 focus-ring"
        >
          {split.today.length - MAX_TODAY} more blocks today
        </button>
      )}

      {split.later.length > 0 && (
        <div className="mt-4 pt-4 border-t border-[rgb(var(--border-subtle))] flex items-center justify-between gap-3">
          <span className="typo-micro !tracking-[0.12em]">
            {split.later.length} block{split.later.length !== 1 ? 's' : ''} coming up
          </span>
          <button
            onClick={() => onNavigate('planner')}
            className="inline-flex items-center gap-1 text-[13px] font-medium text-[rgb(var(--accent))] hover:text-[rgb(var(--accent-hover))] transition-colors focus-ring rounded"
          >
            See the week
            <ArrowUpRight className="w-3.5 h-3.5" />
          </button>
        </div>
      )}
    </section>
  )
}

const PlannerRow: React.FC<{
  item: UpcomingItem
  index: number
  onNavigate: (route: string) => void
}> = ({ item, index, onNavigate }) => (
  <button
    onClick={() => onNavigate('planner')}
    className="w-full text-left flex items-center gap-3 py-2.5 stagger-in-fast focus-ring group"
    style={{ animationDelay: `${index * 45}ms` }}
  >
    {/* Fixed-width time gutter. `border-l` on the hour side gives the column a
        single vertical rule running down the panel, so the times line up
        without each row needing its own box. */}
    <span className="typo-numeric shrink-0 w-[3.25rem] pl-3 border-l-2 border-l-[rgb(var(--border))] group-hover:border-l-[rgb(var(--accent))] transition-colors text-[15px] font-semibold leading-none text-[rgb(var(--text-primary))]">
      {formatTimeOnly(item.due_at)}
    </span>

    <span className="min-w-0 flex-1">
      <span className="block typo-body-sm !font-medium !leading-tight !text-[rgb(var(--text-primary))] truncate">
        {item.title}
      </span>
      <span className="block mt-1 text-[11px] font-mono text-[rgb(var(--text-muted))]">
        {dateKeyOfNaive(item.due_at)}
      </span>
    </span>

    <ArrowUpRight className="w-4 h-4 text-[rgb(var(--text-muted))] shrink-0 group-hover:text-[rgb(var(--accent))] transition-colors" aria-hidden="true" />
  </button>
)

const Empty: React.FC<{ onNavigate: (route: string) => void; hasEvents: boolean }> = ({
  onNavigate,
  hasEvents,
}) => (
  <div className="text-center py-8">
    <p className="typo-body !font-medium">
      {hasEvents ? 'Nothing scheduled today' : 'No planner blocks yet'}
    </p>
    <p className="typo-meta mt-1.5 max-w-[42ch] mx-auto mb-5">
      {hasEvents
        ? 'Your next blocks are later in the week. Open the planner to review the full schedule.'
        : 'Block out time for a task, a habit, or a focus session. Blocks you schedule appear here and in your upcoming list.'}
    </p>
    <button onClick={() => onNavigate('planner')} className="btn-secondary btn-sm focus-ring">
      Open planner <ArrowUpRight className="w-3.5 h-3.5" />
    </button>
  </div>
)