/**
 * Every string rendered on the public landing page lives here.
 *
 * Two reasons it is a module and not inline JSX:
 *
 *  1. Reviewability. Marketing copy is the part of this codebase most likely
 *     to drift out of sync with the product, and a single file makes that
 *     drift obvious. If a capability is added or removed, this is the one
 *     place to change it.
 *
 *  2. Honesty. `ILLUSTRATIVE_*` markers are deliberate. Every example on this
 *     page is either a verbatim string format lifted from backend code, or a
 *     clearly-labelled illustration. Nothing here asserts a statistic, a
 *     customer, an integration or a benchmark, because the product has none.
 */

/**
 * Insight strings below are the real output shapes of
 * `backend/app/services/intelligence_rules_service.py`, populated with the
 * figures from one example account. They are presented as a sample of a
 * populated LifeOS — not as live data, and not as a claim about anyone's
 * actual results.
 */
export const ILLUSTRATIVE_INSIGHTS = [
  {
    tone: 'danger' as const,
    title: '3 overdue tasks',
    detail: '3 of your 12 open tasks are past their due date.',
    action: 'Open tasks',
  },
  {
    tone: 'warning' as const,
    title: 'Ship onboarding redesign',
    detail:
      'Target date passed 4 days ago at 25% progress, with 6 incomplete linked tasks.',
    action: 'Open goal',
  },
  {
    tone: 'info' as const,
    title: '2 days have 6+ events scheduled',
    detail: 'Looking 14 days ahead, the busiest day is 2026-10-07 with 9 open events.',
    action: 'Open planner',
  },
  {
    tone: 'neutral' as const,
    title: '14 transactions in 2026-10',
    detail: 'Income ₹82,000 and expenses ₹31,450 recorded in 2026-10.',
    action: 'Open finance',
  },
]

/** The four stages of the Intelligence pipeline, shown as a flow. */
export const INTELLIGENCE_PIPELINE = [
  {
    label: 'Your records',
    body: 'Tasks, goals, habits, planner events, notes and transactions are read from your own database rows.',
  },
  {
    label: 'Context',
    body: 'Those rows are snapshotted into one scoped view: overdue counts, completion windows, target dates, monthly totals.',
  },
  {
    label: 'Insight',
    body: 'Named rules run over that snapshot. Same data in, same insights out, in the same order — every time.',
  },
  {
    label: 'Action',
    body: 'Each insight carries a button that opens the view where you would fix it. Nothing dead-ends.',
  },
]

/**
 * Domain groups, ordered by role rather than alphabetically. Three execution
 * domains, two context domains, two personal domains — then Intelligence,
 * which is presented separately because it is the layer that reads across all
 * of them rather than another peer box.
 */
export const DOMAIN_GROUPS = [
  {
    id: 'execution',
    eyebrow: 'Daily',
    title: 'What you do',
    body: 'The parts of a day you can act on. These are where the day gets spent.',
    domains: [
      {
        icon: 'CheckSquare',
        name: 'Tasks',
        line: 'What needs doing',
        body: 'A task carries a title, a priority, an optional due date, and an optional link to the goal it serves. Overdue and due-soon are derived from the date, not typed in by hand.',
        connects: 'Link a task to a goal and it starts counting toward that goal.',
      },
      {
        icon: 'Activity',
        name: 'Habits',
        line: 'What you repeat',
        body: 'A habit is a routine with a frequency you set. Every check-in is stored with its date — that record is what makes a current streak and a longest streak computable rather than guessed.',
        connects: 'Streaks feed the consistency insight, which compares 14-day and 30-day completion counts.',
      },
      {
        icon: 'Calendar',
        name: 'Planner',
        line: 'When it happens',
        body: 'Planner events put things on a specific day, so time is blocked instead of assumed. Fired reminders surface here too, because a reminder is really a time with a title on it.',
        connects: 'Day-level counts feed the planning insight, which flags unusually busy days.',
      },
    ],
  },
  {
    id: 'direction',
    eyebrow: 'Longer arc',
    title: 'Why you are doing it',
    body: 'Direction and context. These are what make the daily list mean something.',
    domains: [
      {
        icon: 'Target',
        name: 'Goals',
        line: 'What you want to achieve',
        body: 'A goal holds a progress percentage, a category, an optional target date, and the tasks linked to it. Progress is a number you set — the app never infers it. The target date is what lets the goal be checked against a schedule.',
        connects: 'Linked tasks, plus elapsed time against recorded progress, drive goal-risk findings.',
      },
      {
        icon: 'StickyNote',
        name: 'Notes',
        line: 'What you need to remember',
        body: 'Written context with tags, and an optional link to a goal or task — so a decision keeps the reason it was made, not just the outcome.',
        connects: 'Searchable from the same global search box as every other domain.',
      },
    ],
  },
  {
    id: 'personal',
    eyebrow: 'Personal',
    title: 'Your own record',
    body: 'The parts of life that are yours alone, kept private and kept with the same care.',
    domains: [
      {
        icon: 'Wallet',
        name: 'Finance',
        line: 'Where money goes',
        body: 'Income and expenses recorded as transactions, totalled per calendar month and grouped by category. A factual summary of what came in and what went out.',
        connects: 'The monthly total and most-frequent category are surfaced as one insight.',
      },
      {
        icon: 'BellRing',
        name: 'Reminders',
        line: 'What should not slip',
        body: 'A reminder fires at a time you set, attached to a task, a habit or a planner block. It moves from pending to completed or cancelled, so its state is always knowable.',
        connects: 'A reminder still pending after it fired is a real, dated follow-up — not a guess.',
      },
      {
        icon: 'Search',
        name: 'Search & Notifications',
        line: 'Finding and knowing',
        body: 'One search box across tasks, goals, habits, notes, planner events and transactions, with each result carrying the view to open it in. A notification log records what fired, with unread counts on the header.',
        connects: 'Search returns a route per result, so jumping to a record is one click.',
      },
    ],
  },
]

