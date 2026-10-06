import React from 'react'
import { useReducedMotion } from '../hooks/useReducedMotion'

/**
 * Scroll-triggered fade-and-rise.
 *
 * Deliberately IntersectionObserver rather than a scroll listener: no scroll
 * handler runs per frame, which matters on the integrated graphics this page
 * targets. Nothing renders until observed, then transitions once — there is no
 * animation loop anywhere in the public site.
 *
 * When the visitor prefers reduced motion the element is shown immediately with
 * no transition at all, so content is never gated behind an effect that will
 * not run for them.
 */
export const Reveal: React.FC<{
  children: React.ReactNode
  className?: string
  delay?: number
  as?: 'div' | 'li' | 'article'
}> = ({ children, className = '', delay = 0, as = 'div' }) => {
  const reduced = useReducedMotion()
  const ref = React.useRef<HTMLElement | null>(null)
  const [shown, setShown] = React.useState(false)

  React.useEffect(() => {
    const node = ref.current
    if (!node) return

    if (reduced) {
      setShown(true)
      return
    }

    // No observer support, or a very old engine: show the content rather than
    // risk leaving the page blank.
    if (typeof IntersectionObserver === 'undefined') {
      setShown(true)
      return
    }

    const observer = new IntersectionObserver(
      entries => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            setShown(true)
            observer.disconnect()
          }
        }
      },
      { rootMargin: '0px 0px -8% 0px', threshold: 0.05 },
    )

    observer.observe(node)
    return () => observer.disconnect()
  }, [reduced])

  const Tag = as as 'div'

  return (
    <Tag
      ref={ref as React.Ref<HTMLDivElement>}
      className={`${className} transition-[opacity,transform] duration-[700ms] ease-[cubic-bezier(0.16,1,0.3,1)] ${
        shown || reduced ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-5'
      }`}
      style={delay ? { transitionDelay: `${delay}ms` } : undefined}
    >
      {children}
    </Tag>
  )
}
