import React, { useEffect, useState, useRef } from 'react'
import {
  LayoutDashboard, CheckSquare, Target, Activity, BookOpen, DollarSign, Cpu, Calendar, User, Settings,
  LogOut, Sun, Moon, Command, Search, Menu, X, ChevronLeft, ChevronRight
} from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { usePreferences } from '../context/PreferencesContext'
import { NotificationBell } from '../components/NotificationBell'
import { BrandMark } from '../components/BrandMark'

interface Props { children: React.ReactNode; activeTab: string; setActiveTab: (t: string) => void; onOpenCommandPalette: () => void }

// === NAVIGATION ITEM ===
//
// The active row is marked by a 2px jade rule, a one-step surface lift and
// slightly stronger text (see `.nav-item.active` in theme.css). Previously it
// was a 12%-opacity accent fill *plus* a 3px accent left border *plus* a tinted
// 40×40 icon tile — three accent surfaces stacked on one 260px row, which is
// why the sidebar read as "generic nav chrome" rather than a control surface.
// The icon no longer gets its own box: a bare lucide glyph at 18px with an
// accent fill when active carries the same signal with less colour mass.
interface NavItemProps {
  item: { name: string; id: string; icon: React.ComponentType<{ className?: string }>; badge?: string }
  active: boolean
  onClick: () => void
  collapsed: boolean
}

const NavItem: React.FC<NavItemProps> = ({ item, active, onClick, collapsed }) => {
  const Icon = item.icon
  return (
    <button
      onClick={onClick}
      aria-current={active ? 'page' : undefined}
      className={`nav-item w-full ${active ? 'active' : ''} focus-ring ${collapsed ? 'justify-center px-0' : ''}`}
      title={collapsed ? item.name : undefined}
    >
      <Icon className="nav-icon w-[18px] h-[18px]" />

      {!collapsed && (
        <>
          <span className="truncate flex-1 text-left">{item.name}</span>
          {item.badge && (
            <span className="typo-micro !text-[9px] !tracking-widest !text-[rgb(var(--text-muted))] px-1.5 py-0.5 rounded-[4px] border border-[rgb(var(--border-subtle))] bg-[rgb(var(--surface-3))]">
              {item.badge}
            </span>
          )}
        </>
      )}
    </button>
  )
}

// === PAGE TRANSITION WRAPPER ===
const PageTransition: React.FC<{ children: React.ReactNode; tabKey: string }> = ({ children, tabKey }) => {
  const [isVisible, setIsVisible] = useState(false)
  const [content, setContent] = useState(children)
  const prevKeyRef = useRef(tabKey)

  useEffect(() => {
    if (prevKeyRef.current !== tabKey) {
      setIsVisible(false)
      const timer = setTimeout(() => {
        setContent(children)
        setIsVisible(true)
        prevKeyRef.current = tabKey
      }, 150)
      return () => clearTimeout(timer)
    } else {
      setIsVisible(true)
    }
  }, [tabKey, children])

  return (
    <div
      className={`transition-all duration-200 ease-out ${
        isVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-2'
      }`}
    >
      {content}
    </div>
  )
}

// Section grouping gives the nav a spine: "operate" vs "account". Ten
// undifferentiated rows read as a settings list; three groups read as a
// product's information architecture.
const NAV_SECTIONS: { label: string; items: { name: string; id: string; icon: React.ComponentType<{ className?: string }>; badge?: string }[] }[] = [
  {
    label: 'Operate',
    items: [
      { name: 'Dashboard', id: 'dashboard', icon: LayoutDashboard },
      { name: 'Tasks', id: 'tasks', icon: CheckSquare },
      { name: 'Planner', id: 'planner', icon: Calendar },
    ],
  },
  {
    label: 'Progress',
    items: [
      { name: 'Goals', id: 'goals', icon: Target },
      { name: 'Habits', id: 'habits', icon: Activity },
      { name: 'Notes', id: 'notes', icon: BookOpen },
      { name: 'Finance', id: 'finance', icon: DollarSign },
    ],
  },
  {
    label: 'System',
    items: [
      { name: 'AI Command', id: 'ai', icon: Cpu, badge: 'PRO' },
      { name: 'Profile', id: 'profile', icon: User },
      { name: 'Settings', id: 'settings', icon: Settings },
    ],
  },
]

