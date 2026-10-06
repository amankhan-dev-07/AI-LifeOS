import React from 'react'
import {
  AlertCircle,
  Target,
  TrendingDown,
  TriangleAlert,
  CalendarDays,
  ArrowUpRight,
  ShieldCheck,
} from 'lucide-react'
import type { Insight, InsightType, IntelligenceResponse } from '../../types'

/**
 * Attention Center — triage, not a repeat of the item list.
 *
 * Each row answers "how bad is it, and where do I go", not "what exactly is it".
 * The items themselves are rendered once, by the Today & Next section below, so
 * nothing on the page is shown twice. This block exists to let the dashboard be
 * triaged in a single glance.
 *
 * Every count and every explanation is quoted from the backend:
 *   - overdue, due-soon and open counts come from the `AttentionSummary` the
 *     rule engine computed on this request;
 *   - goal-risk, habit-slip, load and planning rows are counted from the
 *     per-entity insights, and reuse the rule engine's own `detail` wording.
 *
 * Nothing is ranked or judged here. There is no synthetic "priority score" —
 * rows are ordered by the backend's `priority` field, which is an ordinal the
 * rule engine assigned, not a number this UI invented.
 */

type IconComponent = React.ComponentType<{ className?: string }>

interface TriageRow {
  key: string
  count: number
  title: string
  detail: string
  route: string
  actionLabel: string
  icon: IconComponent
  tint: string;
  accent: string;
}

const ICON: Record<string, IconComponent> = {
  overdue: AlertCircle,
  goal_risk: Target,
  habit_consistency: TrendingDown,
  task_load: TriangleAlert,
  planning: CalendarDays,
}

const TINT: Record<string, string> = {
  overdue: 'bg-[rgb(var(--danger) / 0.12)] border-[rgb(var(--danger) / 0.3)] text-[rgb(var(--danger))]',
  goal_risk: 'bg-[rgb(var(--warning) / 0.12)] border-[rgb(var(--warning) / 0.3)] text-[rgb(var(--warning))]',
  habit_consistency: 'bg-[rgb(var(--accent) / 0.12)] border-[rgb(var(--accent) / 0.3)] text-[rgb(var(--accent))]',
  task_load: 'bg-[rgb(var(--warning) / 0.12)] border-[rgb(var(--warning) / 0.3)] text-[rgb(var(--warning))]',
  planning: 'bg-[rgb(var(--accent-tertiary) / 0.12)] border-[rgb(var(--accent-tertiary) / 0.3)] text-[rgb(var(--accent-tertiary))]',
}

const ACCENT: Record<string, string> = {
  overdue: 'border-l-[rgb(var(--danger))]',
  goal_risk: 'border-l-[rgb(var(--warning))]',
  habit_consistency: 'border-l-[rgb(var(--accent))]',
  task_load: 'border-l-[rgb(var(--warning))]',
  planning: 'border-l-[rgb(var(--accent-tertiary))]',
}

const ROUTE: Record<string, string> = {
  overdue: 'tasks',
  goal_risk: 'goals',
  habit_consistency: 'habits',
  task_load: 'tasks',
  planning: 'planner',
}

const ACTION: Record<string, string> = {
  overdue: 'Open tasks',
  goal_risk: 'Open goals',
  habit_consistency: 'Open habits',
  task_load: 'Review load',
  planning: 'Open planner',
}

const PRIORITY_ORDER = { high: 0, medium: 1, low: 2 } as const;

/**
 * How many rows of a given insight type exist, keyed by type.
 *
 * Only the four per-entity / aggregate rule types are counted. `finance`,
 * `data_quality` and `reminder` are deliberately excluded: the finance section
 * reports the money figures directly and reminders have no destination view in
 * this app, so a triage row pointing at them would have nothing to open.
 */
function countByType(insights: Insight[], types: InsightType[]): Map<InsightType, number> {
  const counts = new Map<InsightType, number>();
  insights.forEach((insight) => {
    if (types.includes(insight.type)) {
      counts.set(insight.type, (counts.get(insight.type) ?? 0) + 1);
    }
  });
  return counts;
}

function plural(count: number, singular: string, pluralForm: string): string {
  return count === 1 ? singular : pluralForm;
}

interface AttentionCenterProps {
  data: IntelligenceResponse;
  onNavigate: (route: string) => void;
}

