import React from 'react'
import { Link } from 'react-router-dom'
import {
  CheckSquare,
  Target,
  Activity,
  Calendar,
  StickyNote,
  Wallet,
  BellRing,
  Search,
  Layers,
  Scale,
  Crosshair,
  Lock,
  Database,
  WifiOff,
  ArrowRight,
  Sparkles,
} from 'lucide-react'

import { Landmark } from './Landmark'
import { Reveal } from './Reveal'
import { HeroVisual } from './HeroVisual'
import { PublicNav, PublicBrand } from './PublicNav'
import {
  DOMAIN_GROUPS,
  GET_STARTED_AFTER,
  GET_STARTED_STEPS,
  INTELLIGENCE_PIPELINE,
  REASONS,
  USE_CASES,
} from './content'

const ICONS: Record<string, React.ElementType> = {
  CheckSquare,
  Target,
  Activity,
  Calendar,
  StickyNote,
  Wallet,
  BellRing,
  Search,
  Layers,
  Scale,
  Crosshair,
  Lock,
  Database,
  WifiOff,
  Sparkles,
}

/**
 * The public AI-LifeOS site.
 *
 * Mounted at `/` and nowhere else — this component is never imported by the
 * authenticated tree, so nothing here can reach user data. It reads no context,
 * no service and no store; the only shared dependency is the design system's
 * Tailwind classes and CSS variables.
 */
