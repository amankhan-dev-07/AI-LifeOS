import React, { useEffect, useState } from 'react'
import { Settings, Bell, Palette, Save, ShieldCheck, Monitor, Loader2, AlertCircle, Clock, Globe, Sparkles } from 'lucide-react'
import { usePreferences } from '../context/PreferencesContext'
import { isValidTimezone, normalizeTimeFormat, normalizeTimezone } from '../utils/datetime'
import { extractErrorMessage } from '../utils/apiError'
import type { UserPreferences } from '../types'

type Draft = Pick<UserPreferences, 'theme' | 'daily_briefing_enabled' | 'security_alerts_enabled' | 'planner_start_hour' | 'timezone' | 'time_format'>

const TIMEZONES = [
  'UTC',
  'America/Los_Angeles',
  'America/Denver',
  'America/Chicago',
  'America/New_York',
  'Europe/London',
  'Europe/Berlin',
  'Asia/Dubai',
  'Asia/Kolkata',
  'Asia/Singapore',
  'Asia/Tokyo',
  'Australia/Sydney',
]

const HOUR_LABELS = Array.from({ length: 24 }, (_, hour) => ({
  value: hour,
  label: `${String(hour).padStart(2, '0')}:00`,
}))

const ToggleRow: React.FC<{
  title: string
  description: string
  checked: boolean
  onChange: (v: boolean) => void
  icon?: React.ReactNode
  disabled?: boolean
}> = ({ title, description, checked, onChange, icon, disabled }) => (
  <label className="flex items-center justify-between gap-4 p-4 rounded-xl bg-[rgb(var(--surface-3))] border border-[rgb(var(--border))] cursor-pointer">
    <div className="flex items-center gap-2">
      {icon}
      <div>
        <p className="text-sm font-medium text-[rgb(var(--text-primary))]">{title}</p>
        <p className="text-xs text-[rgb(var(--text-tertiary))]">{description}</p>
      </div>
    </div>
    <input
      type="checkbox"
      checked={checked}
      disabled={disabled}
      onChange={(e) => onChange(e.target.checked)}
      className="w-5 h-5 shrink-0 rounded border-[rgb(var(--border-strong))] bg-[rgb(var(--card))] text-[rgb(var(--accent))] accent-[rgb(var(--accent))] focus-ring disabled:opacity-50"
    />
  </label>
)