export const AttentionCenter: React.FC<AttentionCenterProps> = ({ data, onNavigate }) => {
  const { summary, insights } = data;

  // The representative row for each type: the highest-priority insight of that
  // type. Its `detail` is quoted verbatim so the explanation stays exactly as
  // the rule engine derived it.
  const representative = new Map<InsightType, Insight>();
  insights.forEach((insight) => {
    if (!(insight.type in ICON)) return;
    const current = representative.get(insight.type);
    if (
      !current ||
      (PRIORITY_ORDER[insight.priority] ?? 3) < (PRIORITY_ORDER[current.priority] ?? 3)
    ) {
      representative.set(insight.type, insight);
    }
  });

  const counts = countByType(insights, ['goal_risk', 'habit_consistency', 'task_load', 'planning']);

  const goalRisks = counts.get('goal_risk') ?? 0;
  const habitSlips = counts.get('habit_consistency') ?? 0;
  const loadFindings = counts.get('task_load') ?? 0;
  const planningFindings = counts.get('planning') ?? 0;

  const rows: TriageRow[] = [];

  if (summary.overdue_count > 0) {
    rows.push({
      key: 'overdue',
      count: summary.overdue_count,
      title: plural(summary.overdue_count, 'overdue task', 'overdue tasks'),
      detail: 'Past their due date and still open. Each one is listed in Today & next.',
      route: ROUTE.overdue,
      actionLabel: ACTION.overdue,
      icon: ICON.overdue,
      tint: TINT.overdue,
      accent: ACCENT.overdue,
    });
  }

  if (goalRisks > 0) {
    rows.push({
      key: 'goal_risk',
      count: goalRisks,
      title: plural(goalRisks, 'goal at risk', 'goals at risk'),
      detail: representative.get('goal_risk')?.detail ?? '',
      route: ROUTE.goal_risk,
      actionLabel: ACTION.goal_risk,
      icon: ICON.goal_risk,
      tint: TINT.goal_risk,
      accent: ACCENT.goal_risk,
    });
  }

  if (habitSlips > 0) {
    rows.push({
      key: 'habit_consistency',
      count: habitSlips,
      title: plural(habitSlips, 'habit slipping', 'habits slipping'),
      detail: representative.get('habit_consistency')?.detail ?? '',
      route: ROUTE.habit_consistency,
      actionLabel: ACTION.habit_consistency,
      icon: ICON.habit_consistency,
      tint: TINT.habit_consistency,
      accent: ACCENT.habit_consistency,
    });
  }

  if (loadFindings > 0) {
    rows.push({
      key: 'task_load',
      count: loadFindings,
      title: 'heavy task load',
      detail: representative.get('task_load')?.detail ?? '',
      route: ROUTE.task_load,
      actionLabel: ACTION.task_load,
      icon: ICON.task_load,
      tint: TINT.task_load,
      accent: ACCENT.task_load,
    });
  }

  if (planningFindings > 0) {
    rows.push({
      key: 'planning',
      count: planningFindings,
      title: 'planning issue',
      detail: representative.get('planning')?.detail ?? '',
      route: ROUTE.planning,
      actionLabel: ACTION.planning,
      icon: ICON.planning,
      tint: TINT.planning,
      accent: ACCENT.planning,
    });
  }

  return (
    <section aria-label="Needs your attention" className="card-secondary p-6 stagger-in">
      {/* Editorial header instead of an icon tile + box. The tile carried the
          same danger tint as the first row's own severity marker, so a single
          overdue task put two red signals side by side in the header. */}
      <div className="section-header">
        <div className="min-w-0">
          <p className="section-header-label">
            {rows.length > 0 ? (
              <AlertCircle className="w-3.5 h-3.5 !text-[rgb(var(--danger))]" />
            ) : (
              <ShieldCheck className="w-3.5 h-3.5 !text-[rgb(var(--success))]" />
            )}
            Requires you
          </p>
          <h2 className="section-header-title mt-2">Needs your attention</h2>
        </div>
        {rows.length > 0 && (
          <span className="typo-micro shrink-0 !tracking-[0.14em]">
            {rows.length} {plural(rows.length, 'issue', 'issues')}
          </span>
        )}
      </div>

      {rows.length === 0 ? (
        <AllClear level={summary.level} />
      ) : (
        /* One container, hairline-separated rows. Each row previously carried
           its own border *and* a 2px severity stripe *and* a filled 40px icon
           tile, so five findings rendered as five competing boxes. The stripe
           now reads as the row's only severity marker. */
        <ul className="row-stack mt-4">
          {rows.map((row, i) => (
            <li
              key={row.key}
              className={`row-item !items-start !border-l-2 !border-l-[transparent] !pl-5 !pr-4 ${row.accent} stagger-in-fast`}
              style={{ animationDelay: `${i * 40}ms` }}
            >
              <span
                className={`w-9 h-9 shrink-0 grid place-items-center rounded-lg border ${row.tint} -ml-1`}
                aria-hidden="true"
              >
                <row.icon className="w-4 h-4" />
              </span>

              <div className="min-w-0 flex-1">
                <div className="flex items-start justify-between gap-3">
                  <p className="typo-body-sm !text-[rgb(var(--text-primary))] !font-medium !leading-tight">
                    {row.title}
                  </p>
                  <span className="typo-numeric shrink-0 text-xl font-bold leading-none text-[rgb(var(--text-primary))]">
                    {row.count}
                  </span>
                </div>

                {row.detail && <p className="typo-meta mt-1.5 !text-xs">{row.detail}</p>}

                <button
                  onClick={() => onNavigate(row.route)}
                  className="mt-2 inline-flex items-center gap-1 text-[11px] font-medium text-accent text-accent-hover transition-colors focus-ring rounded"
                >
                  {row.actionLabel}
                  <ArrowUpRight className="w-3 h-3" />
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
};

const AllClear: React.FC<{ level: string }> = ({ level }) => (
  <div className="text-center py-8">
    <p className="typo-body !font-medium">
      {level === 'clear' ? 'All clear' : 'Nothing urgent right now'}
    </p>
    <p className="typo-meta mt-1.5 max-w-[46ch] mx-auto">
      No overdue work, at-risk goals, slipping habits, or overloaded days in your current data.
      Standing observations are further down this page.
    </p>
  </div>
);