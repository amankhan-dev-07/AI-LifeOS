"""
Deterministic insight rules.

This is the "Insight" half of Context → Insight → Actionable Suggestion. Each
function takes the snapshot, inspects one concern, and returns zero or more
`Insight` objects. There is no scoring model, no learned ranking, and no model
call: given the same snapshot, these rules produce the same insights, in the
same order, every time.

Rules of the house
------------------
1. **Explainable.** Every `detail` string is assembled from counts and dates
   the user could verify on the same screen. No rule infers a cause, a motive,
   a mood, or a state of mind. "3 tasks are overdue" is allowed; "you're
   falling behind" is not.
2. **No sensitive inference.** Nothing here touches health, mood, personality
   or diagnosis. Habit rules talk about *recorded completion counts*, never
   about how the user is doing.
3. **Actionable.** Each insight carries a `route` naming an existing view, or
   `None` when there is genuinely nowhere to send the user. A `route` is never
   invented for a page that does not exist.
4. **Aggregates over entities.** A rule about "12 overdue tasks" emits one
   insight, not twelve. Per-entity rows are emitted only when the specific
   entity carries information the aggregate does not — a goal's target date, a
   habit's own completion count — and they are capped.

Priority is a closed `low | medium | high` set assigned explicitly at each
call site, always by comparison against a named threshold from
`intelligence_context_service`. It is not a function of how many insights
exist, so adding a new rule can never silently re-rank the others.
"""

from app.schemas.intelligence import AttentionLevel, AttentionSummary, Insight
from app.services.intelligence_context_service import (
    DUE_SOON_HOURS,
    HABIT_CONSISTENCY_WINDOW_DAYS,
    HABIT_MIN_SAMPLE_SIZE,
    HABIT_RECENT_WINDOW_DAYS,
    MAX_ENTITY_INSIGHTS,
    PLANNER_BUSY_EVENTS_PER_DAY,
    PLANNER_HEAVY_EVENTS_PER_DAY,
    PLANNER_HORIZON_DAYS,
    TASK_LOAD_HIGH_THRESHOLD,
    TASK_LOAD_MEDIUM_THRESHOLD,
    LifeOSContext,
)


# Existing app view keys. These match the `activeTab` values in `App.tsx` and
# the `route` values Global Search already returns, so an insight can navigate
# by handing its `route` straight to the existing `setActiveTab`.
ROUTE_TASKS = "tasks"
ROUTE_GOALS = "goals"
ROUTE_HABITS = "habits"
ROUTE_PLANNER = "planner"
ROUTE_FINANCE = "finance"


# =========================================================
# 1. OVERDUE
# =========================================================


def overdue_rule(context: LifeOSContext) -> list[Insight]:
    """
    Open tasks whose due date has passed.

    One aggregate insight for the whole set — the count is the information —
    plus, only when the set is small enough to act on, a row for the single
    oldest task, which is the one a user would reach for first.
    """

    if context.task_overdue == 0:
        return []

    insights = [
        Insight(
            id="overdue_tasks",
            type="overdue",
            priority="high" if context.task_overdue >= 3 else "medium",
            domain="task",
            title=(
                f"{context.task_overdue} overdue "
                f"{'task' if context.task_overdue == 1 else 'tasks'}"
            ),
            detail=(
                f"{context.task_overdue} of your {context.task_incomplete} open "
                f"tasks are past their due date."
            ),
            metric=str(context.task_overdue),
            action_label="Open tasks",
            route=ROUTE_TASKS,
        )
    ]

    # Only name a specific task when the list is short enough that acting on
    # it is unambiguous. With 40 overdue tasks, singling one out would imply a
    # ranking the data does not support.
    if 1 <= context.task_overdue <= MAX_ENTITY_INSIGHTS and context.overdue_tasks:
        oldest = context.overdue_tasks[0]
        days_overdue = (context.generated_at - oldest.due_date).days

        insights.append(
            Insight(
                id=f"overdue_oldest:{oldest.id}",
                type="overdue",
                priority="medium",
                domain="task",
                title=oldest.title,
                detail=(
                    f"Oldest overdue task — due "
                    f"{oldest.due_date.strftime('%Y-%m-%d')}, "
                    f"{_overdue_phrase(days_overdue)}."
                ),
                action_label="Open tasks",
                route=ROUTE_TASKS,
                entity_type="task",
                entity_id=oldest.id,
            )
        )

    return insights