export const SettingsView: React.FC = () => {
  const { preferences, theme, loading, saving, error, updatePreferences } = usePreferences()
  const [draft, setDraft] = useState<Draft | null>(null)
  const [saved, setSaved] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)
  const [restarting, setRestarting] = useState(false)

  /**
   * Re-arm the first-time flow.
   *
   * Clearing the persisted flag is what makes the walkthrough reappear: `App`
   * reads `onboardingCompleted` from the server and renders `OnboardingFlow`
   * when it is false. A reload is deliberate rather than lazy — it guarantees
   * the flow mounts with fresh preferences rather than relying on the current
   * tree to react to the flag flipping.
   */
  const restartSetup = async () => {
    setRestarting(true)
    setSaveError(null)

    try {
      await updatePreferences({ onboarding_completed: false })
      window.location.reload()
    } catch (err) {
      setSaveError(extractErrorMessage(err, 'Could not reopen the setup walkthrough.'))
      setRestarting(false)
    }
  }

  // Seed the editable draft from the server-loaded preferences. The backend
  // remains the source of truth; this is only the form buffer.
  useEffect(() => {
    if (!preferences) return
    setDraft({
      theme: preferences.theme === 'light' ? 'light' : 'dark',
      daily_briefing_enabled: preferences.daily_briefing_enabled,
      security_alerts_enabled: preferences.security_alerts_enabled,
      planner_start_hour: preferences.planner_start_hour,
      // Same normalization the rest of the app and the backend apply, so the
      // form never seeds itself with a value the save call would reject.
      timezone: normalizeTimezone(preferences.timezone),
      // Normalised rather than cast: a row written before the column existed
      // can still arrive as an unexpected string, and the rest of the app
      // treats anything that isn't '12h' as 24-hour.
      time_format: normalizeTimeFormat(preferences.time_format),
    })
  }, [preferences])

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!draft) return

    setSaveError(null)

    // Caught here rather than round-tripped to the backend: the timezone is
    // selected from a fixed list, so an invalid value only ever means a stale
    // or corrupted stored value, and the safe resolution is the default.
    const timezone = normalizeTimezone(draft.timezone)
    if (timezone !== draft.timezone) {
      setDraft(d => (d ? { ...d, timezone } : d))
    }

    try {
      await updatePreferences({ ...draft, timezone })
      setSaved(true)
      setTimeout(() => setSaved(false), 2000)
    } catch (err) {
      setSaveError(extractErrorMessage(err, 'Could not save preferences.'))
    }
  }

  const themeButton = draft ? (
    <button
      type="button"
      onClick={() => {
        const nextTheme = draft.theme === 'dark' ? 'light' : 'dark';
        setDraft(d => d ? { ...d, theme: nextTheme } : d);
        // Optimistically apply theme immediately for instant visual feedback
        updatePreferences({ theme: nextTheme }).catch(() => {
          // Revert on failure
          setDraft(d => d ? { ...d, theme: draft.theme } : d);
        });
      }}
      disabled={saving}
      className={`btn-primary focus-ring disabled:opacity-50 ${draft.theme === 'light' ? 'btn-secondary' : ''}`}
    >
      {draft.theme === 'dark' ? 'Dark • On' : 'Light • On'}
    </button>
  ) : (
    <span className="text-xs font-mono text-[rgb(var(--text-tertiary))]">—</span>
  )

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div>
        <h1 className="font-display font-bold text-[22px] tracking-tight flex items-center gap-2.5 text-[rgb(var(--text-primary))]">
          <span className="w-9 h-9 grid place-items-center rounded-xl bg-[rgb(var(--accent)/0.1)] border border-[rgb(var(--accent)/0.25)] text-[rgb(var(--accent))]"><Settings className="w-5 h-5" /></span>
          Settings
        </h1>
        <p className="typo-meta mt-1.5">Appearance, notifications and locale.</p>
      </div>

      {loading && !draft && (
        <div className="card p-10 flex flex-col items-center gap-3 text-[rgb(var(--text-tertiary))]">
          <Loader2 className="w-5 h-5 animate-spin" />
          <span className="text-xs font-mono">Loading preferences…</span>
        </div>
      )}

      {error && !draft && (
        <div role="alert" className="card-secondary p-5 flex items-start gap-3 border-l-4" style={{ borderLeftColor: 'rgb(var(--danger) / 0.6)' }}>
          <AlertCircle className="w-5 h-5 text-[rgb(var(--danger))] shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-medium text-[rgb(var(--danger))]">{error}</p>
            <p className="text-xs text-[rgb(var(--text-tertiary))] mt-1">Preferences are stored on the server. Retrying will reload them.</p>
          </div>
        </div>
      )}

      {draft && (
        <form onSubmit={handleSave} className="card-input p-6 space-y-6">
          {/* APPEARANCE */}
          <div className="space-y-3">
            <h3 className="section-header-label flex items-center gap-2"><Palette className="w-4 h-4 text-[rgb(var(--accent))]" /> APPEARANCE</h3>
            <div className="flex items-center justify-between gap-4 p-4 rounded-xl bg-[rgb(var(--surface-3))] border border-[rgb(var(--border))]">
              <div className="flex items-center gap-3">
                <span className="w-9 h-9 grid place-items-center rounded-xl bg-[rgb(var(--card))] border border-[rgb(var(--border))]"><Monitor className="w-4 h-4 text-[rgb(var(--text-tertiary))]" /></span>
                <div>
                  <p className="text-sm font-medium text-[rgb(var(--text-primary))]">Theme</p>
                  <p className="typo-meta">Dark or light{saving ? ' · saving…' : ''}</p>
                </div>
              </div>
              {themeButton}
            </div>
            <p className="typo-micro">
              Active theme: <span className="text-accent">{theme}</span>
            </p>
          </div>

          {/* NOTIFICATIONS */}
          <div className="space-y-3 pt-5 border-t border-[rgb(var(--border))]">
            <h3 className="section-header-label flex items-center gap-2"><Bell className="w-4 h-4 text-[rgb(var(--accent))]" /> NOTIFICATIONS</h3>
            <ToggleRow
              title="AI Daily Briefing"
              description="Morning summary & habit alerts"
              checked={draft.daily_briefing_enabled}
              onChange={(v) => setDraft(d => (d ? { ...d, daily_briefing_enabled: v } : d))}
              disabled={saving}
            />
            <ToggleRow
              title="Security alerts"
              description="Critical account and access warnings"
              icon={<ShieldCheck className="w-4 h-4 text-[rgb(var(--success))]" />}
              checked={draft.security_alerts_enabled}
              onChange={(v) => setDraft(d => (d ? { ...d, security_alerts_enabled: v } : d))}
              disabled={saving}
            />
          </div>

          {/* PLANNER & LOCALE */}
          <div className="space-y-3 pt-5 border-t border-[rgb(var(--border))]">
            <h3 className="section-header-label flex items-center gap-2"><Clock className="w-4 h-4 text-[rgb(var(--accent-tertiary))]" /> PLANNER & LOCALE</h3>

            <div className="flex items-center justify-between gap-4 p-4 rounded-xl bg-[rgb(var(--surface-3))] border border-[rgb(var(--border))]">
              <div className="flex items-center gap-3">
                <span className="w-9 h-9 grid place-items-center rounded-xl bg-[rgb(var(--card))] border border-[rgb(var(--border))]"><Clock className="w-4 h-4 text-[rgb(var(--text-tertiary))]" /></span>
                <div>
                  <p className="text-sm font-medium text-[rgb(var(--text-primary))]">Planner start hour</p>
                  <p className="typo-meta">First block of your daily schedule</p>
                </div>
              </div>
              <select
                value={draft.planner_start_hour}
                onChange={(e) => setDraft(d => (d ? { ...d, planner_start_hour: Number(e.target.value) } : d))}
                disabled={saving}
                aria-label="Planner start hour"
                className="input"
              >
                {HOUR_LABELS.map(h => (
                  <option key={h.value} value={h.value}>{h.label}</option>
                ))}
              </select>
            </div>

            <div className="flex items-center justify-between gap-4 p-4 rounded-xl bg-[rgb(var(--surface-3))] border border-[rgb(var(--border))]">
              <div className="flex items-center gap-3">
                <span className="w-9 h-9 grid place-items-center rounded-xl bg-[rgb(var(--card))] border border-[rgb(var(--border))]"><Globe className="w-4 h-4 text-[rgb(var(--text-tertiary))]" /></span>
                <div>
                  <p className="text-sm font-medium text-[rgb(var(--text-primary))]">Timezone</p>
                  <p className="typo-meta">Used for schedule display</p>
                </div>
              </div>
              <select
                value={draft.timezone}
                onChange={(e) => setDraft(d => (d ? { ...d, timezone: e.target.value } : d))}
                disabled={saving}
                aria-label="Timezone"
                className="input"
              >
                {/* A stored zone outside the curated list stays selectable
                    rather than silently snapping to a different one. */}
                {!TIMEZONES.includes(draft.timezone) && isValidTimezone(draft.timezone) && (
                  <option value={draft.timezone}>{draft.timezone}</option>
                )}
                {TIMEZONES.map(tz => (
                  <option key={tz} value={tz}>{tz}</option>
                ))}
              </select>
            </div>

            {/* 12h/24h is display-only: it never changes a stored instant, so
                it can be flipped freely without rescheduling anything. */}
            <div className="flex items-center justify-between gap-4 p-4 rounded-xl bg-[rgb(var(--surface-3))] border border-[rgb(var(--border))]">
              <div className="flex items-center gap-3">
                <span className="w-9 h-9 grid place-items-center rounded-xl bg-[rgb(var(--card))] border border-[rgb(var(--border))]"><Clock className="w-4 h-4 text-[rgb(var(--text-tertiary))]" /></span>
                <div>
                  <p className="text-sm font-medium text-[rgb(var(--text-primary))]">Time format</p>
                  <p className="typo-meta">How times are displayed, e.g. 18:30 or 6:30 PM</p>
                </div>
              </div>
              <div className="flex items-center gap-1 p-1 rounded-xl bg-[rgb(var(--card))] border border-[rgb(var(--border))]" role="group" aria-label="Time format">
                {(['12h', '24h'] as const).map(f => (
                  <button
                    key={f}
                    type="button"
                    onClick={() => setDraft(d => (d ? { ...d, time_format: f } : d))}
                    disabled={saving}
                    aria-pressed={draft.time_format === f}
                    className={`btn-sm focus-ring disabled:opacity-50 ${
                      draft.time_format === f
                        ? 'btn-primary'
                        : 'btn-ghost'
                    }`}
                  >
                    {f}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {saveError && (
            <div role="alert" className="flex items-start gap-2 typo-micro text-[rgb(var(--danger))]">
              <AlertCircle className="w-4 h-4 shrink-0" />
              {saveError}
            </div>
          )}

          <div className="flex items-center justify-between pt-5 border-t border-[rgb(var(--border))]">
            {/* `aria-live` rather than a purely visual toggle, so the save is
                announced rather than only appearing. */}
            <span role="status" aria-live="polite" className={`typo-micro transition-opacity ${saved ? 'text-[rgb(var(--success))] opacity-100' : 'opacity-0'}`}>✓ Preferences saved</span>
            <button type="submit" disabled={saving} className="btn-primary focus-ring">
              {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
              {saving ? 'Saving…' : 'Save Preferences'}
            </button>
          </div>
        </form>
      )}

      {/* Replay entry point. The first-time flow is gated on a persisted
          server flag, so a user who skipped it would otherwise have no way back
          to it — this is the "resume if partially completed" path, and it
          resets the flag so `App` shows the flow again on next mount. */}
      <div className="card-secondary p-6">
        <h3 className="section-header-label flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-[rgb(var(--accent))]" /> GETTING STARTED
        </h3>
        <p className="typo-body-sm mt-3">
          Replay the short setup walkthrough — what AI-LifeOS manages, and how to create your
          first task, goal, habit or time block. Nothing you have already created is affected.
        </p>
        <button
          type="button"
          onClick={restartSetup}
          disabled={restarting}
          className="btn-secondary mt-4 focus-ring"
        >
          {restarting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
          {restarting ? 'Opening…' : 'Replay setup walkthrough'}
        </button>
      </div>
    </div>
  )
}