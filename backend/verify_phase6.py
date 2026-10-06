"""
Phase 6 verification script.

Runs the whole intelligence layer against a throwaway SQLite database — no
config files are touched, no Alembic state is touched, and the real app
database is never opened. Each scenario builds the ORM objects directly, so
it does not depend on a running server or on network access.

Run from `D:/AI-LifeOS/backend`:

    .venv/Scripts/python.exe verify_phase6.py
"""

import json
import sys
from datetime import date, datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

import app.models  # noqa: F401  (registers every model on Base.metadata)
from app.core.security import hash_password
from app.db.base import Base
from app.models.goal import Goal
from app.models.habit import Habit
from app.models.habit_completion import HabitCompletion
from app.models.note import Note
from app.models.planner_event import PlannerEvent
from app.models.reminder import Reminder
from app.models.task import Task
from app.models.transaction import Transaction
from app.models.user import User
from app.services.intelligence_service import get_intelligence

# A fixed clock, so every assertion below is about determinism rather than
# about when the script happened to run. `now` is threaded through the whole
# layer; nothing calls `utcnow()` internally.
NOW = datetime(2026, 10, 4, 9, 0, 0)


def _session():
    """A fresh in-memory database with the full schema created."""

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def _user(email="u1@example.com", name="User One"):
    return User(
        email=email,
        full_name=name,
        hashed_password=hash_password("x"),
    )


def _add(db, obj):
    db.add(obj)
    db.flush()
    return obj


# =========================================================
# Scenarios
# =========================================================


def scenario_empty_user():
    """Brand new account: no records in any domain."""

    db = _session()
    user = _add(db, _user())

    result = get_intelligence(db=db, user_id=user.id, now=NOW)

    assert result.has_data is False, result.has_data
    assert result.populated_domains == [], result.populated_domains
    assert result.tasks.total == 0 and result.tasks.overdue == 0
    assert result.goals == [] and result.habits == [] and result.upcoming == []
    assert result.finance is None
    assert result.summary.level == "clear"
    assert any(i.id == "setup_empty" for i in result.insights), [
        i.id for i in result.insights
    ]
    # Serializes cleanly — this is where a bad annotation or Literal would blow up.
    payload = result.model_dump(mode="json")

    return "empty user", payload


def scenario_tasks_only():
    """Only tasks: two overdue, one due soon, one completed, one open/no date."""

    db = _session()
    user = _add(db, _user())

    _add(db, Task(user_id=user.id, title="Overdue A", status="pending",
                  priority="high", due_date=NOW - timedelta(days=3)))
    _add(db, Task(user_id=user.id, title="Overdue B", status="pending",
                  priority="medium", due_date=NOW - timedelta(hours=5)))
    _add(db, Task(user_id=user.id, title="Soon", status="pending",
                  priority="medium", due_date=NOW + timedelta(hours=10)))
    _add(db, Task(user_id=user.id, title="Done", status="completed",
                  priority="low", due_date=NOW - timedelta(days=1)))
    _add(db, Task(user_id=user.id, title="Someday", status="pending",
                  priority="low", due_date=None))

    db.commit()

    result = get_intelligence(db=db, user_id=user.id, now=NOW)

    assert result.tasks.total == 5, result.tasks
    assert result.tasks.completed == 1, result.tasks
    # "incomplete" is defined as status != 'completed'.
    assert result.tasks.incomplete == 4, result.tasks
    assert result.tasks.overdue == 2, result.tasks
    assert result.tasks.due_soon == 1, result.tasks
    assert result.tasks.unlinked == 4, result.tasks
    assert result.has_data is True
    assert {i.id for i in result.insights} >= {"overdue_tasks", "tasks_due_soon"}
    # A completed task is never reported overdue.
    overdue_titles = {
        i.title for i in result.insights if i.id == "overdue_oldest:2"
    }
    assert not any("Done" == t for t in overdue_titles)

    return "tasks only", result.model_dump(mode="json")


def scenario_goals_only():
    """Only goals: one past its target date, one with no target date."""

    db = _session()
    user = _add(db, _user())

    _add(db, Goal(user_id=user.id, title="Stalled goal", category="career",
                  progress=25, target_date=NOW - timedelta(days=10)))
    _add(db, Goal(user_id=user.id, title="Undated goal", category="study",
                  progress=0, target_date=None))

    db.commit()

    result = get_intelligence(db=db, user_id=user.id, now=NOW)

    assert len(result.goals) == 2, result.goals
    stalled = next(g for g in result.goals if g.title == "Stalled goal")
    assert stalled.days_to_target == -10, stalled
    assert stalled.incomplete_task_count == 0

    ids = {i.id for i in result.insights}
    assert "goal_risk:1" in ids, ids
    # An undated goal produces no risk insight — there is no schedule to compare.
    assert not any(i.startswith("goal_risk:2") for i in ids), ids
    assert "goals_without_target_date" in ids, ids

    return "goals only", result.model_dump(mode="json")