const LandingPage: React.FC = () => {
  // Per-page metadata. No SEO dependency for a single static page — this is
  // the same shape a helmet would emit, without the package.
  React.useEffect(() => {
    document.title = 'AI-LifeOS — Your personal operating system for tasks, goals, habits and money'

    const description =
      'AI-LifeOS brings tasks, goals, habits, planner, notes, finance and reminders into one connected system, then surfaces explainable insights over your own data. No guessing, no black box.'

    const setMeta = (selector: string, attr: string, value: string) => {
      let el = document.head.querySelector<HTMLMetaElement>(selector)
      if (!el) {
        el = document.createElement('meta')
        document.head.appendChild(el)
      }
      el.setAttribute(attr, value)
    }

    setMeta('meta[name="description"]', 'content', description)
    setMeta('meta[property="og:title"]', 'content', document.title)
    setMeta('meta[property="og:description"]', 'content', description)
    setMeta('meta[property="og:type"]', 'content', 'website')
  }, [])

  return (
    <div className="min-h-screen bg-[rgb(var(--bg))] text-[rgb(var(--text-primary))]">
      {/* Skips the nav straight to the content — the first keyboard user on
          the page should not have to tab through four section links. */}
      <a href="#product" className="sr-only focus:not-sr-only focus-ring">
        Skip to content
      </a>

      <PublicNav />

      <main id="main">
        {/* ============================================================
            HERO
            ============================================================ */}
        <section className="relative overflow-hidden">
          {/* Static atmosphere: one grid wash and one soft brand wash. Both
              are painted once. No moving background, no canvas. */}
          <div
            aria-hidden="true"
            className="pointer-events-none absolute inset-0 -z-10 opacity-[0.035]"
            style={{
              backgroundImage:
                'linear-gradient(rgb(var(--accent-tertiary) / 0.7) 1px, transparent 1px), linear-gradient(90deg, rgb(var(--accent-tertiary) / 0.7) 1px, transparent 1px)',
              backgroundSize: '56px 56px',
              maskImage:
                'radial-gradient(ellipse 70% 60% at 50% 0%, #000 20%, transparent 75%)',
              WebkitMaskImage:
                'radial-gradient(ellipse 70% 60% at 50% 0%, #000 20%, transparent 75%)',
            }}
          />
          <div
            aria-hidden="true"
            className="pointer-events-none absolute inset-x-0 top-0 -z-10 h-[520px]"
            style={{
              background:
                'radial-gradient(ellipse 55% 45% at 50% 0%, rgb(var(--accent) / 0.11), transparent 65%)',
            }}
          />

          {/* `min-h` offsets the 56px fixed navbar so the composition centres
              in the viewport a visitor actually sees, not in a box that starts
              56px too high. `md:` (768px) is the first breakpoint where a
              two-column hero fits; below it the content simply starts under the
              bar and stacks, which is what mobile wants.

              The grid itself is `md:grid-cols-2` — both columns equal — so the
              visual is not shoved right by an asymmetric ratio. Copy is allowed
              to run wider than the visual, because the headline is the
              element that was starving. */}
          <div className="mx-auto flex min-h-[calc(100svh-4rem)] w-full max-w-[1240px] flex-col justify-center px-5 pb-16 pt-24 sm:px-8 md:pb-20 md:pt-20">
            <div className="grid items-center gap-10 md:grid-cols-2 md:gap-8 lg:gap-14">
              {/* Copy column */}
              <div className="animate-fadeInUp">
                {/* The eyebrow. This is the pill that was rendering as an
                    empty coloured bar above the headline: `--accent-soft` was
                    a fully opaque jade and the label was also `--accent`, so
                    the text sat at 0 contrast against its own background. Both
                    the fill and the label are now tokens that differ from each
                    other, and the fill carries its own alpha — the pill is a
                    10% tint with primary-weight text, which reads at a glance
                    in both themes. */}
                <p className="mono-xs text-accent inline-flex items-center gap-2 rounded-full border border-[rgb(var(--accent)/0.3)] bg-[rgb(var(--accent-soft))] px-3 py-1.5 uppercase tracking-[0.16em]">
                  <span
                    aria-hidden="true"
                    className="h-1.5 w-1.5 rounded-full bg-[rgb(var(--accent))]"
                  />
                  Personal operating system
                </p>

                {/* The h1 carries the whole positioning. It names the product,
                    what it manages, and what it does with the result — in that
                    order — because that is what the first viewport has to
                    answer.

                    `text-balance` is deliberately NOT used here. It evens out
                    line lengths, which for a 94-character headline in a wide
                    column means manufacturing short, ragged lines to balance the
                    last one — the opposite of what a hero headline wants. The
                    default greedy wrap plus the wider measure gives 3–4 long,
                    even lines instead. It stays on the section headings below,
                    which are short enough for balancing to help. */}
                <h1 className="mt-5 font-display text-[clamp(2.05rem,4.4vw,3.45rem)] font-bold leading-[1.08] tracking-[-0.03em] text-[rgb(var(--text-primary))]">
                  Your tasks, goals, habits, planner and money —{' '}
                  <span className="text-[rgb(var(--accent))]">
                    in one system that explains itself
                  </span>
                </h1>

                {/* Copy is capped by line count, not width, so it fills the wider
                    column instead of leaving it half empty. 60ch stays inside
                    the ~65–75ch comfortable-measure band. */}
                <p className="mt-5 max-w-[60ch] text-body-lg text-[rgb(var(--text-secondary))]">
                  AI-LifeOS is a personal operating system for life. It keeps
                  what you need to do, what you are trying to achieve, what you
                  are trying to do consistently, and where your money goes — in
                  one place — then reads across all of it to tell you what
                  actually needs attention today.
                </p>

                <p className="mt-3.5 max-w-[60ch] text-body-md text-[rgb(var(--text-tertiary))]">
                  No guessing. Every insight is a count or a date you can check
                  on the same screen, with a button that opens the view where
                  you would fix it.
                </p>

                <div className="mt-8 flex flex-col gap-3 sm:flex-row sm:items-center">
                  <Link
                    to="/register"
                    className="btn-primary focus-ring group inline-flex items-center justify-center gap-2 rounded-xl px-7 py-3.5 text-[15px] font-semibold"
                  >
                    Create your LifeOS
                    <ArrowRight
                      className="h-4 w-4 transition-transform duration-200 group-hover:translate-x-1"
                      aria-hidden="true"
                    />
                  </Link>

                  <Link
                    to="/login"
                    className="btn-secondary focus-ring inline-flex items-center justify-center rounded-xl px-7 py-3.5 text-[15px] font-medium"
                  >
                    Sign in
                  </Link>
                </div>

                <p className="body-xs mt-5 text-[rgb(var(--text-muted))]">
                  Free to use · No card required · Your data stays scoped to your
                  account
                </p>
              </div>

              {/* Visual column. Below the copy on mobile, beside it on desktop.
                  `-mt-6` on mobile and `-mt-4` from `md` pull the visual up
                  into the composition rather than letting it trail the copy
                  down the page.

                  `min-w-0` is load-bearing, not decoration. This div is a grid
                  item, and a grid item's default `min-width: auto` resolves to
                  its *content-based minimum size* — its min-content width.
                  The visual contains `truncate` rows in HeroVisual, and
                  `truncate` is `white-space: nowrap`, so an insight detail like
                  "Target date passed 4 days ago…" has a min-content width of
                  its full unwrapped line (~520px), not of its longest word.
                  That min-content propagates up to here, the single implicit
                  grid track below `md` was sized to it instead of to the space
                  actually available, and the copy column inherited that same
                  over-wide track — so the h1, the paragraphs and the CTAs were
                  laid out far wider than the viewport and clipped by this
                  section's `overflow-hidden`.

                  `min-w-0` removes that floor, so the track is sized by the
                  space available. It has no effect at any width where the
                  visual already fits, because there the floor was never
                  binding and the item still stretches to fill the track. */}
              <div className="animate-fadeInUp -mt-6 min-w-0 [animation-delay:120ms] md:-mt-4">
                <HeroVisual />
              </div>
            </div>
          </div>
        </section>

        {/* ============================================================
            WHAT IT IS
            ============================================================ */}
        <Landmark
          id="product"
          eyebrow="What it is"
          title="A personal operating system for life, not another app to keep up with"
          lede={
            <>
              <p>
                Most personal tools are separate: a to-do list, a habit tracker,
                a calendar, a notes app, a spreadsheet for expenses. Each one is
                fine on its own, and none of them can see the others — so the
                work that actually matters gets lost between them.
              </p>
              <p className="mt-4">
                AI-LifeOS puts those domains on one shared model. A task, a
                goal, a note and a transaction are the same kind of record with
                different fields, which means linking a task to the goal it
                serves is a stored relationship rather than a copy-paste. And
                because the domains are connected, the system can read across
                them for you.
              </p>
            </>
          }
        >
          {/* The section header sits full width above this, so the block below
              is 1200px of grid holding one line of text per card. A lead
              column restores the page's editorial rhythm — and the lead-in is
              content that earns its space, not filler: it is the one-line
              summary the three cards then unpack.

              The split starts at `lg`, not `md`: at 768px a lead column would
              be squeezed to ~180px and the three cards to ~200px each, which
              reads as two cramped columns rather than a balanced one. */}
          <div className="grid gap-8 lg:grid-cols-[0.8fr_2.2fr] lg:gap-10">
            <Reveal>
              <p className="font-display text-[19px] font-semibold leading-[1.3] text-[rgb(var(--text-primary))] lg:sticky lg:top-24">
                One workspace, one record type, and insight that reads across
                both.
              </p>
            </Reveal>

            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {[
                {
                  icon: Layers,
                  title: 'One shared model',
                  body: 'Seven domains over one database. Linking across them is a column, not an integration.',
                },
                {
                  icon: Scale,
                  title: 'Recorded, not inferred',
                  body: 'Streaks count dated completions. Goal progress is a number you set. Nothing about you is guessed.',
                },
                {
                  icon: Crosshair,
                  title: 'Read back to you',
                  body: 'Connected data is turned into findings you can verify, each pointing at the view that fixes it.',
                },
              ].map((item, index) => (
                <Reveal key={item.title} delay={index * 90} className="h-full">
                  <div className="card h-full p-6">
                    <item.icon
                      className="h-5 w-5 text-[rgb(var(--accent))]"
                      aria-hidden="true"
                    />
                    <h3 className="mt-4 font-display text-[15px] font-semibold text-[rgb(var(--text-primary))]">
                      {item.title}
                    </h3>
                    <p className="body-sm mt-2 text-[rgb(var(--text-secondary))]">
                      {item.body}
                    </p>
                  </div>
                </Reveal>
              ))}
            </div>
          </div>
        </Landmark>

        {/* ============================================================
            DOMAINS
            ============================================================ */}
        <Landmark
          id="domains"
          tone="sunken"
          eyebrow="The system"
          title="Seven domains, each with a job, each connected to the others"
          lede="Grouped by what they do for you rather than listed as eight equal feature cards — because a to-do list and a habit streak are not the same kind of thing, even if both have checkboxes."
        >
          <div className="flex flex-col gap-16">
            {DOMAIN_GROUPS.map((group, groupIndex) => (
              <div key={group.id}>
                <Reveal className="max-w-[60ch]">
                  <div className="flex items-baseline gap-3">
                    <span className="mono-xs uppercase tracking-[0.18em] text-[rgb(var(--accent-secondary))]">
                      {group.eyebrow}
                    </span>
                    <span aria-hidden="true" className="h-px flex-1 bg-[rgb(var(--border-subtle))]" />
                  </div>
                  <h3 className="mt-3 font-display text-[19px] font-semibold text-[rgb(var(--text-primary))]">
                    {group.title}
                  </h3>
                  <p className="body-md mt-2 text-[rgb(var(--text-tertiary))]">
                    {group.body}
                  </p>
                </Reveal>

                {/* Staggered grid: one longer row first, then a pair. Reading
                    order stays left-to-right on desktop and stacks cleanly on
                    mobile, so the hierarchy survives a narrow viewport. */}
                <div className="mt-7 grid gap-4 md:grid-cols-2">
                  {group.domains.map((domain, index) => {
                    const Icon = ICONS[domain.icon] ?? Layers
                    const wide = index === 0 && group.domains.length === 3

                    return (
                      <Reveal
                        key={domain.name}
                        delay={index * 80}
                        className={`h-full ${wide ? 'md:col-span-2' : ''}`}
                      >
                        <article className="card card-interactive h-full p-6 md:p-7">
                          <div className="flex items-start gap-4">
                            <span className="grid h-11 w-11 shrink-0 place-items-center rounded-[14px] border border-[rgb(var(--accent)/0.25)] bg-[rgb(var(--accent-soft))]">
                              <Icon
                                className="h-5 w-5 text-[rgb(var(--accent))]"
                                aria-hidden="true"
                              />
                            </span>

                            <div className="min-w-0 flex-1">
                              <h4 className="font-display text-[16px] font-semibold text-[rgb(var(--text-primary))]">
                                {domain.name}
                              </h4>
                              <p className="mono-xs mt-1 text-[rgb(var(--text-tertiary))]">
                                {domain.line}
                              </p>
                            </div>
                          </div>

                          <p className="body-sm mt-4 text-[rgb(var(--text-secondary))]">
                            {domain.body}
                          </p>

                          <p className="body-xs mt-4 flex items-start gap-2 border-t border-[rgb(var(--border-subtle))] pt-4 text-[rgb(var(--text-tertiary))]">
                            <ArrowRight
                              className="mt-0.5 h-3.5 w-3.5 shrink-0 text-[rgb(var(--accent))]"
                              aria-hidden="true"
                            />
                            <span>{domain.connects}</span>
                          </p>
                        </article>
                      </Reveal>
                    )
                  })}
                </div>

                {groupIndex < DOMAIN_GROUPS.length - 1 ? (
                  <div
                    aria-hidden="true"
                    className="mt-16 h-px bg-[rgb(var(--border-subtle))]"
                  />
                ) : null}
              </div>
            ))}
          </div>
        </Landmark>

        {/* ============================================================
            INTELLIGENCE
            ============================================================ */}
        <Landmark
          id="intelligence"
          eyebrow="LifeOS Intelligence"
          title={
            <>
              It does not just store your data.{' '}
              <span className="text-[rgb(var(--accent))]">
                It reads across it
              </span>
              .
            </>
          }
          lede="Four stages, every one of them inspectable. This is the part that makes the system more than a set of tables — and the part that is deliberately the least magical thing here."
        >
          <ol className="grid gap-4 md:grid-cols-4">
            {INTELLIGENCE_PIPELINE.map((stage, index) => (
              <Reveal key={stage.label} as="li" delay={index * 90} className="h-full">
                <div className="card h-full p-5">
                  <span className="mono-xs text-accent">
                    {String(index + 1).padStart(2, '0')}
                  </span>
                  <h3 className="mt-2.5 font-display text-[15px] font-semibold text-[rgb(var(--text-primary))]">
                    {stage.label}
                  </h3>
                  <p className="body-xs mt-2 text-[rgb(var(--text-secondary))]">
                    {stage.body}
                  </p>
                </div>
              </Reveal>
            ))}
          </ol>

          {/* The honesty panel. This is the strongest claim on the page and the
              one most likely to sound like marketing, so it is stated as a
              contrast with what it deliberately does not do. */}
          <Reveal className="mt-8">
            <div className="card grid gap-8 p-7 md:grid-cols-[1.1fr_1fr] md:p-9">
              <div>
                <h3 className="font-display text-[17px] font-semibold text-[rgb(var(--text-primary))]">
                  Every insight is a count or a date
                </h3>
                <p className="body-md mt-3 text-[rgb(var(--text-secondary))]">
                  Insights come from named rules running over a snapshot of your
                  records. There is no model call, no API key, and no ranking
                  you cannot reproduce — the same data produces the same
                  insights, in the same order, every time you ask.
                </p>
                <p className="body-md mt-3 text-[rgb(var(--text-secondary))]">
                  It also means the system stops where the data stops. It will
                  tell you that a habit has no completions in the last fourteen
                  days. It will not tell you what that means about you.
                </p>
              </div>

              <div className="rounded-xl border border-[rgb(var(--border-subtle))] bg-[rgb(var(--bg-deep))] p-5">
                <p className="mono-xs mb-3 uppercase tracking-[0.16em] text-[rgb(var(--text-muted))]">
                  It says
                </p>
                <p className="font-mono text-[13px] leading-relaxed text-[rgb(var(--success))]">
                  &ldquo;3 of your 12 open tasks are past their due
                  date.&rdquo;
                </p>

                <p className="mono-xs mb-3 mt-5 uppercase tracking-[0.16em] text-[rgb(var(--text-muted))]">
                  It does not say
                </p>
                <p
                  className="font-mono text-[13px] leading-relaxed text-[rgb(var(--text-muted))] line-through"
                  style={{ textDecorationColor: 'rgb(var(--danger) / 0.5)' }}
                >
                  &ldquo;You are falling behind and losing focus.&rdquo;
                </p>
              </div>
            </div>
          </Reveal>

          {/* Insight list, mirroring the real card set. */}
          <div className="mt-8">
            <Reveal>
              <p className="body-sm mb-4 text-[rgb(var(--text-tertiary))]">
                The kinds of findings it produces:
              </p>
            </Reveal>

            <ul className="grid gap-3 sm:grid-cols-2">
              {[
                {
                  token: '--danger',
                  title: '3 overdue tasks',
                  detail:
                    '3 of your 12 open tasks are past their due date.',
                  action: 'Open tasks',
                },
                {
                  token: '--warning',
                  title: 'Ship onboarding redesign',
                  detail:
                    'Target date passed 4 days ago at 25% progress, with 6 incomplete linked tasks.',
                  action: 'Open goal',
                },
                {
                  token: '--accent-tertiary',
                  title: '4 days have 6+ events scheduled',
                  detail:
                    'Looking 14 days ahead, the busiest day is 2026-10-07 with 9 open events.',
                  action: 'Open planner',
                },
                {
                  token: '--success',
                  title: '14 transactions in 2026-10',
                  detail: 'Income ₹82,000 and expenses ₹31,450 recorded in 2026-10.',
                  action: 'Open finance',
                },
                {
                  token: '--accent',
                  title: '6 open tasks have no goal attached',
                  detail:
                    '6 of 12 open tasks are not linked to a goal, so they are not counted towards any goal’s progress.',
                  action: 'Open tasks',
                },
                {
                  token: '--accent-secondary',
                  title: '2 habits are on a streak',
                  detail: 'Longest active streak: Morning walk at 21 days.',
                  action: 'Open habits',
                },
              ].map((insight, index) => (
                <Reveal key={insight.title} as="li" delay={index * 60}>
                  <div
                    className="rounded-xl border p-4"
                    style={{
                      color: `rgb(var(${insight.token}))`,
                      backgroundColor: `rgb(var(${insight.token}) / 0.07)`,
                      borderColor: `rgb(var(${insight.token}) / 0.25)`,
                    }}
                  >
                    <p className="font-display text-[13.5px] font-semibold text-[rgb(var(--text-primary))]">
                      {insight.title}
                    </p>
                    <p className="body-xs mt-1.5 leading-relaxed text-[rgb(var(--text-secondary))]">
                      {insight.detail}
                    </p>
                    <p className="mono-xs mt-3 inline-flex items-center gap-1 text-[rgb(var(--text-primary))] opacity-80">
                      {insight.action}
                      <ArrowRight className="h-3 w-3" aria-hidden="true" />
                    </p>
                  </div>
                </Reveal>
              ))}
            </ul>
          </div>
        </Landmark>

        {/* ============================================================
            USE CASES
            ============================================================ */}
        <Landmark
          id="workflows"
          tone="sunken"
          eyebrow="How it works"
          title="What a day actually looks like"
          lede="Four rhythms the system is built around. Each is a real sequence of what the app does with your records."
        >
          <div className="grid gap-4 md:grid-cols-2">
            {USE_CASES.map((useCase, index) => (
              <Reveal key={useCase.id} delay={index * 80} className="h-full">
                <article className="card h-full p-6 md:p-7">
                  <span className="mono-xs text-accent inline-block rounded-full border border-[rgb(var(--border))] px-2.5 py-1">
                    {useCase.label}
                  </span>
                  <h3 className="mt-4 font-display text-[17px] font-semibold text-[rgb(var(--text-primary))]">
                    {useCase.title}
                  </h3>

                  <ol className="mt-5 flex flex-col gap-3.5">
                    {useCase.steps.map((step, stepIndex) => (
                      <li key={step} className="flex gap-3.5">
                        <span
                          aria-hidden="true"
                          className="mono-xs mt-0.5 grid h-5 w-5 shrink-0 place-items-center rounded-md border border-[rgb(var(--border))] text-[rgb(var(--text-muted))]"
                        >
                          {stepIndex + 1}
                        </span>
                        <span className="body-sm text-[rgb(var(--text-secondary))]">
                          {step}
                        </span>
                      </li>
                    ))}
                  </ol>
                </article>
              </Reveal>
            ))}
          </div>
        </Landmark>

        {/* ============================================================
            WHY
            ============================================================ */}
        <Landmark
          id="why"
          eyebrow="Why AI-LifeOS"
          title="Built to be checked, not believed"
          lede="No user counts, no benchmarks, no testimonials — there is nothing here to cite yet. These are the things that are true of how the software actually behaves."
        >
          <div className="grid gap-x-10 gap-y-9 sm:grid-cols-2 lg:grid-cols-3">
            {REASONS.map((reason, index) => {
              const Icon = ICONS[reason.icon] ?? Layers

              return (
                <Reveal key={reason.title} delay={index * 70}>
                  <div>
                    <Icon
                      className="h-5 w-5 text-[rgb(var(--accent))]"
                      aria-hidden="true"
                    />
                    <h3 className="mt-3.5 font-display text-[15px] font-semibold text-[rgb(var(--text-primary))]">
                      {reason.title}
                    </h3>
                    <p className="body-sm mt-2 text-[rgb(var(--text-secondary))]">
                      {reason.body}
                    </p>
                  </div>
                </Reveal>
              )
            })}
          </div>
        </Landmark>

        {/* ============================================================
            AI COMMAND — honest about scope
            ============================================================ */}
        <Landmark
          id="assistant"
          tone="sunken"
          eyebrow="AI Command"
          title="A local assistant, and a specific one"
          lede={
            <>
              <p>
                AI Command runs a small language model on your own machine — no
                key, no account, nothing sent to a hosted service. You can write
                a plain instruction and it will act on your records.
              </p>
              <p className="mt-4">
                It is also narrow on purpose, and worth being precise about what
                that means in practice.
              </p>
            </>
          }
        >
          <div className="grid gap-4 md:grid-cols-2">
            <Reveal className="h-full">
              <div className="card h-full p-6 md:p-7">
                <h3 className="font-display text-[15px] font-semibold text-[rgb(var(--success))]">
                  What it does
                </h3>
                <ul className="mt-4 flex flex-col gap-2.5">
                  {[
                    'Create, update, complete and delete tasks, goals and habits by name',
                    'Ask for your day’s plan, generated from pending tasks and active habits',
                    'Answer plain questions about your own counts and streaks',
                    'Accept English or Hinglish',
                  ].map(item => (
                    <li
                      key={item}
                      className="flex gap-2.5 text-body-sm text-[rgb(var(--text-secondary))]"
                    >
                      <span
                        aria-hidden="true"
                        className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-[rgb(var(--success))]"
                      />
                      {item}
                    </li>
                  ))}
                </ul>

                <div className="mt-6 rounded-lg border border-[rgb(var(--border-subtle))] bg-[rgb(var(--bg-deep))] p-3.5">
                  <p className="mono-xs mb-2 text-[rgb(var(--text-muted))]">
                    You type
                  </p>
                  <p className="font-mono text-[12.5px] text-[rgb(var(--text-primary))]">
                    &ldquo;aaj ka plan dikha&rdquo;
                  </p>
                  <p className="mono-xs mb-2 mt-3.5 text-[rgb(var(--text-muted))]">
                    It runs the plan tool and returns your real schedule
                  </p>
                </div>
              </div>
            </Reveal>

            <Reveal delay={90} className="h-full">
              <div className="card h-full p-6 md:p-7">
                <h3 className="font-display text-[15px] font-semibold text-[rgb(var(--text-tertiary))]">
                  What it does not do
                </h3>
                <ul className="mt-4 flex flex-col gap-2.5">
                  {[
                    'It does not read the web, your email, your files or your calendar',
                    'It does not act on your computer outside the app',
                    'It does not manage finance, planner events or notes',
                    'Every other feature works with the model switched off',
                  ].map(item => (
                    <li
                      key={item}
                      className="flex gap-2.5 text-body-sm text-[rgb(var(--text-tertiary))]"
                    >
                      <span
                        aria-hidden="true"
                        className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-[rgb(var(--text-muted))]"
                      />
                      {item}
                    </li>
                  ))}
                </ul>

                <div className="mt-6 flex items-start gap-2.5 rounded-lg border border-[rgb(var(--border-subtle))] bg-[rgb(var(--bg-deep))] p-3.5">
                  <WifiOff
                    className="mt-0.5 h-4 w-4 shrink-0 text-[rgb(var(--text-muted))]"
                    aria-hidden="true"
                  />
                  <p className="body-xs text-[rgb(var(--text-tertiary))]">
                    If the model is not running, the assistant says so and shows
                    your verified records instead of guessing. The rest of
                    AI-LifeOS is unaffected.
                  </p>
                </div>
              </div>
            </Reveal>
          </div>
        </Landmark>

        {/* ============================================================
            GET STARTED
            ============================================================ */}
        <Landmark
          id="get-started"
          eyebrow="Getting started"
          title="Two steps to your own LifeOS"
          lede="That is the whole first run. Nothing to configure, nothing to import, and no sales call."
        >
          {/* Two steps means two cards, which would leave the right half of a
              3/4-width container empty. Rather than stretch them to fill it —
              which would make two small facts look enormous — the second
              column carries the consequence of step 2 as prose. Real content,
              no filler, and the section keeps its asymmetric editorial shape. */}
          <div className="grid gap-8 md:grid-cols-[1.05fr_0.95fr] md:items-center md:gap-14">
            <ol className="grid gap-4">
              {GET_STARTED_STEPS.map((item, index) => (
                <Reveal key={item.step} as="li" delay={index * 90}>
                  <div className="card flex gap-5 p-6">
                    <span className="font-display text-[26px] font-bold leading-none text-[rgb(var(--accent)/0.35)]">
                      {item.step}
                    </span>
                    <div className="min-w-0">
                      <h3 className="font-display text-[15px] font-semibold text-[rgb(var(--text-primary))]">
                        {item.title}
                      </h3>
                      <p className="body-sm mt-2 text-[rgb(var(--text-secondary))]">
                        {item.body}
                      </p>
                    </div>
                  </div>
                </Reveal>
              ))}
            </ol>

            <Reveal delay={140}>
              <div className="border-l border-[rgb(var(--border-subtle))] pl-6 md:pl-8">
                <span className="mono-xs text-accent uppercase tracking-[0.16em]">
                  After that
                </span>
                <h3 className="mt-3 font-display text-[19px] font-semibold text-[rgb(var(--text-primary))]">
                  {GET_STARTED_AFTER.title}
                </h3>
                <p className="body-md mt-3 text-[rgb(var(--text-secondary))]">
                  {GET_STARTED_AFTER.body}
                </p>
              </div>
            </Reveal>
          </div>

          <Reveal className="mt-10">
            <div className="card flex flex-col items-start gap-7 p-7 md:flex-row md:items-center md:justify-between md:p-9">
              <div className="max-w-[52ch]">
                <h3 className="font-display text-[19px] font-semibold text-[rgb(var(--text-primary))]">
                  Start with one task
                </h3>
                <p className="body-md mt-2.5 text-[rgb(var(--text-secondary))]">
                  That is enough for the system to have something to read. Add
                  more once you can see what it tells you.
                </p>
              </div>

              <Link
                to="/register"
                className="btn-primary focus-ring group inline-flex w-full shrink-0 items-center justify-center gap-2 rounded-xl px-7 py-3.5 text-[15px] font-semibold sm:w-auto"
              >
                Create your LifeOS
                <ArrowRight
                  className="h-4 w-4 transition-transform duration-200 group-hover:translate-x-1"
                  aria-hidden="true"
                />
              </Link>
            </div>
          </Reveal>
        </Landmark>
      </main>

      {/* ============================================================
          FOOTER
          ============================================================ */}
      <footer className="border-t border-[rgb(var(--border))] bg-[rgb(var(--bg-deep))]">
        <div className="mx-auto w-full max-w-[1200px] px-5 py-14 sm:px-8">
          <div className="flex flex-col gap-10 md:flex-row md:justify-between">
            <div className="max-w-[40ch]">
              <PublicBrand />
              <p className="body-sm mt-4 text-[rgb(var(--text-tertiary))]">
                A personal operating system for tasks, goals, habits, planning,
                notes and money — with intelligence you can check the arithmetic
                on.
              </p>
            </div>

            <nav aria-label="Footer" className="flex gap-14 sm:gap-20">
              <div>
                <h2 className="mono-xs mb-3.5 uppercase tracking-[0.16em] text-[rgb(var(--text-muted))]">
                  Product
                </h2>
                <ul className="flex flex-col gap-2.5">
                  {[
                    { label: 'What it is', href: '#product' },
                    { label: 'Domains', href: '#domains' },
                    { label: 'Intelligence', href: '#intelligence' },
                    { label: 'How it works', href: '#workflows' },
                    { label: 'Why', href: '#why' },
                    { label: 'AI Command', href: '#assistant' },
                  ].map(item => (
                    <li key={item.href}>
                      <a
                        href={item.href}
                        className="focus-ring rounded text-body-sm text-[rgb(var(--text-tertiary))] transition-colors hover:text-[rgb(var(--text-primary))]"
                      >
                        {item.label}
                      </a>
                    </li>
                  ))}
                </ul>
              </div>

              <div>
                <h2 className="mono-xs mb-3.5 uppercase tracking-[0.16em] text-[rgb(var(--text-muted))]">
                  Account
                </h2>
                <ul className="flex flex-col gap-2.5">
                  <li>
                    <Link
                      to="/register"
                      className="focus-ring rounded text-body-sm text-[rgb(var(--text-tertiary))] transition-colors hover:text-[rgb(var(--text-primary))]"
                    >
                      Get started
                    </Link>
                  </li>
                  <li>
                    <Link
                      to="/login"
                      className="focus-ring rounded text-body-sm text-[rgb(var(--text-tertiary))] transition-colors hover:text-[rgb(var(--text-primary))]"
                    >
                      Sign in
                    </Link>
                  </li>
                </ul>
              </div>
            </nav>
          </div>

          <div className="mt-12 flex flex-col gap-3 border-t border-[rgb(var(--border-subtle))] pt-7 sm:flex-row sm:items-center sm:justify-between">
            <p className="mono-xs text-[rgb(var(--text-muted))]">
              © {new Date().getFullYear()} AI-LifeOS
            </p>
            <p className="mono-xs text-[rgb(var(--text-muted))]">
              One system · Explainable insight · Your data, your account
            </p>
          </div>
        </div>
      </footer>
    </div>
  )
}

export default LandingPage
