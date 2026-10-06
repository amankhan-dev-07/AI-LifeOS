import React, { useState, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { ChevronLeft, Lock, Mail, User as UserIcon, ArrowRight, ShieldCheck, Sparkles, Eye, EyeOff } from 'lucide-react'
import { useAuth } from './context/AuthContext'
import { BrandMark } from './components/BrandMark'

/**
 * AuthScreen — the entrance to the product.
 *
 * Design rules for this screen, in order of what they cost:
 *   - No continuous animation. The only motion is the one-shot entrance below,
 *     which resolves on the first frame after mount and then never repaints.
 *   - No blurred orb behind the logo. The old mark was a 64px gradient tile with
 *     a second copy of itself at `opacity-15 blur-xl` behind it — a live blur
 *     surface that the compositor had to re-filter, for an effect a solid tile
 *     and a hairline already convey.
 *   - No security claims. The badge says "Password hashed" and nothing more;
 *     "encrypted" / "SSL secured" / "256-bit" would describe transport and
 *     algorithm choices this screen cannot verify.
 *   - Labels are sentence case in the UI sans. Three all-caps monospace labels
 *     above three fields read as a terminal, which is the wrong register for
 *     the front door of a productivity product.
 */

export const AuthScreen: React.FC<{ initialMode?: 'login' | 'register' }> = ({
  initialMode = 'login',
}) => {
  const { login, register } = useAuth()
  const navigate = useNavigate()
  const [isLogin, setIsLogin] = useState(initialMode === 'login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [name, setName] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [showPw, setShowPw] = useState(false)
  const [mounted, setMounted] = useState(false)

  // One rAF, once, on mount — then the state never changes again. This is the
  // only JavaScript-driven animation on the screen and it does not loop.
  useEffect(() => {
    const timer = requestAnimationFrame(() => setMounted(true))
    return () => cancelAnimationFrame(timer)
  }, [])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      if (isLogin) await login(email, password)
      else await register({ email, name, password })
      navigate('/app', { replace: true })
    } catch (err: any) {
      const detail = err?.response?.data?.detail
      let message = 'Authentication failed. Check your email and password.'
      if (Array.isArray(detail)) message = detail.map((d: any) => d?.msg || d?.message || (typeof d === 'string' ? d : JSON.stringify(d))).join(' • ')
      else if (typeof detail === 'string') message = detail
      else if (detail && typeof detail === 'object') message = (detail as any).msg || (detail as any).message || JSON.stringify(detail)
      else if (typeof err?.message === 'string' && err.message) message = err.message
      setError(message)
    } finally { setLoading(false) }
  }

  const toggleMode = () => {
    setIsLogin(v => !v)
    setError('')
  }

  // Entrance is a single 240ms opacity+2px lift on the card as a whole. The
  // previous version staggered four blocks over 700ms with 100/200/300ms
  // delays, which delayed the first paint of the *form* — the thing the user
  // came to type into — behind two decorative blocks.
  const enter = (extra: string) =>
    `transition-all duration-[240ms] ease-out ${extra} ${
      mounted ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-2'
    }`

  return (
    <div className="min-h-screen relative overflow-hidden flex items-center justify-center p-4 md:p-6">
      {/* === PAGE BACKGROUND === */}
      <div className="absolute inset-0 shell-bg" />

      {/* === ATMOSPHERIC WASH (static, painted once, no blur filter) ===
          Two very low-opacity radials: the cyan anchor from the upper left, a
          whisper of violet from the lower right — the two halves of the
          signature accent, at a strength that reads as light rather than as a
          coloured background. Painted once into the layer, never animated. */}
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          background: `
            radial-gradient(ellipse 70% 55% at 18% 8%, rgb(var(--accent) / 0.07) 0%, transparent 62%),
            radial-gradient(ellipse 55% 45% at 84% 92%, rgb(var(--accent-secondary) / 0.05) 0%, transparent 55%)
          `,
        }}
      />

      {/* === MAIN CONTENT === */}
      <div className="relative z-10 w-full max-w-[400px]">
        {/* Back to the public site.
            It is the lowest-priority element on the screen and was sitting
            24px above a 56px brand tile, so a small grey link read as the
            top of the page and everything below it looked pushed down. It now
            hugs the brand block and the four rhythm slots below are tightened,
            which brings the first field up into a comfortable thumb reach on
            a short viewport without moving anything relative to its own group. */}
        <div className={`mb-4 ${enter('')}`}>
          <Link
            to="/"
            className="focus-ring inline-flex items-center gap-1.5 rounded-lg py-1 text-[13px] font-medium text-[rgb(var(--text-tertiary))] transition-colors hover:text-[rgb(var(--text-primary))]"
          >
            <ChevronLeft className="w-4 h-4" aria-hidden="true" />
            Back to the home page
          </Link>
        </div>

        {/* === BRANDING === */}
        <div className={`text-center mb-6 ${enter('delay-60')}`}>
          {/* The brand mark. Shared component so the tile, glyph colour and
              wordmark treatment are identical to the sidebar and the public
              nav — the previous inline copy is what drifted to a dark glyph on
              the violet end of this same gradient. */}
          <BrandMark size="lg" showWordmark={false} />

          <h1 className="typo-h1 mt-5">AI-LifeOS</h1>

          <p className="typo-meta mt-1.5">
            Your personal operating system
          </p>
        </div>

        {/* === AUTH CARD ===
            Level-4 elevated surface: this is the one dialog-like surface on the
            screen, so it carries the deepest shadow and the lightest fill. The
            old version stacked `glass-strong` (an 85%-opacity fill + 12px
            backdrop blur) *and* a `card` border *and* a second absolute border
            ring *and* a gradient hairline — five layers of chrome on a box
            that only needs one. */}
        <div className={enter('delay-120')}>
          <div className="card-hero p-6 md:p-7">
            <div className="flex items-start justify-between gap-3 mb-6">
              <div className="min-w-0">
                <h2 className="typo-card-title">{isLogin ? 'Welcome back' : 'Create your account'}</h2>
                <p className="typo-meta mt-1">
                  {isLogin ? 'Sign in to your LifeOS' : 'Set up your personal OS'}
                </p>
              </div>
              <div className="hidden sm:flex items-center gap-1.5 shrink-0 px-2 py-1 rounded-md bg-[rgb(var(--surface-2))] border border-[rgb(var(--border-subtle))] text-[11px] text-[rgb(var(--text-tertiary))]">
                <ShieldCheck aria-hidden="true" className="w-3.5 h-3.5 text-[rgb(var(--success))]" />
                Password hashed
              </div>
            </div>

            {/* Error state.
                The previous version used `bg-[rgb(var(--danger-soft))]` as the
                fill. `--danger-soft` is a fully opaque red, so the box was
                solid red behind red text — unreadable in both themes. A 10%
                tint over the card is the correct reading for a form-level
                error, with a left rule carrying the severity. */}
            {error && (
              <div
                role="alert"
                className="mb-5 flex items-start gap-2.5 px-3.5 py-3 rounded-lg bg-[rgb(var(--danger) / 0.1)] border border-[rgb(var(--danger) / 0.3)] border-l-2 !border-l-[rgb(var(--danger))] text-[13px] leading-relaxed text-[rgb(var(--danger))] animate-scaleIn"
              >
                {error}
              </div>
            )}

            {/* Form */}
            <form onSubmit={handleSubmit} className="space-y-4">
              {/* Name Field (Register Only) */}
              {!isLogin && (
                <div>
                  <label htmlFor="auth-name" className="typo-label block mb-2">
                    Full name
                  </label>
                  <div className="relative group">
                    <UserIcon aria-hidden="true" className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-[rgb(var(--text-muted))] transition-colors group-focus-within:text-[rgb(var(--accent))]" />
                    <input
                      id="auth-name"
                      value={name}
                      onChange={e => setName(e.target.value)}
                      placeholder="Ada Lovelace"
                      autoComplete="name"
                      required
                      className="input input-icon-left"
                    />
                  </div>
                </div>
              )}

              {/* Email Field */}
              <div>
                <label htmlFor="auth-email" className="typo-label block mb-2">
                  Email address
                </label>
                <div className="relative group">
                  <Mail aria-hidden="true" className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-[rgb(var(--text-muted))] transition-colors group-focus-within:text-[rgb(var(--accent))]" />
                  <input
                    id="auth-email"
                    type="email"
                    value={email}
                    onChange={e => setEmail(e.target.value)}
                    placeholder="operator@lifeos.app"
                    autoComplete="email"
                    required
                    className="input input-icon-left"
                  />
                </div>
              </div>

              {/* Password Field */}
              <div>
                <label htmlFor="auth-password" className="typo-label block mb-2">
                  Password
                </label>
                <div className="relative group">
                  <Lock aria-hidden="true" className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-[rgb(var(--text-muted))] transition-colors group-focus-within:text-[rgb(var(--accent))]" />
                  <input
                    id="auth-password"
                    type={showPw ? 'text' : 'password'}
                    value={password}
                    onChange={e => setPassword(e.target.value)}
                    placeholder="••••••••"
                    autoComplete={isLogin ? 'current-password' : 'new-password'}
                    required
                    className="input input-icon-both"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPw(v => !v)}
                    aria-label={showPw ? 'Hide password' : 'Show password'}
                    aria-pressed={showPw}
                    className="absolute right-1.5 top-1/2 -translate-y-1/2 btn-icon !w-10 !h-10 focus-ring"
                  >
                    {showPw ? <EyeOff className="w-4 h-4" aria-hidden="true" /> : <Eye className="w-4 h-4" aria-hidden="true" />}
                  </button>
                </div>
              </div>

              {/* Submit — the one primary action on the screen.
                  Solid accent, NOT the signature gradient, and that is a
                  contrast decision rather than an aesthetic one. In light mode
                  the gradient runs #0891B2 → #8B5CF6, and no single flat label
                  colour passes AA at both ends: dark text on the cyan is 4.6:1
                  but only 3.2:1 on the violet, white is 5.3:1 on the violet but
                  3.7:1 on the cyan. A gradient is used behind an ICON (the brand
                  mark) where nothing has to be read out of it, and behind the
                  progress fill; a CTA with a label on it stays solid so its
                  text is legible end to end. */}
              <button
                type="submit"
                disabled={loading}
                className="btn-primary btn-lg w-full mt-1 focus-ring"
              >
                {loading ? (
                  <>
                    <span
                      className="w-4 h-4 border-2 border-[rgb(var(--text-inverse)/0.35)] border-t-[rgb(var(--text-inverse))] rounded-full animate-spin"
                      aria-hidden="true"
                    />
                    <span>{isLogin ? 'Signing in…' : 'Creating account…'}</span>
                  </>
                ) : (
                  <>
                    <span>{isLogin ? 'Sign in' : 'Create account'}</span>
                    <ArrowRight className="w-4 h-4" aria-hidden="true" />
                  </>
                )}
              </button>
            </form>

            {/* Mode switch.
                The "──── Or ────" rule divided two actions that are not
                alternatives between competing methods; they are the two ends of
                one flow. A single quiet link states the relationship directly. */}
            <div className="mt-6 pt-5 border-t border-[rgb(var(--border-subtle))] text-center">
              <button
                onClick={toggleMode}
                className="inline-flex items-center gap-1.5 rounded-lg px-2 py-1.5 text-[13px] font-medium text-accent text-accent-hover transition-colors focus-ring"
              >
                <Sparkles className="w-4 h-4" aria-hidden="true" />
                {isLogin ? 'Need an account? Create one' : 'Already registered? Sign in'}
              </button>

              <p className="mt-3 text-[12px] text-[rgb(var(--text-muted))]">
                Your data stays scoped to your account.
              </p>
            </div>
          </div>
        </div>

        <p className={`mt-6 text-center text-[11px] text-[rgb(var(--text-muted))] ${enter('delay-180')}`}>
          © {new Date().getFullYear()} AI-LifeOS
        </p>
      </div>
    </div>
  )
}