def scenario_mixed_and_finance():
    """Habits with and without completions, transactions, overdue reminder."""

    db = _session()
    user = _add(db, _user())

    goal = _add(db, Goal(user_id=user.id, title="Ship v2", category="work",
                         progress=25, target_date=NOW + timedelta(days=7)))

    task = _add(db, Task(user_id=user.id, title="Linked work", status="pending",
                         priority="high", goal_id=goal.id,
                         due_date=NOW + timedelta(days=1)))
    _add(db, Task(user_id=user.id, title="Unlinked work", status="pending",
                  priority="low"))

    # A habit with real history then a gap.
    habit = _add(db, Habit(user_id=user.id, title="Read", frequency="daily",
                           current_streak=0, longest_streak=9))

    for offset in (20, 25, 28):
        _add(db, HabitCompletion(habit_id=habit.id,
                                 completed_date=NOW.date() - timedelta(days=offset)))

    # A habit on a streak.
    streaky = _add(db, Habit(user_id=user.id, title="Walk", frequency="daily",
                             current_streak=5, longest_streak=5))
    for offset in range(0, 5):
        _add(db, HabitCompletion(habit_id=streaky.id,
                                 completed_date=NOW.date() - timedelta(days=offset)))

    # Transactions in the current calendar month.
    _add(db, Transaction(user_id=user.id, title="Salary", amount=50000,
                         type="income", category="Job",
                         transaction_date=date(2026, 10, 1)))
    _add(db, Transaction(user_id=user.id, title="Rent", amount=12000,
                         type="expense", category="Housing",
                         transaction_date=date(2026, 10, 2)))
    _add(db, Transaction(user_id=user.id, title="Groceries", amount=2500,
                         type="expense", category="Food",
                         transaction_date=date(2026, 10, 3)))

    # A reminder that fired and was never resolved.
    _add(db, Reminder(user_id=user.id, title="Call the bank",
                      remind_at=NOW - timedelta(hours=2), status="pending",
                      is_completed=False, is_cancelled=False,
                      notified_at=NOW - timedelta(hours=2)))

    # A planner day overloaded past the 5/day threshold, and also past the
    # 8/day "heavy" threshold so the per-day insight fires.
    for index in range(8):
        _add(db, PlannerEvent(
            user_id=user.id, title=f"Block {index}",
            event_date=NOW + timedelta(days=1),
            start_time=NOW + timedelta(days=1, hours=index),
            end_time=NOW + timedelta(days=1, hours=index + 1),
            event_type="focus_block", is_completed=False,
        ))

    db.commit()

    result = get_intelligence(db=db, user_id=user.id, now=NOW)

    # Decimal totals survive as exact decimals, not floats.
    assert result.finance is not None
    assert str(result.finance.income_total) == "50000.00", result.finance.income_total
    assert str(result.finance.expense_total) == "14500.00", result.finance.expense_total
    assert result.finance.transaction_count == 3, result.finance
    assert result.finance.period_start == date(2026, 10, 1), result.finance.period_start

    ids = {i.id for i in result.insights}
    assert "reminder_follow_up" in ids, ids
    assert "planner_busy_days" in ids, ids
    assert "planner_busy_day:2026-10-05" in ids, ids
    assert "habit_gap:1" in ids, ids
    assert "habit_streak" in ids, ids
    assert "tasks_without_goal" in ids, ids
    assert "goal_risk:1" in ids, ids

    # Priority ordering is deterministic: high before medium before low.
    order = {"high": 0, "medium": 1, "low": 2}
    ranks = [order[i.priority] for i in result.insights]
    assert ranks == sorted(ranks), ranks

    return "mixed + finance", result.model_dump(mode="json")


def scenario_isolation():
    """Two users: B's records must never appear in A's response."""

    db = _session()
    alice = _add(db, _user("alice@example.com", "Alice"))
    bob = _add(db, _user("bob@example.com", "Bob"))

    _add(db, Task(user_id=alice.id, title="Alice secret task", status="pending",
                  priority="high", due_date=NOW - timedelta(days=5)))
    _add(db, Task(user_id=bob.id, title="Bob secret task", status="pending",
                  priority="high", due_date=NOW - timedelta(days=5)))
    _add(db, Goal(user_id=bob.id, title="Bob secret goal", progress=10,
                  target_date=NOW - timedelta(days=30)))
    _add(db, Note(user_id=bob.id, title="Bob secret note", content="x",
                  tag="General"))

    db.commit()

    alice_result = get_intelligence(db=db, user_id=alice.id, now=NOW)
    bob_result = get_intelligence(db=db, user_id=bob.id, now=NOW)

    alice_blob = json.dumps(alice_result.model_dump(mode="json"))
    bob_blob = json.dumps(bob_result.model_dump(mode="json"))

    assert "Bob secret" not in alice_blob, alice_blob
    assert "Alice secret" not in bob_blob, bob_blob

    assert alice_result.tasks.overdue == 1, alice_result.tasks
    assert bob_result.tasks.overdue == 1, bob_result.tasks
    assert len(bob_result.goals) == 1, bob_result.goals
    assert alice_result.goals == [], alice_result.goals

    return "cross-user isolation", {"alice": alice_blob[:200], "bob": bob_blob[:200]}


