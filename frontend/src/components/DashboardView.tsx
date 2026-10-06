import React, { useCallback, useEffect, useState } from 'react'
import { Cpu, Brain, Calendar, CheckSquare, Target, Activity } from 'lucide-react'
import { intelligenceService } from '../services/services'
import { extractErrorMessage } from '../utils/apiError'
import { useAuth } from '../context/AuthContext'
import { IntelligencePanel } from './IntelligencePanel'
import {
  RightNowSummary,
  RightNowSkeleton,
  AttentionCenter,
  TodayActions,
  GoalProgress,
  HabitConsistency,
  PlannerToday,
  FinanceSnapshot,
  QuickActions,
  EmptyOnboarding,
} from './Dashboard'
import type { IntelligenceResponse } from '../types'

/**
 * AI-LifeOS Command Center.
 *
 * Ordering is by operational priority, not by novelty: what is happening now →
 * what needs attention → what is next → the domains behind it (goals, habits,
 * plan, money) → the standing observations Phase 6 derived.
 *
 * Data flow: this component is the single owner of the `/intelligence` request.
 * It fetches once per mount and on explicit refresh — the page-lifecycle pattern
 * the rest of the app uses, with no polling and no new global store — and hands
 * the resulting `IntelligenceResponse` to every section as a prop. Sections
 * never fetch, so mounting the dashboard issues exactly one request, and
 * identity is decided by the bearer token on that request alone: no user id is
 * read from the frontend or sent as a query parameter.
 *
 * Every visible control either navigates to an existing view or triggers the
 * single refresh above. Nothing here is decorative-only.
 */
