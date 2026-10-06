import React from 'react'
import { Sparkles, CheckSquare, Target, Activity, Calendar, ArrowUpRight, Cpu, Brain } from 'lucide-react'

interface EmptyOnboardingProps {
  onNavigate: (route: string) => void
}

/**
 * First-run state for an account with no data at all.
 *
 * The previous version of this screen carried two `blur-3xl` orbs on an
 * infinite float plus a floating logo tile. Three 64px-blur layers animating
 * forever on an otherwise empty page is the most expensive thing the dashboard
 * ever rendered, and none of it carried information. It is replaced by one
 * static radial wash — painted once, never repainted.
 */

const FIRST_ACTIONS = [
  {
    title: 'Create your first task',
    description: 'Capture something you need to do. Tasks drive your attention center and daily plan.',
    route: 'tasks',
    icon: CheckSquare,
    tint: 'bg-[rgb(var(--accent) / 0.12)] border-[rgb(var(--accent) / 0.3)] text-[rgb(var(--accent))]',
  },
  {
    title: 'Define a goal',
    description: 'Set the objective your tasks and habits serve. Goals give your work direction.',
    route: 'goals',
    icon: Target,
    tint: 'bg-[rgb(var(--accent-secondary) / 0.12)] border-[rgb(var(--accent-secondary) / 0.3)] text-[rgb(var(--accent-secondary))]',
  },
  {
    title: 'Plan your day',
    description: 'Block out time in the planner. A structured schedule beats an open calendar.',
    route: 'planner',
    icon: Calendar,
    tint: 'bg-[rgb(var(--accent-tertiary) / 0.12)] border-[rgb(var(--accent-tertiary) / 0.3)] text-[rgb(var(--accent-tertiary))]',
  },
  {
    title: 'Start a habit',
    description: 'Pick one routine to track. Streaks build momentum that compounds over time.',
    route: 'habits',
    icon: Activity,
    tint: 'bg-[rgb(var(--accent) / 0.12)] border-[rgb(var(--accent) / 0.3)] text-[rgb(var(--accent))]',
  },
]

export const EmptyOnboarding: React.FC<EmptyOnboardingProps> = ({ onNavigate }) => {
  return (
    <div className="space-y-6 animate-fadeInUp">
      {/* === HERO === */}
      <div className="relative overflow-hidden rounded-2xl border border-[rgb(var(--border))] p-6 md:p-8 card stagger-in">
        {/* One static ambient wash. No blur filter, no animation, no repaint. */}
        <div
          className="absolute inset-0 pointer-events-none"
          style={{
            background:
              'radial-gradient(ellipse 70% 90% at 85% 0%, rgb(var(--accent) / 0.10) 0%, transparent 60%)',
          }}
        />

        <div className="relative z-10 flex flex-col md:flex-row md:items-center gap-6">
          <div className="w-16 h-16 shrink-0 rounded-2xl bg-[rgb(var(--accent) / 0.14)] border border-[rgb(var(--accent) / 0.3)] grid place-items-center">
            <Sparkles className="w-8 h-8 text-[rgb(var(--accent))]" />
          </div>

          <div className="min-w-0">
            <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded-full border text-xs font-medium bg-[rgb(var(--accent) / 0.12)] border-[rgb(var(--accent) / 0.3)] text-[rgb(var(--accent))] mb-3">
              <Sparkles className="w-3.5 h-3.5" />
              Welcome
            </div>
            <h1 className="font-display font-bold tracking-tight text-[28px] md:text-[32px] leading-tight text-[rgb(var(--text-primary))]">
              Your LifeOS is ready.
            </h1>
            <p className="mt-3 text-sm leading-relaxed text-[rgb(var(--text-secondary))] max-w-[62ch]">
              AI-LifeOS turns your tasks, goals, habits, schedule, and finances into one operational
              picture — then tells you what needs attention. It&rsquo;s empty right now because you
              haven&rsquo;t added anything yet. Start with one of the actions below and this
              dashboard comes alive.
            </p>
          </div>
        </div>
      </div>

      {/* === WHAT THIS IS === */}
      <div className="card p-6 stagger-in" style={{ animationDelay: '60ms' }}>
        <div className="flex items-center gap-2.5 mb-4">
          <span className="w-10 h-10 grid place-items-center rounded-xl bg-[rgb(var(--accent) / 0.12)] border border-[rgb(var(--accent) / 0.3)] text-[rgb(var(--accent))]">
            <Brain className="w-4 h-4" />
          </span>
          <h2 className="font-display font-semibold text-base text-[rgb(var(--text-primary))]">
            What this dashboard does
          </h2>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          {[
            {
              title: 'Right now',
              body: 'A compact summary of what is happening in your life today.',
            },
            {
              title: 'Needs attention',
              body: 'Overdue work, goal risks, and habit gaps surfaced for you.',
            },
            {
              title: 'What next',
              body: 'A prioritized list of the most immediately actionable items.',
            },
          ].map((item, i) => (
            <div
              key={item.title}
              className="p-3.5 rounded-xl bg-[rgb(var(--surface) / 0.6)] border border-[rgb(var(--border))] stagger-in-fast"
              style={{ animationDelay: `${i * 50}ms` }}
            >
              <p className="text-xs font-semibold text-[rgb(var(--text-primary))] mb-1">{item.title}</p>
              <p className="text-[11px] leading-relaxed text-[rgb(var(--text-secondary))]">{item.body}</p>
            </div>
          ))}
        </div>
      </div>

      {/* === FIRST ACTIONS === */}
      <div className="card p-6 stagger-in" style={{ animationDelay: '120ms' }}>
        <div className="flex items-center gap-2.5 mb-4">
          <span className="w-10 h-10 grid place-items-center rounded-xl bg-[rgb(var(--accent) / 0.12)] border border-[rgb(var(--accent) / 0.3)] text-[rgb(var(--accent))]">
            <Cpu className="w-4 h-4" />
          </span>
          <h2 className="font-display font-semibold text-base text-[rgb(var(--text-primary))]">Start here</h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {FIRST_ACTIONS.map((action, i) => (
            <button
              key={action.route}
              onClick={() => onNavigate(action.route)}
              className="flex items-start gap-3 p-4 rounded-xl bg-[rgb(var(--surface) / 0.6)] border border-[rgb(var(--border))] hover:bg-[rgb(var(--surface-hover) / 0.7)] hover:border-[rgb(var(--border-hover))] transition-colors duration-200 focus-ring stagger-in-fast text-left group"
              style={{ animationDelay: `${i * 50}ms` }}
            >
              <span className={`w-10 h-10 shrink-0 grid place-items-center rounded-xl border ${action.tint}`}>
                <action.icon className="w-5 h-5" />
              </span>
              <div className="min-w-0 flex-1">
                <p className="text-sm font-semibold text-[rgb(var(--text-primary))] leading-tight">
                  {action.title}
                </p>
                <p className="text-xs text-[rgb(var(--text-secondary))] leading-relaxed mt-1">
                  {action.description}
                </p>
              </div>
              <ArrowUpRight className="w-4 h-4 text-[rgb(var(--text-tertiary))] shrink-0 opacity-0 group-hover:opacity-100 group-hover:text-[rgb(var(--accent))] transition-colors duration-200" />
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}