import React from 'react'

/**
 * Single `<section>` wrapper for every landing band.
 *
 * Owns three things that would otherwise be repeated eleven times and drift
 * apart: the scroll-reveal wiring, the vertical rhythm, and the accessible
 * heading. `id` is also the anchor target the navbar links to, so a section
 * cannot exist without an addressable id.
 */
export const Landmark: React.FC<{
  id: string
  eyebrow?: string
  title: React.ReactNode
  lede?: React.ReactNode
  children: React.ReactNode
  tone?: 'base' | 'sunken'
  headingLevel?: 'h2' | 'h3'
}> = ({
  id,
  eyebrow,
  title,
  lede,
  children,
  tone = 'base',
  headingLevel = 'h2',
}) => {
  const Heading = headingLevel

  return (
    <section
      id={id}
      aria-labelledby={`${id}-heading`}
      className={`relative scroll-mt-24 border-t ${
        tone === 'sunken'
          ? 'border-[rgb(var(--border-subtle))] bg-[rgb(var(--bg-deep))]'
          : 'border-transparent'
      }`}
    >
      <div className="mx-auto w-full max-w-[1200px] px-5 py-20 sm:px-8 md:py-28">
        {eyebrow ? (
          <p className="mono-xs text-accent mb-4 flex items-center gap-2 uppercase tracking-[0.2em]">
            <span aria-hidden="true" className="h-px w-6 bg-[rgb(var(--accent)/0.5)]" />
            {eyebrow}
          </p>
        ) : null}

        <Heading
          id={`${id}-heading`}
          className="text-balance text-display-md font-bold text-[rgb(var(--text-primary))] md:text-display-lg"
        >
          {title}
        </Heading>

        {lede ? (
          <div className="mt-5 max-w-[62ch] text-body-lg text-[rgb(var(--text-secondary))]">
            {lede}
          </div>
        ) : null}

        <div className={lede ? 'mt-12 md:mt-16' : 'mt-10 md:mt-12'}>{children}</div>
      </div>
    </section>
  )
}
