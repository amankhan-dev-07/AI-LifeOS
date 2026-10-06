import React, { useEffect, useState } from 'react'
import { useAuth } from './context/AuthContext'
import { usePreferences } from './context/PreferencesContext'
import { MainLayout } from './layouts/MainLayout'
import { DashboardView } from './components/DashboardView'
import { TasksView } from './components/TasksView'
import { GoalsView } from './components/GoalsView'
import { HabitsView } from './components/HabitsView'
import { AICommandView } from './components/AICommandView'
import { PlannerView } from './components/PlannerView'
import { NotesView } from './components/NotesView'
import { FinanceView } from './components/FinanceView'
import { ProfileView } from './components/ProfileView'
import { SettingsView } from './components/SettingsView'
import { CommandPalette } from './components/CommandPalette'
import { OnboardingFlow } from './components/OnboardingFlow'

/**
 * The authenticated application.
 *
 * This is the body of the old `App.tsx`, unchanged — every view, the command
 * palette, the onboarding gate and the tab routing behave exactly as they did
 * in Phase 1–8. It was moved here, not rewritten, so that it can sit behind a
 * `React.lazy` boundary: `/` then loads none of it, and in particular none of
 * `three`.
 *
 * Its auth gate now lives one level up in `RequireAuth`; the `isLoading` branch
 * below is therefore only reachable during a logout in flight.
 */
const AppAuthenticated: React.FC = () => {
  const { isAuthenticated, isLoading } = useAuth()
  const { onboardingCompleted, loaded: prefsLoaded } = usePreferences()
  const [activeTab, setActiveTab] = useState('dashboard')
  const [commandPaletteOpen, setCommandPaletteOpen] = useState(false)

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault()
        if (isAuthenticated) setCommandPaletteOpen(v => !v)
      }
      if (e.key === 'Escape') setCommandPaletteOpen(false)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [isAuthenticated])

  if (isLoading) {
    return (
      <div className="min-h-screen shell-bg flex items-center justify-center p-8">
        <div className="flex flex-col items-center gap-4">
          <div className="w-12 h-12 rounded-2xl bg-[rgb(var(--accent))] flex items-center justify-center">
            <span className="w-2 h-2 rounded-full bg-[rgb(var(--text-inverse))]" />
          </div>
          <p className="text-sm font-mono tracking-widest text-[rgb(var(--text-tertiary))]">LOADING YOUR WORKSPACE…</p>
          <div className="h-1 w-32 rounded-full bg-[rgb(var(--border))] overflow-hidden">
            <div className="h-full w-1/2 bg-[rgb(var(--accent))] rounded-full animate-shimmer" />
          </div>
        </div>
      </div>
    )
  }

  // The first-time flow. Gated on the persisted server flag alone — no
  // `has_data` check, because a user who registered before Phase 8 and never
  // onboarded would otherwise be stranded, and `DashboardView` already renders
  // `EmptyOnboarding` for an account with no records, so an onboarded-but-empty
  // user still lands somewhere useful.
  if (!prefsLoaded) {
    return (
      <div className="min-h-screen shell-bg flex items-center justify-center p-8">
        <div className="flex flex-col items-center gap-4">
          <div className="w-12 h-12 rounded-2xl bg-[rgb(var(--accent))] flex items-center justify-center">
            <span className="w-2 h-2 rounded-full bg-[rgb(var(--text-inverse))]" />
          </div>
          <p className="text-sm font-mono tracking-widest text-[rgb(var(--text-tertiary))]">LOADING YOUR SETTINGS…</p>
        </div>
      </div>
    )
  }

  if (!onboardingCompleted) {
    return <OnboardingFlow onComplete={() => window.location.reload()} />
  }

  // One element, reused by both the dashboard case and the fallback, so
  // returning to an unknown tab cannot mount a second command center.
  const dashboardView = (
    <DashboardView
      setActiveTab={setActiveTab}
      onOpenCommandPalette={() => setCommandPaletteOpen(true)}
    />
  );

  const renderView = () => {
    switch (activeTab) {
      case 'dashboard': return dashboardView;
      case 'tasks': return <TasksView />;
      case 'goals': return <GoalsView />;
      case 'habits': return <HabitsView />;
      case 'ai': return <AICommandView />;
      case 'planner': return <PlannerView />;
      case 'notes': return <NotesView />;
      case 'finance': return <FinanceView />;
      case 'profile': return <ProfileView />;
      case 'settings': return <SettingsView />;
      default: return dashboardView;
    }
  }

  return (
    <>
      <MainLayout activeTab={activeTab} setActiveTab={setActiveTab} onOpenCommandPalette={() => setCommandPaletteOpen(true)}>
        <div className="animate-fadeIn">{renderView()}</div>
      </MainLayout>
      <CommandPalette isOpen={commandPaletteOpen} onClose={() => setCommandPaletteOpen(false)} setActiveTab={setActiveTab} />
    </>
  )
}

export default AppAuthenticated