def _overdue_phrase(days: int) -> str:
    """'1 day overdue' / '4 days overdue', from an integer day difference."""

    if days < 1:
        return "overdue"

    return f"{days} {'day' if days == 1 else 'days'} overdue"


# =========================================================
# 2. TODAY / NEXT
# =========================================================


def upcoming_rule(context: LifeOSContext) -> list[Insight]:
    """Open tasks coming due soon."""

    if context.task_due_soon == 0:
        return []

    return [
        Insight(
            id="tasks_due_soon",
            type="upcoming",
            priority="medium",
            domain="task",
            title=(
                f"{context.task_due_soon} "
                f"{'task' if context.task_due_soon == 1 else 'tasks'} "
                f"due soon"
            ),
            detail=(
                f"{context.task_due_soon} open tasks are due within the next "
                f"{DUE_SOON_HOURS} hours."
            ),
            metric=str(context.task_due_soon),
            action_label="Open tasks",
            route=ROUTE_TASKS,
        )
    ]


# =========================================================
# 3. GOAL RISK
# =========================================================


def goal_risk_rule(context: LifeOSContext) -> list[Insight]:
    """
    Active goals whose recorded progress sits behind their own schedule.

    "Behind schedule" is computed, not asserted: a goal carries an explicit
    target date, so the comparison between elapsed time and recorded progress
    is arithmetic the user can redo. Goals with no target date are excluded —
    there is no schedule to compare against, and inventing one would be a
    causal claim the data does not support.
    """

    insights: list[Insight] = []

    for goal in context.goals:
        if goal.days_to_target is None:
            continue

        # Past its target and not finished is unambiguous.
        if goal.days_to_target < 0 and goal.progress < 100:
            insights.append(
                Insight(
                    id=f"goal_risk:{goal.id}",
                    type="goal_risk",
                    priority="high",
                    domain="goal",
                    title=goal.title,
                    detail=(
                        f"Target date passed {-goal.days_to_target} days ago "
                        f"at {goal.progress}% progress"
                        + (
                            f", with {goal.incomplete_task_count} incomplete "
                            "linked tasks."
                            if goal.incomplete_task_count
                            else "."
                        )
                    ),
                    metric=f"{goal.progress}%",
                    action_label="Open goal",
                    route=ROUTE_GOALS,
                    entity_type="goal",
                    entity_id=goal.id,
                )
            )
            continue

        # Within the final fortnight, and less than half done.
        if 0 <= goal.days_to_target <= 14 and goal.progress < 50:
            insights.append(
                Insight(
                    id=f"goal_risk:{goal.id}",
                    type="goal_risk",
                    priority="medium",
                    domain="goal",
                    title=goal.title,
                    detail=(
                        f"{goal.progress}% progress with "
                        f"{goal.days_to_target} "
                        f"{'day' if goal.days_to_target == 1 else 'days'} "
                        "until the target date"
                        + (
                            f" and {goal.incomplete_task_count} incomplete "
                            "linked tasks."
                            if goal.incomplete_task_count
                            else "."
                        )
                    ),
                    metric=f"{goal.progress}%",
                    action_label="Open goal",
                    route=ROUTE_GOALS,
                    entity_type="goal",
                    entity_id=goal.id,
                )
            )
            continue

    # A third branch — "elapsed time versus recorded progress" — is
    # deliberately absent. Measuring it needs the span between a goal's
    # creation and its target date, and `GoalSignal` does not carry
    # `created_at`. Adding it to the snapshot for one rule would mean shipping
    # a timestamp the UI never renders; guessing the window from the target
    # date alone would produce a ratio the user cannot verify. The two cases
    # above are the ones the stored data fully supports.

    return insights[:MAX_ENTITY_INSIGHTS]


