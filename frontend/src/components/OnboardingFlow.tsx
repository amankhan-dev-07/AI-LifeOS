import React, { useCallback, useState } from 'react'
import {
  Sparkles,
  CheckSquare,
  Target,
  Calendar,
  Activity,
  Brain,
  ArrowRight,
  X,
  CheckCircle2,
  Loader2,
  Zap,
  StickyNote,
  BellRing,
  Wallet,
} from 'lucide-react'
import { taskService, goalService, habitService, plannerService } from '../services/services'
import { extractErrorMessage } from '../utils/apiError'
import { usePreferences } from '../context/PreferencesContext'

/**
 * Two steps, deliberately.
 *
 * A separate "you're done" page existed here first and was removed: it only
 * restated what step 2's confirmation list already said, and every CTA on it
 * performed the same single action as the button that had just been pressed —
 * a dead-end screen. Finishing is now the last button on step 2.
 */
type OnboardingStep = 'welcome' | 'first-action'

interface CreatedItem {
  type: 'task' | 'goal' | 'habit' | 'planner'
  title: string
}

/**
 * The domains AI-LifeOS actually manages, in plain language.
 *
 * Every entry here is a view that exists in the app and persists to the
 * backend — there is no aspirational capability on this list. Each icon is
 * distinct, because two domains sharing an icon made the grid read as a
 * rendering bug rather than a list.
 */
const tint = (token: string): React.CSSProperties => ({
  color: `rgb(var(${token}))`,
  backgroundColor: `rgb(var(${token}) / 0.1)`,
  borderColor: `rgb(var(${token}) / 0.28)`,
})

/**
 * Seven domains each got their own Tailwind hue, which is what made this grid
 * read as a swatch chart rather than a list. The icon and the label already
 * carry the identity, so colour is pulled in to the semantic tokens: the accent
 * family for the everyday surfaces, warning/danger only where the domain is
 * genuinely about something going wrong or nagging you.
 */
const DOMAINS = [
  { key: 'task', label: 'Tasks', icon: CheckSquare, token: '--accent-tertiary', desc: 'Things to do, with priority and due dates' },
  { key: 'goal', label: 'Goals', icon: Target, token: '--accent-tertiary', desc: 'Objectives with progress you can watch move' },
  { key: 'habit', label: 'Habits', icon: Activity, token: '--accent', desc: 'Routines you track for streaks and consistency' },
  { key: 'planner', label: 'Planner', icon: Calendar, token: '--accent', desc: 'Your day, blocked into time instead of left open' },
  { key: 'note', label: 'Notes', icon: StickyNote, token: '--warning', desc: 'Written context, linkable to goals and tasks' },
  { key: 'finance', label: 'Finance', icon: Wallet, token: '--success', desc: 'Income and expenses, summarised per month' },
  { key: 'reminder', label: 'Reminders', icon: BellRing, token: '--danger', desc: 'Nudges on a task, habit or plan block' },
]

/**
 * What the Intelligence layer does, stated as facts rather than promises.
 *
 * The wording is deliberately concrete and rule-based. "Autonomous agent" and
 * similar framings are avoided outright: every figure on the dashboard comes
 * from deterministic rules over the user's own rows, so anything implying a
 * model deciding or acting would be a claim the product cannot back.
 */
const INTELLIGENCE_EXPLANATION = [
  'Flags overdue work and what is coming up next',
  'Warns when a goal is slipping against its target date',
  'Shows where habit streaks have broken',
  'Builds a daily plan from your tasks and habits',
  'Sums income and spending for the month',
  'Counts and dates, not guesses — you can check every one of them',
]

