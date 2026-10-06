import React from 'react'
import { RefreshCw, AlertCircle, Loader2 } from 'lucide-react'
import { formatLocalDateTime } from '../../utils/datetime'
import { usePreferences } from '../../context/PreferencesContext'
import type { IntelligenceResponse } from '../../types'

/**
 * Right Now.
 *
 * The first thing the dashboard answers: *what is happening in my life right
 * now*. Every number, and the headline itself, comes from the backend's own
 * `AttentionSummary` — the object the Phase 6 rule engine derived on this same
 * request — so this section restates a single derived verdict rather than
 * recomputing one on the client.
 *
 * The freshness line reports `generated_at`, the instant the backend built the
 * snapshot, so stale data is distinguishable from live data.
 *
 * Visual note: the old hero stacked two `blur-3xl` orbs on a 60px grid layer
 * driven by `gridMove` (a `background-position` animation that repaints the
 * whole panel, every frame, forever). That is the single most expensive thing in
 * the dashboard. It is replaced here with one static radial wash — depth from
 * gradient, not from motion.
 */

// Only the dot carries severity; the label beside it stays neutral.
const LEVEL_STYLES: Record<string, { dot: string }> = {
  clear: { dot: 'status-dot-success' },
  watch: { dot: 'status-dot-warning' },
  busy: { dot: 'status-dot-danger' },
}

interface RightNowSummaryProps {
  data: IntelligenceResponse | null
  loading: boolean
  refreshing: boolean
  error: string | null
  onRefresh: () => void
}

export const RightNowSummary: React.FC<RightNowSummaryProps> = ({
  data,
  loading,
  refreshing,
  error,
  onRefresh,
}) => {
  const { timezone, timeFormat } = usePreferences()
  const level = data?.summary.level ?? 'clear'
  const style = LEVEL_STYLES[level] ?? LEVEL_STYLES.clear

  const firstLoad = loading && !data

  // Only counts the backend already placed in the summary object. Nothing here
  // is aggregated from the goals/habits/finance lists on the client.
  const summary = data?.summary
  const tiles = summary
    ? [
        { label: 'overdue', value: summary.overdue_count, tone: 'text-[rgb(var(--danger))]' },
        { label: 'due soon', value: summary.due_soon_count, tone: 'text-[rgb(var(--warning))]' },
        { label: 'open', value: summary.incomplete_task_count, tone: 'text-[rgb(var(--accent-tertiary))]' },
        { label: 'unread', value: summary.unread_notification_count, tone: 'text-[rgb(var(--accent))]' },
      ]
    : []

  // The verdict chip is now a bare micro label beside a status dot rather than a
  // filled, bordered pill. A tinted pill put the same severity colour on the
  // chrome as on the figures, so a "busy" state stained the whole header row;
  // the dot alone carries severity and the label stays neutral.
  const chipText = error
    ? 'Backend unreachable'
    : firstLoad
      ? 'Synchronizing…'
      : (summary?.headline ?? 'Synchronizing…')

  return (
    <section
      aria-label="Right now"
      className="card-hero p-6 md:p-8 stagger-in"
    >
      {/* One static wash. No blur filter, no animation, no repaint. */}
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          background:
            'radial-gradient(ellipse 70% 90% at 100% 0%, rgb(var(--accent) / 0.09) 0%, transparent 60%)',
        }}
      />

      <div className="relative z-10 flex flex-col lg:flex-row lg:items-start lg:justify-between gap-6 lg:gap-8">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <span className="section-header-label !m-0 !p-0">
              {error ? (
                <AlertCircle className="w-3.5 h-3.5 !text-[rgb(var(--danger))]" />
              ) : firstLoad ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <span className={`status-dot ${style.dot}`} />
              )}
              {chipText}
            </span>

            {data && (
              <button
                onClick={onRefresh}
                disabled={loading || refreshing}
                aria-label="Refresh your LifeOS summary"
                className="btn-icon focus-ring disabled:cursor-not-allowed"
              >
                <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
              </button>
            )}
          </div>

          {/* The headline is the page's one real H1. It sits above the label in
              visual weight even though the label reads first in the DOM, which
              is what makes "what matters now" legible in under two seconds. */}
          <h1 className="typo-display mt-3 !text-[30px] md:!text-[36px]">
            Right now
          </h1>

          <p className="typo-body mt-3 max-w-[58ch]">
            {error
              ? error
              : data
                ? data.summary.detail
                : 'Reading your tasks, goals, habits, schedule and finance from your LifeOS.'}
          </p>

          {data && (
            <p className="typo-micro mt-4 !tracking-wide !normal-case !font-normal">
              Derived {formatLocalDateTime(data.generated_at, timeFormat, timezone)}
              {error && ' · showing the last snapshot'}
            </p>
          )}
        </div>

        {/* Metric rail, not four boxes.
            The old version wrapped each figure in its own bordered, filled
            tile, so the four counts competed with the headline instead of
            supporting it. Hairline-separated figures on the hero's own surface
            read as one measurement set, and a zero drops to muted grey so a
            non-zero value is the only thing the eye lands on. */}
        {tiles.length > 0 && (
          <dl className="grid grid-cols-4 gap-px shrink-0 lg:w-[21rem] lg:pt-1 bg-[rgb(var(--border-subtle))] rounded-xl overflow-hidden border border-[rgb(var(--border-subtle))]">
            {tiles.map((tile) => (
              <div key={tile.label} className="bg-[rgb(var(--surface-3))] px-2 py-3.5 text-center">
                <dd
                  className={`typo-numeric text-[26px] font-bold leading-none ${
                    tile.value > 0 ? tile.tone : 'text-[rgb(var(--text-muted))]'
                  }`}
                >
                  {tile.value}
                </dd>
                <dt className="typo-micro mt-2 !tracking-[0.12em] !text-[9px]">{tile.label}</dt>
              </div>
            ))}
          </dl>
        )}
      </div>
    </section>
  )
}

/**
 * Placeholder that mirrors the live panel's geometry, so the page does not jump
 * when the first payload lands. No API call and no fabricated figures.
 */
export const RightNowSkeleton: React.FC = () => (
  <div
    aria-hidden="true"
    className="card-hero p-6 md:p-8"
  >
    <div className="relative z-10 flex flex-col lg:flex-row lg:items-start lg:justify-between gap-6 lg:gap-8">
      <div className="min-w-0 flex-1">
        <div className="skeleton h-3 w-40" />
        <div className="skeleton mt-4 h-9 w-48" />
        <div className="skeleton mt-4 h-4 w-full max-w-[52ch]" />
        <div className="skeleton mt-2 h-4 w-64" />
      </div>
      <div className="grid grid-cols-4 gap-2 shrink-0 lg:w-[21rem]">
        {[0, 1, 2, 3].map((i) => (
          <div key={i} className="skeleton h-[4.75rem]" />
        ))}
      </div>
    </div>
  </div>
)