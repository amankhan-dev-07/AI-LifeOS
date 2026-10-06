import React from 'react'
import { User, Shield, Cpu, Mail, Calendar } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { formatShortDate } from '../utils/datetime'

export const ProfileView: React.FC = () => {
  const { user } = useAuth()

  // Every row below is read from the authenticated account. The previous
  // version hardcoded the join date ('2026.09.30'), the fallback email and a
  // fixed "Verified Neural Clearance" line, so the page showed the same
  // details for every user regardless of who was signed in. `created_at` is
  // returned by `GET /users/me`, and account state comes from `is_active`,
  // which the backend enforces (403 on an inactive account).
  const rows = [
    { label: 'Email address', value: user?.email || '—', icon: Mail, token: '--accent-tertiary' },
    { label: 'Account status', value: user?.is_active ? 'Active' : 'Deactivated', icon: Shield, token: user?.is_active ? '--success' : '--danger' },
    { label: 'Member since', value: user?.created_at ? formatShortDate(user.created_at.slice(0, 10)) : '—', icon: Calendar, token: '--text-tertiary' },
    { label: 'App version', value: 'v1.0', icon: Cpu, token: '--text-tertiary' },
  ]

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div>
        <h1 className="font-display font-bold text-[22px] tracking-tight flex items-center gap-2.5 text-[rgb(var(--text-primary))]">
          <span className="w-9 h-9 grid place-items-center rounded-xl bg-[rgb(var(--accent)/0.1)] border border-[rgb(var(--accent)/0.25)] text-[rgb(var(--accent))]"><User className="w-5 h-5"/></span>
          Profile
        </h1>
        <p className="typo-meta mt-1.5">Your account details.</p>
      </div>
      <div className="card-secondary p-6 space-y-6">
        <div className="flex items-center gap-4">
          <div className="w-16 h-16 rounded-2xl bg-[rgb(var(--accent))] grid place-items-center text-[rgb(var(--text-inverse))] text-2xl font-bold">
            {user?.name ? user.name[0].toUpperCase() : '—'}
          </div>
          <div className="min-w-0">
            <h2 className="typo-h3 truncate">{user?.name || '—'}</h2>
            <p className="typo-meta mt-1 truncate">{user?.email || ''}</p>
          </div>
        </div>
        <div className="pt-4 border-t border-[rgb(var(--border))] space-y-3">
          {rows.map(row => {
            const Icon = row.icon
            return (
              <div key={row.label} className="row-item">
                <span className="typo-micro flex items-center gap-2">
                  <Icon className="w-4 h-4" style={{ color: `rgb(var(${row.token}))` }} />
                  {row.label}
                </span>
                <span className="typo-body-sm font-medium truncate">{row.value}</span>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}