import React from 'react'
import { AlertTriangle, ArrowRight, Calendar, CheckSquare, Target, Activity, Wallet } from 'lucide-react'
import { ILLUSTRATIVE_INSIGHTS } from './content'

/**
 * Hero product visual.
 *
 * This is a CSS/DOM composition, not an image and not WebGL — no canvas, no
 * video, no screenshot asset, so it costs a few hundred bytes rather than a
 * few hundred kilobytes and stays sharp at any density.
 *
 * Every string in it is a real output format from the backend: the attention
 * headline and detail come from `build_attention_summary`, and the insight
 * titles, details and action labels from `intelligence_rules_service`. So the
 * panel shows the shapes the product really produces rather than invented ones
 * — a visitor who signs in meets the same card set.
 *
 * The values shown are an example of one account's records, which is what any
 * product illustration is. It is deliberately not captioned as live data and
 * deliberately not dressed up as a screenshot of a specific person's account.
 *
 * Motion is a single staggered fade on mount. No loop, no parallax, no
 * continuous repaint.
 */

/**
 * Tones are the same semantic tokens the app itself uses, so the illustration
 * cannot drift away from the product it illustrates. Previously these were four
 * hard-coded Tailwind hues (rose/amber/cyan/emerald) which read fine in dark
 * mode and were invisible on the landing page's warm-white light background.
 */
const TONE_STYLES: Record<string, { icon: React.ElementType; token: string }> = {
  danger: { icon: AlertTriangle, token: '--danger' },
  warning: { icon: Target, token: '--warning' },
  info: { icon: Calendar, token: '--accent-tertiary' },
  neutral: { icon: Wallet, token: '--success' },
}

const toneTint = (token: string): React.CSSProperties => ({
  color: `rgb(var(${token}))`,
  backgroundColor: `rgb(var(${token}) / 0.1)`,
  borderColor: `rgb(var(${token}) / 0.25)`,
})

/** Small stat tile mirroring the dashboard's summary row. */
const Stat: React.FC<{ label: string; value: string; token: string }> = ({
  label,
  value,
  token,
}) => (
  <div className="rounded-xl border border-[rgb(var(--border-subtle))] bg-[rgb(var(--card))] px-3 py-2.5">
    <div className="font-display text-[15px] font-bold leading-none" style={{ color: `rgb(var(${token}))` }}>{value}</div>
    <div className="mono-xs mt-1.5 text-[rgb(var(--text-muted))]">{label}</div>
  </div>
)

export const HeroVisual: React.FC = () => {
  return (
    <figure className="relative m-0">
      {/* Restrained glow. Static, no pulse — it sits behind the frame and is
          blurred once by the compositor rather than animated. */}
      <div
        aria-hidden="true"
        className="pointer-events-none absolute -inset-8 -z-10 opacity-70"
        style={{
          background:
            'radial-gradient(ellipse 60% 50% at 50% 30%, rgb(var(--accent-tertiary) / 0.14), transparent 70%)',
        }}
      />

      <div className="card animate-fadeInUp overflow-hidden rounded-2xl">
        {/* Window chrome. Purely decorative, so it is hidden from the
            accessibility tree rather than read as app content. */}
        <div
          aria-hidden="true"
          className="flex items-center gap-2 border-b border-[rgb(var(--border))] bg-[rgb(var(--surface))] px-4 py-2.5"
        >
          <span className="h-2.5 w-2.5 rounded-full bg-[rgb(var(--border-strong))]" />
          <span className="h-2.5 w-2.5 rounded-full bg-[rgb(var(--border-strong))]" />
          <span className="h-2.5 w-2.5 rounded-full bg-[rgb(var(--border-strong))]" />
          <span className="mono-xs ml-2 truncate text-[rgb(var(--text-muted))]">
            AI-LifeOS — Command Center
          </span>
        </div>

        <div className="flex">
          {/* App rail. Mirrors MainLayout's navigation order. */}
          <div
            aria-hidden="true"
            className="hidden w-14 shrink-0 flex-col items-center gap-1 border-r border-[rgb(var(--border-subtle))] bg-[rgb(var(--bg-deep))] py-4 sm:flex"
          >
            {[CheckSquare, Target, Activity, Calendar, Wallet].map(
              (Icon, index) => (
                <span
                  key={index}
                  className={`grid h-9 w-9 place-items-center rounded-xl ${
                    index === 0
                      ? 'bg-[rgb(var(--accent-soft))] text-[rgb(var(--accent))]'
                      : 'text-[rgb(var(--text-muted))]'
                  }`}
                >
                  <Icon className="h-[18px] w-[18px]" />
                </span>
              ),
            )}
          </div>

          <div className="min-w-0 flex-1 p-4 sm:p-5">
            {/* Attention summary — real headline/detail strings. */}
            <div
              className="rounded-xl border p-3.5"
              style={{
                backgroundColor: 'rgb(var(--warning) / 0.07)',
                borderColor: 'rgb(var(--warning) / 0.25)',
              }}
            >
              <div className="flex items-start gap-2.5">
                <AlertTriangle
                  className="mt-0.5 h-4 w-4 shrink-0 text-[rgb(var(--warning))]"
                  aria-hidden="true"
                />
                <div className="min-w-0">
                  <p className="font-display text-[13px] font-semibold text-[rgb(var(--text-primary))]">
                    Several things need attention
                  </p>
                  <p className="body-xs mt-0.5 text-[rgb(var(--text-secondary))]">
                    3 overdue tasks, 12 open tasks in total.
                  </p>
                </div>
              </div>
            </div>

            {/* Insights. Real titles, details and action labels. */}
            <ul className="mt-3 flex flex-col gap-2">
              {ILLUSTRATIVE_INSIGHTS.map((insight, index) => {
                const tone = TONE_STYLES[insight.tone]
                const Icon = tone.icon

                return (
                  <li
                    key={insight.title}
                    className="animate-fadeInUp flex items-center gap-3 rounded-xl border border-[rgb(var(--border-subtle))] bg-[rgb(var(--card))] p-3"
                    style={{
                      animationDelay: `${180 + index * 90}ms`,
                      animationFillMode: 'both',
                    }}
                  >
                    <span
                      className="grid h-8 w-8 shrink-0 place-items-center rounded-lg border"
                      style={toneTint(tone.token)}
                    >
                      <Icon className="h-4 w-4" aria-hidden="true" />
                    </span>

                    <span className="min-w-0 flex-1">
                      <span className="block truncate font-display text-[12.5px] font-semibold text-[rgb(var(--text-primary))]">
                        {insight.title}
                      </span>
                      <span className="body-xs mt-0.5 block truncate text-[rgb(var(--text-tertiary))]">
                        {insight.detail}
                      </span>
                    </span>

                    <span className="mono-xs hidden shrink-0 items-center gap-1 whitespace-nowrap text-[rgb(var(--accent))] sm:inline-flex">
                      {insight.action}
                      <ArrowRight className="h-3 w-3" aria-hidden="true" />
                    </span>
                  </li>
                )
              })}
            </ul>

            {/* Summary row. */}
            <div className="mt-3 grid grid-cols-3 gap-2">
              <Stat label="Open tasks" value="12" token="--accent-tertiary" />
              <Stat label="Active goals" value="4" token="--accent-tertiary" />
              <Stat label="Best streak" value="21d" token="--accent" />
            </div>
          </div>
        </div>
      </div>

      <figcaption className="body-xs mt-4 text-center text-[rgb(var(--text-muted))]">
        The AI-LifeOS Command Center — your attention summary and the insights
        derived from your own records.
      </figcaption>
    </figure>
  )
}