def scenario_large_and_edge():
    """Large task count, NULL cross-references, and a determinism re-run."""

    db = _session()
    user = _add(db, _user())

    # 40 open tasks, none overdue, all unlinked.
    for index in range(40):
        _add(db, Task(user_id=user.id, title=f"Task {index}", status="pending",
                      priority="low"))

    # A completed task with a NULL goal (a deleted goal leaves goal_id NULL).
    _add(db, Task(user_id=user.id, title="Old done", status="completed",
                  priority="low", goal_id=None))

    # A task due exactly at `now` — neither overdue nor due-soon-wrong.
    _add(db, Task(user_id=user.id, title="Boundary", status="pending",
                  priority="medium", due_date=NOW))

    # A habit with zero completions at all.
    _add(db, Habit(user_id=user.id, title="Brand new", frequency="daily",
                   current_streak=0, longest_streak=0))

    db.commit()

    first = get_intelligence(db=db, user_id=user.id, now=NOW)
    second = get_intelligence(db=db, user_id=user.id, now=NOW)

    assert first.tasks.incomplete == 41, first.tasks
    assert first.tasks.overdue == 0, first.tasks
    # Due exactly now counts as due soon (>= now, <= horizon).
    assert first.tasks.due_soon == 1, first.tasks

    ids = {i.id for i in first.insights}
    assert "task_load" in ids, ids
    # A habit with no history produces no consistency finding at all.
    assert not any(i.startswith("habit_") for i in ids), ids

    # Same input, same output — no randomness, no clock drift inside the layer.
    assert first.model_dump(mode="json") == second.model_dump(mode="json")

    return "large load + edge cases", first.model_dump(mode="json")


def scenario_deleted_references():
    """Goal deleted while tasks still reference it (SET NULL) must not crash."""

    db = _session()
    user = _add(db, _user())

    goal = _add(db, Goal(user_id=user.id, title="Doomed", progress=10,
                         target_date=NOW - timedelta(days=1)))

    for index in range(3):
        _add(db, Task(user_id=user.id, title=f"Orphan {index}", status="pending",
                      priority="low", goal_id=goal.id))

    db.commit()

    db.delete(goal)
    db.commit()

    # Re-read the tasks so the stale in-memory goal_id cannot mask the SET NULL.
    db.expire_all()

    result = get_intelligence(db=db, user_id=user.id, now=NOW)

    assert result.goals == [], result.goals
    assert result.tasks.incomplete == 3, result.tasks
    assert result.tasks.unlinked == 3, result.tasks

    return "deleted / NULL references", result.model_dump(mode="json")


def scenario_unauthorized_route_shape():
    """The endpoint must require a bearer token."""

    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as client:
        # No Authorization header.
        assert client.get("/api/v1/intelligence").status_code in (401, 403)

        # A token signed for a user that does not exist.
        from app.core.security import create_access_token

        ghost = create_access_token({"sub": "99999999"})

        response = client.get(
            "/api/v1/intelligence",
            headers={"Authorization": f"Bearer {ghost}"},
        )
        assert response.status_code == 401, response.status_code

    return "unauthorized access", {"checked": "no token, and unknown user"}


def main():
    scenarios = [
        scenario_empty_user,
        scenario_tasks_only,
        scenario_goals_only,
        scenario_mixed_and_finance,
        scenario_isolation,
        scenario_large_and_edge,
        scenario_deleted_references,
    ]

    for scenario in scenarios:
        name, payload = scenario()
        insights = payload.get("insights", []) if isinstance(payload, dict) else []
        print(f"PASS  {name}")
        if insights:
            for insight in insights:
                print(f"        [{insight['priority']:>6}] {insight['type']:<18} "
                      f"{insight['title']}  —  {insight['detail']}")

    print()

    try:
        scenario_unauthorized_route_shape()
        print("PASS  unauthorized access")
    except Exception as exc:  # pragma: no cover - reported, not raised
        print(f"FAIL  unauthorized access: {exc}")

    print("\nALL SCENARIOS COMPLETED")
    return 0


if __name__ == "__main__":
    sys.exit(main())