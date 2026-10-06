import React from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'

import { AuthProvider, useAuth } from './context/AuthContext'
import { PreferencesProvider } from './context/PreferencesContext'
import { NotificationsProvider } from './context/NotificationsContext'
import { RemindersProvider } from './context/RemindersContext'
import { AuthScreen } from './AuthScreen'
import ErrorBoundary from './components/ErrorBoundary'

/**
 * Route shell.
 *
 * Three deliberate decisions live here.
 *
 * 1. `AuthProvider` sits above the router because the gate needs it. It holds
 *    nothing but a token and a user.
 *
 * 2. Everything authenticated — the views, `MainLayout`, `OnboardingFlow` and
 *    with them `three` and `@react-three/fiber` — is imported lazily inside
 *    `AppShell`. A visitor on `/` downloads the landing page and `react-dom`,
 *    not the whole application. This is the single biggest performance win in
 *    Phase 9 and it is why the public route was split rather than added.
 *
 * 3. The three authenticated providers mount *inside* `AppShell`, so they are
 *    not part of the public bundle. They all early-return on
 *    `!isAuthenticated` regardless, but not shipping them is better than
 *    relying on that.
 */
function AppShell() {
  const App = React.lazy(() => import('./AppAuthenticated'))

  return (
    <React.Suspense fallback={<BootScreen label="LOADING YOUR WORKSPACE…" />}>
      <App />
    </React.Suspense>
  )
}

/**
 * Gate for the authenticated area. Redirects to `/login` rather than rendering
 * a spinner forever, so a deep link into `/app` lands somewhere usable.
 */
function RequireAuth({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth()

  if (isLoading) return <BootScreen label="LOADING YOUR WORKSPACE…" />
  if (!isAuthenticated) return <Navigate to="/login" replace />

  return <>{children}</>
}

const BootScreen: React.FC<{ label: string }> = ({ label }) => (
  <div className="shell-bg flex min-h-screen items-center justify-center p-8">
    <div className="flex flex-col items-center gap-4">
      <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-[rgb(var(--accent))]">
        <span className="h-2 w-2 rounded-full bg-[rgb(var(--text-inverse))]" />
      </div>
      <p className="font-mono text-sm tracking-widest text-[rgb(var(--text-tertiary))]">
        {label}
      </p>
      {/* The shimmer is a transform-only animation and is neutralised under
          `prefers-reduced-motion`. It is the one looping animation on this
          screen because it is the one that reports real progress — everything
          else here is static. */}
      <div className="h-1 w-32 overflow-hidden rounded-full bg-[rgb(var(--border))]">
        <div className="animate-shimmer h-full w-1/2 rounded-full bg-[rgb(var(--accent))]" />
      </div>
    </div>
  </div>
)

/**
 * Providers that only ever wrap authenticated content.
 *
 * Split out of the router's root so `PreferencesProvider` is not mounted for a
 * visitor reading the marketing site.
 */
const AuthenticatedProviders: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => (
  <PreferencesProvider>
    <NotificationsProvider>
      <RemindersProvider>{children}</RemindersProvider>
    </NotificationsProvider>
  </PreferencesProvider>
)

/**
 * The landing page is its own chunk, so the public route carries only what it
 * renders and never pulls the authenticated views.
 */
const LandingPage = React.lazy(() => import('./landing/LandingPage'))

function PublicRoutes() {
  const { isAuthenticated } = useAuth()

  return (
    <React.Suspense fallback={<BootScreen label="LOADING…" />}>
      <Routes>
        {/* An authenticated visitor asking for the landing page goes straight
            to their dashboard rather than being shown marketing copy. */}
        <Route
          path="/"
          element={isAuthenticated ? <Navigate to="/app" replace /> : <LandingPage />}
        />

        {/* AuthScreen toggles login and register internally; `initialMode`
            picks the starting side, so both URLs resolve and are linkable and
            the landing CTAs land on the form the visitor asked for. */}
        <Route
          path="/login"
          element={<AuthScreen initialMode="login" />}
        />
        <Route
          path="/register"
          element={<AuthScreen initialMode="register" />}
        />

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </React.Suspense>
  )
}

const App: React.FC = () => {
  return (
    <ErrorBoundary>
      <BrowserRouter>
        <AuthProvider>
          <Routes>
            <Route
              path="/app/*"
              element={
                <RequireAuth>
                  <AuthenticatedProviders>
                    <AppShell />
                  </AuthenticatedProviders>
                </RequireAuth>
              }
            />
            {/* Everything else is public. `/login` and `/register` live in the
                same branch so an unauthenticated visitor never mounts a
                provider that would immediately start fetching with no token. */}
            <Route path="*" element={<PublicRoutes />} />
          </Routes>
        </AuthProvider>
      </BrowserRouter>
    </ErrorBoundary>
  )
}

export default App
