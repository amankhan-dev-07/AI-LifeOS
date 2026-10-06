import React from 'react'
import { Menu, X, ArrowRight } from 'lucide-react'
import { Link } from 'react-router-dom'
import { BrandMark } from '../components/BrandMark'

/**
 * Anchor ids, defined once.
 *
 * The nav renders links only to these. Every entry exists as a `Landmark` id on
 * the page, so there is no way to add a nav link to a section that is missing —
 * if a band is removed, the link here dangles visibly in review rather than
 * silently 404-ing for a visitor.
 */
export const NAV_SECTIONS = [
  { id: 'product', label: 'Product' },
  { id: 'intelligence', label: 'Intelligence' },
  { id: 'workflows', label: 'How it works' },
  { id: 'why', label: 'Why' },
] as const

export const PublicBrand: React.FC<{ compact?: boolean }> = ({ compact }) => (
  // One flex row owns the spacing. `BrandMark` is asked for the bare tile
  // because the wordmark below is not plain text — it carries the "PERSONAL OS"
  // descriptor in a different weight, and belongs in this flex row rather than
  // inside `BrandMark`'s.
  <span className="inline-flex items-center gap-2.5">
    <BrandMark size="sm" showWordmark={false} />
    <span className="brand-wordmark !font-bold">
      AI-LifeOS
      {compact ? null : (
        <span className="mono-xs ml-2 hidden font-normal uppercase tracking-[0.18em] text-[rgb(var(--text-muted))] sm:inline">
          Personal OS
        </span>
      )}
    </span>
  </span>
)

export const PublicNav: React.FC = () => {
  const [open, setOpen] = React.useState(false)
  const [scrolled, setScrolled] = React.useState(false)

  // Backdrop only appears once content is behind the bar. Passive listener,
  // and it writes one boolean rather than a layout-triggering style.
  React.useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8)
    onScroll()
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  // Locking body scroll while the sheet is open stops the page behind the
  // overlay from scrolling on touch, which otherwise reads as a broken menu.
  React.useEffect(() => {
    if (!open) return
    const previous = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false)
    }
    window.addEventListener('keydown', onKey)
    return () => {
      document.body.style.overflow = previous
      window.removeEventListener('keydown', onKey)
    }
  }, [open])

  const close = () => setOpen(false)

  return (
    <header
      className={`fixed inset-x-0 top-0 z-50 transition-colors duration-300 ${
        scrolled
          ? 'border-b border-[rgb(var(--border))] bg-[rgb(var(--bg))]/90 backdrop-blur-lg'
          : 'border-b border-transparent'
      }`}
    >
      <nav
        aria-label="Primary"
        className="mx-auto flex h-14 w-full max-w-[1240px] items-center justify-between px-5 sm:px-8"
      >
        <Link
          to="/"
          className="focus-ring rounded-lg"
          aria-label="AI-LifeOS home"
          onClick={close}
        >
          <PublicBrand />
        </Link>

        <div className="hidden items-center gap-1 md:flex">
          {NAV_SECTIONS.map(item => (
            <a
              key={item.id}
              href={`#${item.id}`}
              className="focus-ring rounded-lg px-3 py-2 text-sm text-[rgb(var(--text-secondary))] transition-colors hover:text-[rgb(var(--text-primary))]"
            >
              {item.label}
            </a>
          ))}
        </div>

        <div className="hidden items-center gap-2 md:flex">
          <Link
            to="/login"
            className="btn-ghost focus-ring rounded-xl px-4 py-2 text-sm font-medium"
          >
            Sign in
          </Link>
          <Link
            to="/register"
            className="btn-primary focus-ring group inline-flex items-center gap-1.5 rounded-xl px-4 py-2 text-sm font-semibold"
          >
            Get started
            <ArrowRight
              className="h-4 w-4 transition-transform duration-200 group-hover:translate-x-0.5"
              aria-hidden="true"
            />
          </Link>
        </div>

        <button
          type="button"
          onClick={() => setOpen(v => !v)}
          aria-expanded={open}
          aria-controls="public-mobile-menu"
          aria-label={open ? 'Close menu' : 'Open menu'}
          className="btn-ghost focus-ring grid h-10 w-10 place-items-center rounded-xl md:hidden"
        >
          {open ? (
            <X className="h-5 w-5" aria-hidden="true" />
          ) : (
            <Menu className="h-5 w-5" aria-hidden="true" />
          )}
        </button>
      </nav>

      {/* Mobile sheet. Rendered only when open, so it costs no nodes when closed. */}
      {open ? (
        <div
          id="public-mobile-menu"
          className="animate-fadeIn border-t border-[rgb(var(--border))] bg-[rgb(var(--bg))] px-5 pb-6 pt-3 shadow-[var(--shadow-elevated)] md:hidden"
        >
          <ul className="flex flex-col">
            {NAV_SECTIONS.map(item => (
              <li key={item.id}>
                <a
                  href={`#${item.id}`}
                  onClick={close}
                  className="focus-ring block rounded-lg px-1 py-3.5 text-body-md text-[rgb(var(--text-secondary))] transition-colors hover:text-[rgb(var(--text-primary))]"
                >
                  {item.label}
                </a>
              </li>
            ))}
          </ul>

          <div className="mt-4 flex flex-col gap-2.5 border-t border-[rgb(var(--border-subtle))] pt-5">
            <Link
              to="/register"
              onClick={close}
              className="btn-primary focus-ring inline-flex h-12 items-center justify-center gap-2 rounded-xl text-sm font-semibold"
            >
              Get started
              <ArrowRight className="h-4 w-4" aria-hidden="true" />
            </Link>
            <Link
              to="/login"
              onClick={close}
              className="btn-secondary focus-ring inline-flex h-12 items-center justify-center rounded-xl text-sm font-medium"
            >
              Sign in
            </Link>
          </div>
        </div>
      ) : null}
    </header>
  )
}
