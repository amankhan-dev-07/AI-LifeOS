from sqlalchemy import Row, case, or_, select
from sqlalchemy.orm import Session

from app.models.goal import Goal
from app.models.habit import Habit
from app.models.note import Note
from app.models.planner_event import PlannerEvent
from app.models.task import Task
from app.models.transaction import Transaction


def _pattern(term: str) -> str:
    """Build an ILIKE pattern, escaping LIKE metacharacters in user input.

    Without this a query of `%` would match every row of the table.
    """

    escaped = term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")

    return f"%{escaped}%"


def _contains(column, term: str):
    """Case-insensitive "contains" filter scoped by the caller to one user."""

    return column.ilike(_pattern(term), escape="\\")


def _rank(title_column, term: str):
    """0 for a title match, 1 for a secondary-field-only match.

    Cheap, deterministic prioritization — no ranking engine, no extra pass.
    """

    return case((title_column.ilike(_pattern(term), escape="\\"), 0), else_=1)


def search_tasks(
    db: Session,
    user_id: int,
    term: str,
    limit: int,
) -> list[Row]:
    statement = (
        select(
            Task.id,
            Task.title,
            Task.description,
            Task.status,
            Task.priority,
            Task.updated_at,
        )
        .where(
            Task.user_id == user_id,
            or_(
                _contains(Task.title, term),
                _contains(Task.description, term),
                _contains(Task.status, term),
                _contains(Task.priority, term),
            ),
        )
        .order_by(_rank(Task.title, term), Task.updated_at.desc(), Task.id.desc())
        .limit(limit)
    )

    return list(db.execute(statement).all())


def search_goals(
    db: Session,
    user_id: int,
    term: str,
    limit: int,
) -> list[Row]:
    statement = (
        select(
            Goal.id,
            Goal.title,
            Goal.description,
            Goal.category,
            Goal.is_completed,
            Goal.target_date,
            Goal.updated_at,
        )
        .where(
            Goal.user_id == user_id,
            or_(
                _contains(Goal.title, term),
                _contains(Goal.description, term),
                _contains(Goal.category, term),
            ),
        )
        .order_by(_rank(Goal.title, term), Goal.updated_at.desc(), Goal.id.desc())
        .limit(limit)
    )

    return list(db.execute(statement).all())


def search_habits(
    db: Session,
    user_id: int,
    term: str,
    limit: int,
) -> list[Row]:
    statement = (
        select(
            Habit.id,
            Habit.title,
            Habit.description,
            Habit.frequency,
            Habit.is_active,
            Habit.updated_at,
        )
        .where(
            Habit.user_id == user_id,
            or_(
                _contains(Habit.title, term),
                _contains(Habit.description, term),
                _contains(Habit.frequency, term),
            ),
        )
        .order_by(_rank(Habit.title, term), Habit.updated_at.desc(), Habit.id.desc())
        .limit(limit)
    )

    return list(db.execute(statement).all())


def search_notes(
    db: Session,
    user_id: int,
    term: str,
    limit: int,
) -> list[Row]:
    statement = (
        select(
            Note.id,
            Note.title,
            Note.content,
            Note.tag,
            Note.is_pinned,
            Note.updated_at,
        )
        .where(
            Note.user_id == user_id,
            Note.is_archived.is_(False),
            or_(
                _contains(Note.title, term),
                _contains(Note.content, term),
                _contains(Note.tag, term),
            ),
        )
        .order_by(
            _rank(Note.title, term),
            Note.is_pinned.desc(),
            Note.updated_at.desc(),
            Note.id.desc(),
        )
        .limit(limit)
    )

    return list(db.execute(statement).all())


def search_planner_events(
    db: Session,
    user_id: int,
    term: str,
    limit: int,
) -> list[Row]:
    statement = (
        select(
            PlannerEvent.id,
            PlannerEvent.title,
            PlannerEvent.description,
            PlannerEvent.event_type,
            PlannerEvent.event_date,
            PlannerEvent.start_time,
        )
        .where(
            PlannerEvent.user_id == user_id,
            or_(
                _contains(PlannerEvent.title, term),
                _contains(PlannerEvent.description, term),
                _contains(PlannerEvent.event_type, term),
            ),
        )
        .order_by(
            _rank(PlannerEvent.title, term),
            PlannerEvent.event_date.desc(),
            PlannerEvent.id.desc(),
        )
        .limit(limit)
    )

    return list(db.execute(statement).all())


def search_transactions(
    db: Session,
    user_id: int,
    term: str,
    limit: int,
) -> list[Row]:
    statement = (
        select(
            Transaction.id,
            Transaction.title,
            Transaction.notes,
            Transaction.category,
            Transaction.type,
            Transaction.transaction_date,
        )
        .where(
            Transaction.user_id == user_id,
            or_(
                _contains(Transaction.title, term),
                _contains(Transaction.category, term),
                _contains(Transaction.notes, term),
                _contains(Transaction.type, term),
            ),
        )
        .order_by(
            _rank(Transaction.title, term),
            Transaction.transaction_date.desc(),
            Transaction.id.desc(),
        )
        .limit(limit)
    )

    return list(db.execute(statement).all())