const PAGE_TITLES: Record<string, string> = {
  dashboard: 'Dashboard',
  tasks: 'Tasks',
  goals: 'Goals',
  habits: 'Habits',
  planner: 'Planner',
  notes: 'Notes',
  finance: 'Finance',
  ai: 'AI Command Center',
  profile: 'Profile',
  settings: 'Settings',
}

export const MainLayout: React.FC<Props> = ({ children, activeTab, setActiveTab, onOpenCommandPalette }) => {
  const { user, logout } = useAuth()
  const { theme, updatePreferences } = usePreferences()
  const [open, setOpen] = useState(false)
  const [collapsed, setCollapsed] = useState(false)

  const toggleTheme = () => {
    void updatePreferences({ theme: theme === 'dark' ? 'light' : 'dark' })
  }

  useEffect(() => {
    const mql = window.matchMedia('(min-width: 768px)')
    const onResize = () => { if (mql.matches) setOpen(false) }
    window.addEventListener('resize', onResize)
    return () => window.removeEventListener('resize', onResize)
  }, [])

  // Escape closes the mobile drawer. Without it a drawer opened by the menu
  // button can only be dismissed by tapping the overlay or a nav item.
  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') setOpen(false) }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open])

  const pageTitle = PAGE_TITLES[activeTab] ?? activeTab

  return (
    <div className="min-h-screen shell-bg flex flex-col md:flex-row">
      {/* === MOBILE TOP BAR ===
          Level-2 surface, quieter than the content it caps: no accent fill on
          the menu button (it was a full jade block, which pulled the eye to the
          chrome rather than the page). */}
      <div className="md:hidden sticky top-0 z-30 flex items-center justify-between h-14 px-4 glass-strong border-b border-[rgb(var(--border))]">
        <button
          onClick={() => setActiveTab('dashboard')}
          className="focus-ring rounded-lg -ml-1 px-1 py-1"
          aria-label="AI-LifeOS home"
        >
          <BrandMark size="sm" />
        </button>
        <div className="flex items-center gap-0.5">
          <button onClick={onOpenCommandPalette} aria-label="Open command palette" className="btn-icon focus-ring">
            <Search className="w-[18px] h-[18px]" />
          </button>
          <NotificationBell onNavigate={setActiveTab} />
          <button onClick={toggleTheme} aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} theme`} className="btn-icon focus-ring">
            {theme === 'dark' ? <Sun className="w-[18px] h-[18px]" /> : <Moon className="w-[18px] h-[18px]" />}
          </button>
          <button
            onClick={() => setOpen(v => !v)}
            aria-label={open ? 'Close navigation menu' : 'Open navigation menu'}
            aria-expanded={open}
            className="btn-icon focus-ring"
          >
            {open ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>
      </div>

      {/* === MOBILE OVERLAY === */}
      {open && (
        <button
          aria-label="Close navigation menu"
          onClick={() => setOpen(false)}
          className="fixed inset-0 z-30 bg-[rgb(var(--bg-deep) / 0.65)] md:hidden animate-fadeIn"
        />
      )}

      {/* === SIDEBAR ===
          Level-2 surface (--surface-2), which is one step behind the level-3
          cards in the content area — so content reads as "on top of" the
          chrome rather than sharing the same plane. */}
      <aside
        className={`fixed md:sticky top-0 z-40 h-[100dvh] shrink-0 flex flex-col transition-all duration-300 ease-out md:translate-x-0 ${
          open ? 'translate-x-0' : '-translate-x-full md:translate-x-0'
        } ${open ? 'opacity-100' : 'opacity-0 md:opacity-100 pointer-events-none md:pointer-events-auto'} ${
          collapsed ? 'md:w-[72px]' : 'md:w-[252px]'
        } w-[268px] bg-[rgb(var(--surface-2))] border-r border-[rgb(var(--border))]`}
      >
        {/* === LOGO HEADER ===
            The mark is the visual anchor of the navigation: 36px here versus the
            38px nav rows below, so it leads the column without the sidebar
            having to grow. `collapsed` drops the wordmark only — the tile stays
            at the same size, so collapsing the rail does not shift anything
            horizontally and the mark never becomes a small stray glyph. */}
        <div className={`px-5 pt-5 pb-4 ${collapsed ? 'md:px-3' : ''}`}>
          <div className="flex items-center gap-2.5">
            {/* The name comes from `BrandMark` and only from `BrandMark` — it
                must NOT be written here as well, which is exactly what happened
                once and printed the name twice. `v1.0` rides along beneath it
                via `subtext`, so it stays on the baseline it was designed for
                without this block owning a second copy of the wordmark. The
                tile keeps its size when collapsed, so nothing shifts. */}
            <BrandMark
              size="md"
              showWordmark={!collapsed}
              subtext={<span className="typo-micro !tracking-[0.16em] !text-[8px] !text-[rgb(var(--text-muted))] leading-none">v1.0</span>}
            />
          </div>
        </div>

        {/* === COMMAND PALETTE BUTTON === */}
        {!collapsed && (
          <div className="px-4 pb-4 hidden md:block">
            <button
              onClick={onOpenCommandPalette}
              className="nav-item w-full focus-ring"
            >
              <Command className="nav-icon w-[18px] h-[18px]" />
              <span className="flex-1 text-left">Command</span>
              <kbd className="hidden lg:inline-flex items-center px-1.5 py-0.5 rounded-[5px] bg-[rgb(var(--surface-4))] border border-[rgb(var(--border-subtle))] text-[10px] font-mono leading-none text-[rgb(var(--text-tertiary))]">⌘K</kbd>
            </button>
          </div>
        )}

        {/* === NAVIGATION === */}
        <nav className="flex-1 px-3 pb-3 overflow-y-auto scroll-y" aria-label="Main">
          {NAV_SECTIONS.map((section) => (
            <div key={section.label} className="nav-group">
              {!collapsed && (
                <p className="nav-group-label" aria-hidden="true">{section.label}</p>
              )}
              {collapsed && <div className="divider mb-3" aria-hidden="true" />}
              <div className="space-y-0.5">
                {section.items.map(item => (
                  <NavItem
                    key={item.id}
                    item={item}
                    active={activeTab === item.id}
                    onClick={() => { setActiveTab(item.id); setOpen(false) }}
                    collapsed={collapsed}
                  />
                ))}
              </div>
            </div>
          ))}
        </nav>

        {/* === COLLAPSE TOGGLE (Desktop only) === */}
        <button
          onClick={() => setCollapsed(v => !v)}
          className="hidden md:flex items-center justify-center w-8 h-8 mx-auto my-2 rounded-md text-[rgb(var(--text-muted))] hover:text-[rgb(var(--text-secondary))] hover:bg-[rgb(var(--surface-3))] transition-colors focus-ring"
          aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {collapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
        </button>

        {/* === USER PROFILE ===
            Deliberately not a detached card. The account block shares the
            sidebar's surface and is separated by a single hairline, so it
            reads as part of the shell. A bordered footer card previously
            boxed the user off from the product chrome. */}
        <div className="border-t border-[rgb(var(--border))] p-3">
          <div className={`flex items-center gap-2.5 px-1 py-1.5 ${collapsed ? 'md:justify-center' : ''}`}>
            <span className="w-8 h-8 rounded-full bg-[rgb(var(--accent))] grid place-items-center text-[rgb(var(--text-inverse))] font-semibold text-[13px] shrink-0">
              {user?.name ? user.name[0].toUpperCase() : '—'}
            </span>
            {!collapsed && (
              <div className="min-w-0 flex-1">
                <p className="text-[13px] font-medium leading-tight truncate text-[rgb(var(--text-primary))]">{user?.name || 'Operator'}</p>
                <p className="text-[11px] truncate text-[rgb(var(--text-tertiary))] mt-0.5">{user?.email || '—'}</p>
              </div>
            )}
          </div>

          {!collapsed && (
            <div className="mt-2 flex items-center gap-1">
              <button
                onClick={toggleTheme}
                className="flex-1 h-9 inline-flex items-center justify-center gap-1.5 rounded-lg text-[12px] font-medium text-[rgb(var(--text-tertiary))] hover:text-[rgb(var(--text-primary))] hover:bg-[rgb(var(--surface-3))] transition-colors focus-ring"
                title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} theme`}
              >
                {theme === 'dark' ? <><Sun className="w-[14px] h-[14px]" /> Light</> : <><Moon className="w-[14px] h-[14px]" /> Dark</>}
              </button>
              <button
                onClick={logout}
                className="flex-1 h-9 inline-flex items-center justify-center gap-1.5 rounded-lg text-[12px] font-medium text-[rgb(var(--text-tertiary))] hover:text-[rgb(var(--danger))] hover:bg-[rgb(var(--danger) / 0.1)] transition-colors focus-ring"
                title="Sign out"
              >
                <LogOut className="w-[14px] h-[14px]" /> Sign out
              </button>
            </div>
          )}
        </div>
      </aside>

      {/* === MAIN CONTENT === */}
      <main className="flex-1 min-w-0 flex flex-col">
        {/* === DESKTOP TOP BAR ===
            Intentionally the quietest surface in the shell: level-2 fill, a
            hairline bottom border, no shadow and no accent. The title is set
            in display type at 15px — a breadcrumb-scale label, not a second
            H1 competing with the page's own heading. */}
        <header className="hidden md:flex sticky top-0 z-20 items-center justify-between gap-6 h-14 px-6 lg:px-8 bg-[rgb(var(--surface-2))] border-b border-[rgb(var(--border))]">
          <div className="flex items-center gap-3 min-w-0">
            <h2 className="font-display font-medium text-[15px] tracking-tight truncate text-[rgb(var(--text-primary))]">
              {pageTitle}
            </h2>
            <span className="hidden lg:inline-flex items-center gap-1.5 text-[11px] text-[rgb(var(--text-muted))]">
              <span className="w-1 h-1 rounded-full bg-[rgb(var(--text-muted))]" aria-hidden="true" />
              <span className="truncate">{user?.email || 'AI-LifeOS'}</span>
            </span>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            {/* The command trigger is a system control, not a form field: it
                reads as a bordered, monospace-labelled shortcut rather than a
                search box, and shares the 40px control height with the bell. */}
            <button
              onClick={onOpenCommandPalette}
              className="hidden lg:inline-flex items-center gap-2 h-10 pl-3 pr-1.5 rounded-lg bg-[rgb(var(--surface-4))] border border-[rgb(var(--border))] text-[rgb(var(--text-tertiary))] hover:text-[rgb(var(--text-secondary))] hover:border-[rgb(var(--border-hover))] transition-colors focus-ring"
            >
              <Search className="w-4 h-4" />
              <span className="text-[13px]">Search or jump…</span>
              <kbd className="ml-1.5 px-1.5 py-0.5 rounded-[5px] bg-[rgb(var(--surface-2))] border border-[rgb(var(--border-subtle))] text-[10px] font-mono leading-none text-[rgb(var(--text-tertiary))]">⌘K</kbd>
            </button>
            <button
              onClick={onOpenCommandPalette}
              className="lg:hidden btn-icon focus-ring"
              aria-label="Search"
            >
              <Search className="w-[18px] h-[18px]" />
            </button>
            <div className="w-px h-5 bg-[rgb(var(--border))]" aria-hidden="true" />
            <NotificationBell onNavigate={setActiveTab} />
          </div>
        </header>

        {/* === PAGE CONTENT === */}
        <div className="flex-1 px-4 md:px-6 lg:px-8 py-6 lg:py-8 max-w-[1240px] w-full mx-auto">
          <PageTransition tabKey={activeTab}>
            {children}
          </PageTransition>
        </div>
      </main>
    </div>
  )
}