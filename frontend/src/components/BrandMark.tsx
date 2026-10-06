import React from 'react'
import { Cpu } from 'lucide-react'

/**
 * BrandMark — the AI-LifeOS identity tile.
 *
 * This component exists because the mark was previously written out four times
 * (sidebar, mobile top bar, public nav, auth screen) and each copy drifted: the
 * mobile bar never received the gradient at all and stayed flat `--accent`,
 * while the other three used `--text-inverse` for the glyph — which is a DARK
 * token in light mode, so the glyph sank to ~3:1 against the violet end of the
 * gradient. Centralising it means the next change cannot land on three sites
 * out of four again.
 *
 * OWNERSHIP OF THE WORDMARK. `BrandMark` is the single owner of the
 * "AI-LifeOS" text. It renders the tile AND the wordmark by default, and a
 * call site must never add its own — an earlier version had this flag named
 * `decorationOnly`, which read as "render only the decoration" but meant
 * "hide the wordmark", so every call site had to pass it and the sidebar
 * passed it inverted (`decorationOnly={collapsed}`) and printed the name
 * twice. The flag is now `showWordmark` and says what it does.
 *
 * A call site needs `showWordmark={false}` only when it renders the name in
 * different type — the auth screen's H1, or the public nav, where the wordmark
 * also carries a "PERSONAL OS" descriptor and so belongs in that row's own
 * flex container. Everything else gets the name from here.
 *
 * The mark is `aria-hidden`: each call site is already a link or button
 * carrying its own "AI-LifeOS home" label, so exposing the tile separately
 * would make a screen reader announce the wordmark twice. Nothing here is
 * interactive, so it adds no tab stop.
 */
export const BrandMark: React.FC<{
  size?: 'sm' | 'md' | 'lg'
  /**
   * Render the "AI-LifeOS" wordmark beside the tile. `true` by default —
   * `false` returns the bare tile and is correct ONLY for a call site that
   * renders the brand name itself.
   */
  showWordmark?: boolean
  /**
   * Optional line set beneath the wordmark (the sidebar's `v1.0`). It rides
   * inside this component so a call site never has to build the
   * wordmark-plus-caption stack itself — which is what let the sidebar end up
   * rendering the wordmark a second time next to the caption.
   */
  subtext?: React.ReactNode
  /** Extra classes for the wrapper when the wordmark is shown. */
  className?: string
}> = ({ size = 'sm', showWordmark = true, subtext, className = '' }) => {
  const tile = (
    <span className={`brand-mark brand-mark-${size}`} aria-hidden="true">
      <Cpu strokeWidth={2} />
    </span>
  )

  // `showWordmark={false}` returns the bare tile rather than wrapping it. The
  // tile is `inline-grid` and already `flex-shrink: 0`, so a wrapper would add
  // a box that contributes nothing — and, worse, would swallow the caller's own
  // layout if the caller expected a single flex child.
  if (!showWordmark) return tile

  return (
    <span className={`inline-flex items-center gap-2.5 shrink-0 ${className}`}>
      {tile}
      {subtext ? (
        // `leading-none` only when there is a second line: a lone wordmark was
        // inheriting the UI font's line-height and centring on it, and adding a
        // class here would nudge the mobile and public-nav marks.
        <span className="flex flex-col items-start leading-none">
          <span className="brand-wordmark">AI-LifeOS</span>
          <span className="mt-1.5 block">{subtext}</span>
        </span>
      ) : (
        <span className="brand-wordmark">AI-LifeOS</span>
      )}
    </span>
  )
}

export default BrandMark