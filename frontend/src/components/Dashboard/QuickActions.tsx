import React from 'react'
import { CheckSquare, Target, Activity, Calendar, BookOpen, DollarSign, ArrowUpRight, Sparkles } from 'lucide-react'

/**
 * Quick actions.
 *
 * Each entry navigates to an existing view that already owns its own creation
 * flow (each of these views renders an inline create form on mount). There is no
 * dashboard-side modal and no duplicated form here: the button either goes
 * somewhere real or it is not rendered.
 *
 * Reminders are deliberately absent — the app has no dedicated reminder view,
 * only the notification bell and a per-item modal — so no entry is offered for
 * it rather than offering a destination that does not exist.
 *
 * The per-entity tints that used to live here are gone. Six tiles cycling
 * jade → amber → cyan made the accent mean "one of six" rather than "primary
 * action", and each tile's coloured icon box put more colour on the page than
 * the attention list above it. The icons now inherit the row's own text colour,
 * which is one less per-component colour decision to keep in sync with the
 * tokens.
 */

interface QuickActionsProps {
  onNavigate: (route: string) => void
  onOpenCommandPalette?: () => void
}

interface QuickAction {
  label: string
  description: string
  route: string
  icon: React.ComponentType<{ className?: string }>
}

const QUICK_ACTIONS: QuickAction[] = [
  { label: 'Task', description: 'Capture something to do', route: 'tasks', icon: CheckSquare },
  { label: 'Goal', description: 'Define an objective', route: 'goals', icon: Target },
  { label: 'Habit', description: 'Start a routine', route: 'habits', icon: Activity },
  { label: 'Plan', description: 'Block out your day', route: 'planner', icon: Calendar },
  { label: 'Note', description: 'Write something down', route: 'notes', icon: BookOpen },
  { label: 'Finance', description: 'Record income or expense', route: 'finance', icon: DollarSign },
]

export const QuickActions: React.FC<QuickActionsProps> = ({ onNavigate, onOpenCommandPalette }) => {
  return (
    /* A compact utility surface, not a content card: this is a launcher, so it
       sits at level 2 behind the level-3 sections above it. Each tile keeps a
       40px touch target (section 20) but drops its filled background and icon
       box — six tinted boxes under a title read as a second dashboard. */
    <section aria-label="Quick actions" className="card-secondary p-6 stagger-in">
      <div className="section-header">
        <div className="min-w-0">
          <p className="section-header-label">
            <Sparkles className="w-3.5 h-3.5 !text-[rgb(var(--accent))]" />
            Create
          </p>
          <h2 className="section-header-title mt-2">Quick actions</h2>
        </div>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2 mt-4">
        {QUICK_ACTIONS.map((action, i) => (
          <button
            key={action.route}
            onClick={() => onNavigate(action.route)}
            className="flex flex-col items-start gap-2 p-3 min-h-[84px] rounded-lg bg-[rgb(var(--surface-4))] border border-[rgb(var(--border-subtle))] hover:bg-[rgb(var(--surface-hover))] hover:border-[rgb(var(--border-hover))] transition-colors duration-200 focus-ring stagger-in-fast text-left"
            style={{ animationDelay: `${i * 40}ms` }}
          >
            <action.icon className="w-[18px] h-[18px] text-[rgb(var(--text-secondary))]" aria-hidden="true" />
            <div className="min-w-0">
              <p className="typo-body-sm !text-[13px] !font-semibold !leading-tight">{action.label}</p>
              <p className="typo-meta mt-1 !text-[11px] !leading-snug">{action.description}</p>
            </div>
          </button>
        ))}
      </div>

      {onOpenCommandPalette && (
        <button onClick={onOpenCommandPalette} className="btn-secondary btn-sm w-full mt-3 focus-ring">
          Search everything <ArrowUpRight className="w-4 h-4" />
        </button>
      )}
    </section>
  )
}