export const DashboardView: React.FC<{
  setActiveTab: (tab: string) => void
  onOpenCommandPalette?: () => void
}> = ({ setActiveTab, onOpenCommandPalette }) => {
  const { user } = useAuth()
  const [data, setData] = useState<IntelligenceResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      setData(await intelligenceService.getOverview())
    } catch (e) {
      // Keep the last good snapshot on screen: a failed refresh should not blank
      // out a dashboard the user is in the middle of reading.
      setError(extractErrorMessage(e, 'Could not load your LifeOS summary.'))
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  const refresh = useCallback(() => {
    setRefreshing(true)
    void load()
  }, [load])

  // Only the "Right Now" header — greet the person, don't invent a persona.
  const greeting = (user?.name ?? '').trim()

  if (!loading && !data && error) {
    return (
      <div className="space-y-6 animate-fadeInUp">
        <LoadError error={error} onRetry={refresh} />
      </div>
    )
  }

  if (loading && !data) {
    return (
      <div className="space-y-6 animate-fadeInUp">
        <RightNowSkeleton />
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 h-64 card skeleton" />
          <div className="h-64 card skeleton" />
        </div>
      </div>
    )
  }

  // A brand-new account has no records anywhere. Showing a wall of zeroes would
  // be worse than useless, so this is an orientation instead of a report.
  if (data && !data.has_data) {
    return (
      <div className="space-y-6 animate-fadeInUp">
        <EmptyOnboarding onNavigate={setActiveTab} />
        <QuickActions onNavigate={setActiveTab} onOpenCommandPalette={onOpenCommandPalette} />
      </div>
    )
  }

  if (!data) return null

  return (
    <div className="space-y-8 lg:space-y-10 animate-fadeInUp">
      <RightNowSummary
        data={data}
        loading={loading}
        refreshing={refreshing}
        error={error}
        onRefresh={refresh}
      />

      {error && (
        <div className="card-secondary px-4 py-3.5 border-l-2 !border-l-[rgb(var(--danger))] flex items-center justify-between gap-3 stagger-in">
          <span className="flex items-center gap-2 text-sm text-[rgb(var(--danger))] min-w-0">
            <span className="truncate">{error}</span>
          </span>
          <button onClick={refresh} className="btn-secondary btn-sm shrink-0 focus-ring">
            Retry
          </button>
        </div>
      )}

      {/* Group 1 — Decide. Attention triage and what is next are the only two
          sections given the wide column, and they sit directly under the hero
          so the page's answer is reachable without scrolling. */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <AttentionCenter data={data} onNavigate={setActiveTab} />
          <TodayActions data={data} onNavigate={setActiveTab} />
        </div>

        {/* Group 2 — Orient. The domains that shape the above, in one column
            so they read as context rather than as three more decisions. */}
        <div className="space-y-6">
          <PlannerToday data={data} onNavigate={setActiveTab} />
          <HabitConsistency data={data} onNavigate={setActiveTab} />
          <FinanceSnapshot finance={data.finance} onNavigate={setActiveTab} />
        </div>
      </div>

      {/* Group 3 — Progress. Full width, once, so the three domains below read
          as one band of steady state rather than competing with triage above. */}
      <GoalProgress data={data} onNavigate={setActiveTab} />

      {/* Phase 6's own panel, in shared mode: it renders only the low-priority
          observations that none of the sections above covers, and reuses this
          component's payload instead of fetching a second copy. */}
      <IntelligencePanel setActiveTab={setActiveTab} data={data} />

      <QuickActions onNavigate={setActiveTab} onOpenCommandPalette={onOpenCommandPalette} />

      <AIStatusPanel setActiveTab={setActiveTab} connected={!error} greeting={greeting} />
    </div>
  )
}

const LoadError: React.FC<{ error: string; onRetry: () => void }> = ({ error, onRetry }) => (
  <div className="card-secondary p-6 flex flex-col sm:flex-row sm:items-center justify-between gap-4 stagger-in">
    <div className="min-w-0">
      <h2 className="section-header-title">Your LifeOS summary could not be loaded</h2>
      <p className="typo-body mt-1.5 break-words">{error}</p>
    </div>
    <button onClick={onRetry} className="btn-primary shrink-0 focus-ring">
      Try again
    </button>
  </div>
)

/**
 * AI status.
 *
 * This is a reachability indicator, not a health check: it reports whether the
 * last request the dashboard made succeeded, and offers the two views a user
 * most often wants next. There is no "model", "engine", or provider concept
 * here — LifeOS Intelligence is deterministic and runs without any LLM, so a
 * "neural core" badge with a fake status would be a lie.
 *
 * The status dot is static. A 2-second opacity pulse on a static value — the
 * value only changes when the user hits refresh — animates forever while
 * communicating nothing, so it is now a plain dot that changes colour.
 */
const AIStatusPanel: React.FC<{
  setActiveTab: (tab: string) => void
  connected: boolean
  greeting: string
}> = ({ setActiveTab, connected, greeting }) => {
  const links: { label: string; icon: React.ComponentType<{ className?: string }>; tab: string }[] = [
    { label: 'Tasks', icon: CheckSquare, tab: 'tasks' },
    { label: 'Planner', icon: Calendar, tab: 'planner' },
    { label: 'Goals', icon: Target, tab: 'goals' },
    { label: 'Habits', icon: Activity, tab: 'habits' },
    { label: 'AI Brain', icon: Cpu, tab: 'ai' },
  ]

  return (
    /* A footer band rather than another card. This panel reports *how* the
       numbers above were produced — it is provenance, not a section of content,
       so it sits on the page surface behind a hairline instead of claiming the
       same weight as the attention list. */
    <div className="card-plain border-t border-[rgb(var(--border-subtle))] pt-6 stagger-in">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-start gap-2.5 min-w-0">
          <Brain className="w-4 h-4 mt-0.5 shrink-0 text-[rgb(var(--accent))]" aria-hidden="true" />
          <div className="min-w-0">
            <h3 className="typo-label !text-[rgb(var(--text-primary))]">Intelligence engine</h3>
            <p className="typo-meta mt-1 !text-xs max-w-[68ch]">
              {connected
                ? `Every figure on this page was derived from your own records just now, by rules — not generated by a language model.${
                    greeting ? ` Welcome back, ${greeting}.` : ''
                  }`
                : 'The last read did not reach the backend. Figures shown are from the previous snapshot.'}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <span
            className={`status-dot ${connected ? 'status-dot-success' : 'status-dot-danger'}`}
            aria-hidden="true"
          />
          <span className="typo-micro !tracking-[0.14em]">{connected ? 'Online' : 'Offline'}</span>
        </div>
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-2">
        {links.map(({ label, icon: Icon, tab }) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className="inline-flex items-center gap-1.5 h-8 px-3 rounded-lg text-[12px] font-medium text-[rgb(var(--text-secondary))] bg-[rgb(var(--surface-3))] border border-[rgb(var(--border-subtle))] hover:text-[rgb(var(--text-primary))] hover:border-[rgb(var(--border-hover))] transition-colors duration-200 focus-ring"
          >
            <Icon className="w-3.5 h-3.5" />
            {label}
          </button>
        ))}
      </div>
    </div>
  )
}