export const OnboardingFlow: React.FC<{
  onComplete: () => void
}> = ({ onComplete }) => {
  const { completeOnboarding } = usePreferences()
  const [step, setStep] = useState<OnboardingStep>('welcome')
  const [createdItems, setCreatedItems] = useState<CreatedItem[]>([])
  const [creating, setCreating] = useState<CreatedItem['type'] | null>(null)
  const [finishing, setFinishing] = useState(false)
  const [error, setError] = useState<string | null>(null)

  /**
   * Persist the completion flag, then hand control back.
   *
   * The write is awaited before `onComplete` so the server has actually
   * recorded the decision before the app is allowed to move on. Otherwise a
   * fast click could navigate away and race the PATCH, and the user would be
   * shown this flow again on their next visit. A failed write surfaces the
   * error rather than letting them through, because a completion that did not
   * persist is worse than a visible error.
   */
  const finish = useCallback(async () => {
    setFinishing(true)
    setError(null)

    try {
      await completeOnboarding()
      onComplete()
    } catch (e) {
      setError(extractErrorMessage(e, 'Could not save your setup. Please try again.'))
      setFinishing(false)
    }
  }, [completeOnboarding, onComplete])

  const handleSkip = useCallback(async () => {
    await finish()
  }, [finish])

  const handleNext = useCallback(() => {
    setStep('first-action')
  }, [])

  const handleCreateTask = useCallback(async () => {
    setCreating('task')
    setError(null)
    try {
      const task = await taskService.createTask({
        title: 'Review PR #42',
        priority: 'high',
        estimated_minutes: 30,
      })
      setCreatedItems(prev => [...prev, { type: 'task', title: task.title }])
    } catch (e) {
      setError(extractErrorMessage(e, 'Could not create task.'))
    } finally {
      setCreating(null)
    }
  }, [])

  const handleCreateGoal = useCallback(async () => {
    setCreating('goal')
    setError(null)
    try {
      const goal = await goalService.createGoal({
        title: 'Learn React patterns',
        category: 'study',
        progress: 0,
      })
      setCreatedItems(prev => [...prev, { type: 'goal', title: goal.title }])
    } catch (e) {
      setError(extractErrorMessage(e, 'Could not create goal.'))
    } finally {
      setCreating(null)
    }
  }, [])

  const handleCreateHabit = useCallback(async () => {
    setCreating('habit')
    setError(null)
    try {
      const habit = await habitService.createHabit({
        title: 'Walk 30 minutes',
        frequency: 'daily',
      })
      setCreatedItems(prev => [...prev, { type: 'habit', title: habit.title }])
    } catch (e) {
      setError(extractErrorMessage(e, 'Could not create habit.'))
    } finally {
      setCreating(null)
    }
  }, [])

  const handleCreateEvent = useCallback(async () => {
    setCreating('planner')
    setError(null)
    try {
      // A real planner block, created through the same endpoint PlannerView
      // uses — filed under today at 09:00–10:00. The Planner's own modal is
      // deliberately not reused here: it owns its own overlay and closing it
      // would race this flow's unmount.
      const today = new Date().toISOString().slice(0, 10)

      const event = await plannerService.createEvent({
        title: 'Morning focus block',
        event_date: `${today}T00:00:00`,
        start_time: `${today}T09:00:00`,
        end_time: `${today}T10:00:00`,
        event_type: 'focus_block',
      })
      setCreatedItems(prev => [...prev, { type: 'planner', title: event.title }])
    } catch (e) {
      setError(extractErrorMessage(e, 'Could not create planner block.'))
    } finally {
      setCreating(null)
    }
  }, [])

  const handleFinish = useCallback(async () => {
    await finish()
  }, [finish])

  const renderStep = () => {
    switch (step) {
      case 'welcome':
        return (
          <div className="space-y-6 animate-fadeInUp max-w-xl mx-auto">
            {/* Hero */}
            <div className="relative overflow-hidden rounded-2xl card p-6 md:p-8 stagger-in">
              {/* This panel previously carried two `blur-3xl` orbs on infinite
                  float animations plus a floating logo tile — 64px blur layers
                  animating forever on the very first screen a new user sees. */}
              <div
                className="absolute inset-0 pointer-events-none"
                style={{ background: 'radial-gradient(ellipse 70% 90% at 85% 0%, rgb(var(--accent) / 0.12) 0%, transparent 60%)' }}
              />

              <div className="relative z-10 text-center">
                <div className="w-16 h-16 mx-auto rounded-2xl bg-[rgb(var(--accent)/0.12)] border border-[rgb(var(--accent)/0.28)] grid place-items-center mb-4">
                  <Sparkles className="w-8 h-8 text-[rgb(var(--accent))]" />
                </div>

                {/* Not "Your LifeOS is ready" — that headline belongs to
                    EmptyOnboarding, and reusing it here made the first-run
                    welcome read as though something had already happened. */}
                <h1 className="font-display font-bold tracking-tight text-[26px] md:text-[32px] leading-tight text-[rgb(var(--text-primary))]">
                  Your personal operating system for daily life.
                </h1>

                <p className="mt-4 text-sm leading-relaxed text-[rgb(var(--text-secondary))] max-w-[62ch] mx-auto">
                  AI-LifeOS brings your tasks, goals, habits, schedule, notes and finances into one
                  place — then shows you what needs attention, using your own records.
                </p>
              </div>
            </div>

            {/* What it manages */}
            <div className="card p-6 stagger-in" style={{ animationDelay: '60ms' }}>
              <div className="flex items-center gap-2.5 mb-4">
                <span className="w-8 h-8 grid place-items-center rounded-xl bg-[rgb(var(--accent-tertiary)/0.1)] border border-[rgb(var(--accent-tertiary)/0.28)] text-[rgb(var(--accent-tertiary))]">
                  <CheckSquare className="w-4 h-4" />
                </span>
                <h2 className="section-header-title">What it manages</h2>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {DOMAINS.map((domain, i) => {
                  const Icon = domain.icon
                  return (
                    <div
                      key={domain.key}
                      className="p-3.5 rounded-xl bg-[rgb(var(--surface))] border border-[rgb(var(--border))] stagger-in-fast"
                      style={{ animationDelay: `${i * 50}ms` }}
                    >
                      <div className="flex items-center gap-2.5 mb-2">
                        <span className="w-8 h-8 grid place-items-center rounded-xl border" style={tint(domain.token)}>
                          <Icon className="w-4 h-4" />
                        </span>
                        <p className="typo-label">{domain.label}</p>
                      </div>
                      <p className="typo-body-sm pl-10 text-[rgb(var(--text-tertiary))] leading-relaxed">{domain.desc}</p>
                    </div>
                  )
                })}
              </div>
            </div>

            {/* Intelligence */}
            <div className="card p-6 stagger-in" style={{ animationDelay: '120ms' }}>
              <div className="flex items-center gap-2.5 mb-4">
                <span className="w-8 h-8 grid place-items-center rounded-xl bg-[rgb(var(--accent)/0.1)] border border-[rgb(var(--accent)/0.28)] text-[rgb(var(--accent))]">
                  <Brain className="w-4 h-4" />
                </span>
                <h2 className="section-header-title">What makes it different</h2>
              </div>

              <div className="space-y-2">
                {INTELLIGENCE_EXPLANATION.map((item, i) => (
                  <div
                    key={item}
                    className="flex items-center gap-2.5 p-2.5 rounded-lg bg-[rgb(var(--surface))] border border-[rgb(var(--border))] stagger-in-fast"
                    style={{ animationDelay: `${i * 40}ms` }}
                  >
                    <span className="w-5 h-5 shrink-0 grid place-items-center rounded-lg bg-[rgb(var(--success)/0.1)] border border-[rgb(var(--success)/0.28)] text-[rgb(var(--success))]">
                      <CheckCircle2 className="w-3 h-3" />
                    </span>
                    <p className="typo-body-sm text-[rgb(var(--text-secondary))] leading-relaxed">{item}</p>
                  </div>
                ))}
              </div>
            </div>

            {/* Step 1 CTA */}
            <button
              onClick={handleNext}
              className="btn-primary w-full h-11 rounded-xl inline-flex items-center justify-center gap-2 text-sm font-semibold stagger-in"
              style={{ animationDelay: '180ms' }}
            >
              Show me how to start
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        )

      case 'first-action':
        return (
          <div className="space-y-6 animate-fadeInUp max-w-xl mx-auto">
            <div className="card p-6 stagger-in">
              <div className="flex items-center gap-2.5 mb-4">
                <span className="w-8 h-8 grid place-items-center rounded-xl bg-[rgb(var(--accent-tertiary)/0.1)] border border-[rgb(var(--accent-tertiary)/0.28)] text-[rgb(var(--accent-tertiary))]">
                  <Zap className="w-4 h-4" />
                </span>
                <h2 className="font-display font-semibold text-base text-[rgb(var(--text-primary))]">Start with one thing</h2>
              </div>

              <p className="text-sm text-[rgb(var(--text-secondary))] mb-4">
                Create your first item and the dashboard comes alive. Pick what matters most right now:
              </p>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-4">
                {([
                  { type: 'task', Icon: CheckSquare, token: '--accent-tertiary', title: 'Create a Task', desc: '"Review PR #42" — high priority, 30 min' },
                  { type: 'goal', Icon: Target, token: '--accent-tertiary', title: 'Create a Goal', desc: '"Learn React patterns" — study category' },
                  { type: 'habit', Icon: Activity, token: '--accent', title: 'Start a Habit', desc: '"Walk 30 minutes" — daily frequency' },
                  { type: 'planner', Icon: Calendar, token: '--accent', title: 'Block Out Time', desc: '"Morning focus block" — today, 09:00–10:00' },
                ] as const).map(({ type, Icon, token, title, desc }) => {
                  const handlers = {
                    task: handleCreateTask,
                    goal: handleCreateGoal,
                    habit: handleCreateHabit,
                    planner: handleCreateEvent,
                  } as const
                  const busy = creating === type

                  return (
                    <button
                      key={type}
                      onClick={handlers[type]}
                      disabled={creating !== null}
                      className="flex items-start gap-3 p-4 rounded-xl bg-[rgb(var(--surface))] border border-[rgb(var(--border))] hover:bg-[rgb(var(--surface-hover))] hover:border-[rgb(var(--border-hover))] transition-colors focus-ring text-left group disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      <span
                        className="relative w-10 h-10 shrink-0 grid place-items-center rounded-xl border"
                        style={busy
                          ? { color: `rgb(var(${token}))`, backgroundColor: `rgb(var(${token}) / 0.2)`, borderColor: `rgb(var(${token}) / 0.4)` }
                          : tint(token)}
                      >
                        <Icon className="w-5 h-5" />
                        {busy && <Loader2 className="absolute w-5 h-5 animate-spin" />}
                      </span>
                      <div className="min-w-0 flex-1">
                        <p className="typo-body !font-semibold !leading-tight text-[rgb(var(--text-primary))]">{title}</p>
                        <p className="typo-body-sm mt-1 text-[rgb(var(--text-tertiary))] leading-relaxed">{desc}</p>
                      </div>
                    </button>
                  )
                })}
              </div>

              {error && (
                <div role="alert" className="mt-4 px-4 py-3 rounded-xl bg-[rgb(var(--danger)/0.08)] border border-[rgb(var(--danger)/0.28)] text-[rgb(var(--danger))] text-sm animate-scaleIn">
                  {error}
                </div>
              )}
            </div>

            {/* The way out. Deliberately a SIBLING of the card above rather
                than a child of it.

                Creating is encouraged but never required, so a user who would
                rather explore on their own still needs a forward path that is
                not the destructive-sounding Skip. */}
            <div className="space-y-4">
              {createdItems.length > 0 && (
                <div className="card p-6">
                  <p className="text-xs font-mono text-[rgb(var(--text-tertiary))] mb-2">Created so far:</p>
                  <div className="space-y-1.5">
                    {createdItems.map((item, i) => (
                      <div
                        key={`${item.type}-${i}`}
                        className="flex items-center gap-2 p-2 rounded-lg bg-[rgb(var(--surface))] border border-[rgb(var(--border))] stagger-in-fast"
                        style={{ animationDelay: `${i * 50}ms` }}
                      >
                        <CheckCircle2 className="w-3.5 h-3.5 text-[rgb(var(--success))] shrink-0" />
                        <span className="text-xs text-[rgb(var(--text-secondary))] truncate">{item.title}</span>
                        <span className="text-[10px] font-mono text-[rgb(var(--text-muted))] ml-auto shrink-0">{item.type}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <button
                onClick={handleFinish}
                disabled={finishing || creating !== null}
                className="btn-primary w-full h-11 rounded-xl inline-flex items-center justify-center gap-2 text-sm font-semibold disabled:opacity-60 disabled:cursor-not-allowed"
              >
                {finishing ? <Loader2 className="w-4 h-4 animate-spin" /> : <ArrowRight className="w-4 h-4" />}
                {finishing ? 'Saving…' : createdItems.length > 0 ? 'Continue' : "I'll do this later"}
              </button>
            </div>
          </div>
        )

      default:
        return null
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-start sm:items-center justify-center p-4 bg-[rgb(var(--bg-deep))] overflow-y-auto"
      role="dialog"
      aria-modal="true"
      aria-labelledby="onboarding-title"
    >
      {/* Background atmosphere — static. The old version carried a 95%-opacity
          `backdrop-blur-sm` over the whole viewport, which blurred everything
          behind a full-screen overlay for the entire duration of onboarding. */}
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          background: `
            radial-gradient(ellipse 80% 60% at 20% -10%, rgb(var(--accent-tertiary) / 0.12) 0%, transparent 50%),
            radial-gradient(ellipse 60% 50% at 90% 10%, rgb(var(--accent) / 0.12) 0%, transparent 50%),
          `
        }}
      />

      {/* `items-start` on small screens plus this max-height keeps the primary
          action inside the viewport on a phone; centring a tall card on a short
          screen is what pushed buttons below the fold. */}
      <div className="relative z-10 w-full max-w-2xl my-auto max-h-none sm:max-h-[90vh] sm:overflow-y-auto">
        {/* Header with skip */}
        <div className="flex items-center justify-between gap-3 mb-6">
          <div className="flex items-center gap-2.5 min-w-0">
            <span className="w-8 h-8 shrink-0 grid place-items-center rounded-xl bg-[rgb(var(--accent)/0.1)] border border-[rgb(var(--accent)/0.28)] text-[rgb(var(--accent))]">
              <Sparkles className="w-4 h-4" />
            </span>
            <h2 id="onboarding-title" className="typo-h3">Welcome to AI-LifeOS</h2>
          </div>

          <button
            onClick={handleSkip}
            disabled={creating !== null || finishing}
            className="btn-secondary shrink-0 h-10 px-4 inline-flex items-center gap-2 text-xs font-mono disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {finishing ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <X className="w-3.5 h-3.5" />}
            <span className="hidden sm:inline">{finishing ? 'Saving…' : 'Skip'}</span>
          </button>
        </div>

        {/* Progress indicator — labelled, so the dots are not the only cue that
            this is a two-step sequence. */}
        <div className="flex items-center gap-3 mb-6">
          {(['welcome', 'first-action'] as const).map((s, i) => {
            const currentIndex = (['welcome', 'first-action'] as const).indexOf(step)
            const reached = currentIndex >= i

            return (
              <div key={s} className="flex items-center gap-3">
                <div className="flex items-center gap-2">
                  <span
                    aria-hidden="true"
                    className={`w-2 h-2 rounded-full transition-colors ${
                      reached ? 'bg-[rgb(var(--accent))]' : 'bg-[rgb(var(--border-strong))]'
                    }`}
                  />
                  <span
                    className={`typo-micro transition-colors ${
                      reached ? 'text-[rgb(var(--text-secondary))]' : 'text-[rgb(var(--text-muted))]'
                    }`}
                  >
                    {i === 0 ? 'Understand' : 'First action'}
                  </span>
                </div>
                {i === 0 && <div className="w-8 h-0.5 bg-[rgb(var(--border-strong))]" />}
              </div>
            )
          })}
        </div>

        {/* Step content */}
        <div className="animate-fadeInUp">
          {renderStep()}
        </div>
      </div>
    </div>
  )
}

export default OnboardingFlow