# =========================================================
# 4. HABIT CONSISTENCY
# =========================================================


def habit_consistency_rule(context: LifeOSContext) -> list[Insight]:
    """
    Active habits whose recorded completions have dropped off, and the ones
    holding a streak.

    Two directions, both read off `habit_completions` rows and nothing else:

    * a streak at or above three days is reported as-is — the user set that
      number by checking in, so echoing it back is fact, not praise;
    * a habit with enough history to judge that recorded *no* completion in
      the last week is reported as an absence.

    A habit with fewer than `HABIT_MIN_SAMPLE_SIZE` completions in the window
    is skipped entirely. Its history is too thin to distinguish "inconsistent"
    from "recently added".
    """

    insights: list[Insight] = []

    streaks: list = []

    for habit in context.habits:
        if habit.current_streak >= 3:
            streaks.append(habit)

        if habit.completions_30d < HABIT_MIN_SAMPLE_SIZE:
            # Too little history to say anything about consistency.
            continue

        if habit.completions_14d == 0:
            days_since = habit.last_completed_on

            insights.append(
                Insight(
                    id=f"habit_gap:{habit.id}",
                    type="habit_consistency",
                    priority="medium",
                    domain="habit",
                    title=habit.title,
                    detail=(
                        f"{habit.completions_30d} completions in the last 30 "
                        f"days and none in the last "
                        f"{HABIT_RECENT_WINDOW_DAYS}"
                        + (
                            f" — last recorded "
                            f"{days_since.strftime('%Y-%m-%d')}."
                            if days_since is not None
                            else "."
                        )
                    ),
                    metric="0",
                    action_label="Open habit",
                    route=ROUTE_HABITS,
                    entity_type="habit",
                    entity_id=habit.id,
                )
            )
            continue

        # Sparse but not absent: some record, roughly a third of the window.
        if habit.completions_14d <= max(1, HABIT_CONSISTENCY_WINDOW_DAYS // 4):
            insights.append(
                Insight(
                    id=f"habit_sparse:{habit.id}",
                    type="habit_consistency",
                    priority="low",
                    domain="habit",
                    title=habit.title,
                    detail=(
                        f"{habit.completions_14d} completions in the last "
                        f"{HABIT_CONSISTENCY_WINDOW_DAYS} days "
                        f"({habit.frequency} habit)."
                    ),
                    metric=str(habit.completions_14d),
                    action_label="Open habit",
                    route=ROUTE_HABITS,
                    entity_type="habit",
                    entity_id=habit.id,
                )
            )

    # Cap the gap/sparse rows, but report the streak set as one aggregate so a
    # user with 20 habits does not lose the headline to a truncation.
    if len(insights) > MAX_ENTITY_INSIGHTS:
        insights = insights[:MAX_ENTITY_INSIGHTS]

    if streaks:
        best = max(streaks, key=lambda habit: habit.current_streak)

        insights.append(
            Insight(
                id="habit_streak",
                type="habit_consistency",
                priority="low",
                domain="habit",
                title=(
                    f"{len(streaks)} "
                    f"{'habit is' if len(streaks) == 1 else 'habits are'} "
                    f"on a streak"
                ),
                detail=(
                    f"Longest active streak: {best.title} at "
                    f"{best.current_streak} "
                    f"{'day' if best.current_streak == 1 else 'days'}."
                ),
                metric=str(best.current_streak),
                action_label="Open habits",
                route=ROUTE_HABITS,
            )
        )

    return insights


# =========================================================
# 5. PLANNING
# =========================================================


def planning_rule(context: LifeOSContext) -> list[Insight]:
    """
    Upcoming days carrying an unusual number of open planner events.

    The day-level `GROUP BY`/`HAVING` happens in the database, so this rule
    only ever sees days that already exceed
    `PLANNER_BUSY_EVENTS_PER_DAY`. Overlap detection is deliberately not
    attempted: it would need every event's start/end pair across the window,
    and a false "conflict" reported on a merely busy day is worse than saying
    nothing.
    """

    if not context.busy_days:
        return []

    heaviest = max(context.busy_days, key=lambda day: day.event_count)
    # Ensure consistent YYYY-MM-DD format for the insight ID regardless of
    # whether the DB driver returns a date object, datetime, or string.
    day = heaviest.day
    if hasattr(day, "strftime"):
        day_label = day.strftime("%Y-%m-%d")
    else:
        day_label = str(day)[:10]

    insights = [
        Insight(
            id="planner_busy_days",
            type="planning",
            priority="high"
            if heaviest.event_count >= PLANNER_HEAVY_EVENTS_PER_DAY
            else "medium",
            domain="planner",
            title=(
                f"{len(context.busy_days)} "
                f"{'day has' if len(context.busy_days) == 1 else 'days have'} "
                f"{PLANNER_BUSY_EVENTS_PER_DAY}+ events scheduled"
            ),
            detail=(
                f"Looking {PLANNER_HORIZON_DAYS} days ahead, the busiest day "
                f"is {day_label} with {heaviest.event_count} open events."
            ),
            metric=str(heaviest.event_count),
            action_label="Open planner",
            route=ROUTE_PLANNER,
        )
    ]

    # Call out the single heaviest day on its own when it clears the higher
    # threshold, so the user has one concrete day to act on.
    if heaviest.event_count >= PLANNER_HEAVY_EVENTS_PER_DAY:
        insights.append(
            Insight(
                id=f"planner_busy_day:{day_label}",
                type="planning",
                priority="high",
                domain="planner",
                title=f"{heaviest.event_count} events on {day_label}",
                detail=(
                    f"{heaviest.event_count} open events are scheduled on this "
                    "day alone."
                ),
                metric=str(heaviest.event_count),
                action_label="Open planner",
                route=ROUTE_PLANNER,
            )
        )

    return insights


# =========================================================
# 6. TASK LOAD
# =========================================================


def task_load_rule(context: LifeOSContext) -> list[Insight]:
    """
    An unusually large number of simultaneously open tasks.

    Thresholds are explicit constants, so "unusually large" means a specific,
    stated number rather than a comparison against the user's own history —
    which would drift as they use the product and would be unexplplainable in
    the moment.
    """

    if context.task_incomplete >= TASK_LOAD_HIGH_THRESHOLD:
        priority = "high"
    elif context.task_incomplete >= TASK_LOAD_MEDIUM_THRESHOLD:
        priority = "medium"
    else:
        return []

    return [
        Insight(
            id="task_load",
            type="task_load",
            priority=priority,
            domain="task",
            title=f"{context.task_incomplete} open tasks",
            detail=(
                f"You have {context.task_incomplete} tasks that are not "
                f"completed ({context.task_completed} completed in total)."
            ),
            metric=str(context.task_incomplete),
            action_label="Open tasks",
            route=ROUTE_TASKS,
        )
    ]


# =========================================================
# 7. FINANCE
# =========================================================


def finance_rule(context: LifeOSContext) -> list[Insight]:
    """
    Factual totals from the current calendar month.

    A summary, not advice: what came in, what went out, and how many entries
    that was. No spending judgement, no budget recommendation, no suggestion
    about what the user "should" change — the data supports none of that, and
    it is not this layer's role to give financial advice.
    """

    if context.finance is None:
        return []

    finance = context.finance

    period = finance.period_start.strftime("%Y-%m")

    insights = [
        Insight(
            id="finance_month",
            type="finance",
            priority="low",
            domain="finance",
            title=f"{finance.transaction_count} transactions in {period}",
            detail=(
                f"Income {finance.income_total} and expenses "
                f"{finance.expense_total} recorded in {period}."
            ),
            metric=str(finance.transaction_count),
            action_label="Open finance",
            route=ROUTE_FINANCE,
        )
    ]

    if finance.top_expense_categories:
        top = finance.top_expense_categories[0]

        insights.append(
            Insight(
                id="finance_top_category",
                type="finance",
                priority="low",
                domain="finance",
                title=f"Most frequent expense: {top.category}",
                detail=(
                    f"{top.category} was the most frequently recorded expense "
                    f"category in {period}."
                ),
                metric=top.category,
                action_label="Open finance",
                route=ROUTE_FINANCE,
            )
        )

    return insights


# =========================================================
# 8. REMINDER FOLLOW-UP
# =========================================================


def reminder_rule(context: LifeOSContext) -> list[Insight]:
    """
    Pending reminders that have already fired.

    A reminder past its time and still `pending` was delivered but never
    resolved — the one reminder state that means something actionable. The
    insight points at the planner, which is where reminders are surfaced in the
    UI, rather than at a reminders page that does not exist.
    """

    if not context.follow_up_reminders:
        return []

    count = len(context.follow_up_reminders)

    oldest = context.follow_up_reminders[0]

    return [
        Insight(
            id="reminder_follow_up",
            type="reminder",
            priority="medium",
            domain="reminder",
            title=(
                f"{count} "
                f"{'reminder is' if count == 1 else 'reminders are'} "
                f"still pending after firing"
            ),
            detail=(
                f"The oldest is “{oldest.title}”, set for "
                f"{oldest.remind_at.strftime('%Y-%m-%d %H:%M')} and not yet "
                "completed or cancelled."
            ),
            metric=str(count),
            action_label="Open planner",
            route=ROUTE_PLANNER,
        )
    ]


# =========================================================
# 9. DATA QUALITY / SETUP
# =========================================================


def data_quality_rule(context: LifeOSContext) -> list[Insight]:
    """
    Relationships that are missing, where the gap actually costs the user
    something intelligence.

    Two cases only:

    * open tasks with no goal attached — they cannot contribute to any goal's
      progress, so the goals page under-reports how much work is outstanding;
    * a brand-new account with nothing in any domain, which is the empty
      state rather than a finding.

    Habit and note gaps are deliberately not reported: neither is used as a
    progress signal by any other rule, so their absence changes nothing.
    """

    insights: list[Insight] = []

    if not context.has_data:
        insights.append(
            Insight(
                id="setup_empty",
                type="data_quality",
                priority="low",
                domain="system",
                title="No records yet",
                detail=(
                    "There are no tasks, goals, habits, notes, transactions "
                    "or reminders on this account yet. Insights appear once "
                    "there is something to describe."
                ),
                action_label="Create a task",
                route=ROUTE_TASKS,
            )
        )

        return insights

    if context.task_unlinked > 0:
        insights.append(
            Insight(
                id="tasks_without_goal",
                type="data_quality",
                priority="low",
                domain="task",
                title=(
                    f"{context.task_unlinked} open "
                    f"{'task has' if context.task_unlinked == 1 else 'tasks have'} "
                    f"no goal attached"
                ),
                detail=(
                    f"{context.task_unlinked} of {context.task_incomplete} open "
                    "tasks are not linked to a goal, so they are not counted "
                    "towards any goal's progress."
                ),
                metric=str(context.task_unlinked),
                action_label="Open tasks",
                route=ROUTE_TASKS,
            )
        )

    if context.goals_without_target_date > 0:
        insights.append(
            Insight(
                id="goals_without_target_date",
                type="data_quality",
                priority="low",
                domain="goal",
                title=(
                    f"{context.goals_without_target_date} active "
                    f"{'goal has' if context.goals_without_target_date == 1 else 'goals have'} "
                    f"no target date"
                ),
                detail=(
                    "Goals without a target date cannot be checked against a "
                    "schedule, so progress findings are not generated for them."
                ),
                metric=str(context.goals_without_target_date),
                action_label="Open goals",
                route=ROUTE_GOALS,
            )
        )

    return insights


# =========================================================
# SUMMARY
# =========================================================


def build_attention_summary(context: LifeOSContext) -> AttentionSummary:
    """
    The panel headline.

    `level` is a plain function of two counts the user can see for themselves —
    overdue tasks and open tasks — never of how many insights fired or of any
    notion of the user's state. An account with no data reads as `clear` rather
    than alarming.

    Reminders get a say because they are the one domain with a hard deadline:
    a pending reminder past its time is a thing that already happened.
    """

    if not context.has_data:
        return AttentionSummary(
            level="clear",
            headline="Nothing to analyse yet",
            detail=(
                "Once there are tasks, goals, habits or transactions on this "
                "account, this panel will summarise what needs attention."
            ),
            overdue_count=0,
            due_soon_count=0,
            incomplete_task_count=context.task_incomplete,
            unread_notification_count=context.unread_notifications,
        )

    follow_ups = len(context.follow_up_reminders)

    if context.task_overdue >= 3 or context.task_incomplete >= TASK_LOAD_HIGH_THRESHOLD:
        level: AttentionLevel = "busy"
    elif context.task_overdue > 0 or follow_ups > 0:
        level = "watch"
    else:
        level = "clear"

    if level == "busy":
        headline = "Several things need attention"

        # `busy` can be reached on load alone, with nothing overdue at all, so
        # the overdue clause is only stated when there is a count to state.
        parts = []

        if context.task_overdue:
            parts.append(
                f"{context.task_overdue} overdue "
                f"{'task' if context.task_overdue == 1 else 'tasks'}"
            )

        parts.append(
            f"{context.task_incomplete} open "
            f"{'task' if context.task_incomplete == 1 else 'tasks'} in total"
        )

        detail = ", ".join(parts) + "."
    elif level == "watch":
        headline = "A few things need attention"
        parts = []

        if context.task_overdue:
            parts.append(
                f"{context.task_overdue} overdue "
                f"{'task' if context.task_overdue == 1 else 'tasks'}"
            )

        if follow_ups:
            parts.append(
                f"{follow_ups} pending "
                f"{'reminder' if follow_ups == 1 else 'reminders'}"
            )

        detail = " and ".join(parts) + "."
    else:
        headline = "Nothing overdue"
        detail = (
            f"{context.task_incomplete} open "
            f"{'task' if context.task_incomplete == 1 else 'tasks'}, "
            f"{context.goal_active} active "
            f"{'goal' if context.goal_active == 1 else 'goals'}."
        )

    return AttentionSummary(
        level=level,
        headline=headline,
        detail=detail,
        overdue_count=context.task_overdue,
        due_soon_count=context.task_due_soon,
        incomplete_task_count=context.task_incomplete,
        unread_notification_count=context.unread_notifications,
    )


# =========================================================
# ENGINE
# =========================================================

#: Rule order. This is also the sort order of the emitted list after priority
#: is applied, so a rule added here appears in a predictable place.
RULES = (
    overdue_rule,
    upcoming_rule,
    goal_risk_rule,
    task_load_rule,
    reminder_rule,
    planning_rule,
    habit_consistency_rule,
    finance_rule,
    data_quality_rule,
)

_PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}


def evaluate(context: LifeOSContext) -> list[Insight]:
    """
    Run every rule over the snapshot and return the insights.

    Rules are independent and none reads another's output, so the order they
    run in cannot change what they produce. Sorting afterwards is therefore
    purely presentational — and it is stable, because the rule order above
    breaks ties between equal priorities.
    """

    insights: list[Insight] = []

    for rule in RULES:
        insights.extend(rule(context))

    insights.sort(key=lambda insight: _PRIORITY_ORDER[insight.priority])

    return insights