/** Use-case narratives. Concrete sequences, not personas with adjectives. */
export const USE_CASES = [
  {
    id: 'morning',
    label: 'Morning',
    title: 'Open the day already arranged',
    steps: [
      'The dashboard reads your overdue count, open tasks and today’s planner blocks.',
      'The attention panel tells you what needs attention, with a button that opens the right view.',
      'The daily plan is generated from your pending tasks and active habits, blocked into time.',
    ],
  },
  {
    id: 'during',
    label: 'During the day',
    title: 'Work the list without re-planning',
    steps: [
      'Complete tasks and check in habits; each check-in writes a dated record.',
      'Planner events hold the shape of the day.',
      'Reminders fire at their time and land in notifications, so nothing depends on you remembering to look.',
    ],
  },
  {
    id: 'long-term',
    label: 'Over months',
    title: 'See whether the goals are real',
    steps: [
      'Tasks link to goals, so progress reflects actual outstanding work.',
      'A target date plus recorded progress is enough to flag a goal sitting behind its own schedule.',
      'Insight follows the data rather than your memory of it.',
    ],
  },
  {
    id: 'personal',
    label: 'Personal',
    title: 'Keep the rest of life in the same place',
    steps: [
      'Notes hold written context, linkable to a goal or task.',
      'Transactions are totalled per month by category.',
      'Global search spans every domain from one box.',
    ],
  },
]

/** Differentiation claims, each tied to observable behaviour. */
export const REASONS = [
  {
    icon: 'Layers',
    title: 'One connected system, not seven tools',
    body: 'Tasks, goals, habits, planner, notes, finance and reminders share one database and one search box. A note and a task and a goal are the same kind of object with different fields — so linking between them is a column, not an integration.',
  },
  {
    icon: 'Scale',
    title: 'Intelligence you can check the arithmetic on',
    body: 'Every insight is assembled from counts and dates already on your screen. There is no model call, no API key and no ranking you cannot reproduce. If it says 3 tasks are overdue, it counted 3.',
  },
  {
    icon: 'Crosshair',
    title: 'Insights that carry an action',
    body: 'An insight names a view that already exists and a button to open it. No dead-end advice, and no route invented for a page that does not exist.',
  },
  {
    icon: 'Lock',
    title: 'Scoped to you, by construction',
    body: 'The user is resolved from the bearer token on every request — no client-supplied user id is accepted anywhere in the read path. Your data is not queryable by another account.',
  },
  {
    icon: 'Database',
    title: 'Records, not streaks of optimism',
    body: 'Habit completions are dated rows, so a streak is a count you can audit. Goal progress is set by you and never guessed at.',
  },
  {
    icon: 'WifiOff',
    title: 'The model is not the product',
    body: 'Ask in plain English or Hinglish through a locally-run model, for creating and updating records and asking about your day. Everything else — including all of Intelligence — works with no model running at all.',
  },
]

/**
 * The onboarding bridge.
 *
 * These are the two steps of the actual first-run flow, and nothing else. An
 * earlier version of this page listed three and described the second one as
 * collecting timezone, time format, theme and planning hours — all of which is
 * wrong: `OnboardingFlow` collects none of it (those live in Settings), and it
 * is a two-step sequence by design.
 *
 * Whatever is added to the real flow must be reflected here, and vice versa.
 */
export const GET_STARTED_STEPS = [
  {
    step: '01',
    title: 'Create an account',
    body: 'Name, email, password. No card, no trial countdown, no sales call.',
  },
  {
    step: '02',
    title: 'Add your first thing',
    body: 'A two-step first run: see every domain AI-LifeOS manages, then create one real record — a task, goal, habit or planner block — and watch the dashboard fill in around it.',
  },
]

/**
 * What happens after the steps, in its own line. Deliberately not a numbered
 * step: it is a consequence of step 2, not a screen the user passes through.
 */
export const GET_STARTED_AFTER = {
  title: 'Then the insights start',
  body: 'With a record in place, the attention panel and the insight rules have something to describe. An account with nothing in it says so plainly rather than guessing.',
}
