"""
Model registry.

SQLAlchemy resolves a string relationship such as `relationship("User")` by
looking the name up in the registry that `Base.metadata` belongs to. A model is
in that registry only once its module has been *imported* — no model in this
project imports another model (they are all linked by string name plus
`ForeignKey`), so registration is purely a side effect of import.

That made registration depend on which entry point ran. `app.main` and
`alembic/env.py` each listed all twelve models by hand, but any other entry
point — a script, a test, or the scheduler run directly — imported only the
models it happened to touch. `reminder_scheduler` pulls in `Reminder` and
`Notification` alone, so `Reminder.user = relationship("User")` was configured
before `User` existed in the registry and mapper configuration raised:

    InvalidRequestError: When initializing mapper Mapper[Reminder(reminders)],
    expression 'User' failed to locate a name ('User')

Importing every model here makes registration a property of the package rather
than of the caller: importing any submodule of `app.models` now configures the
complete registry, so `Base.metadata` always holds the full schema and every
entry point agrees.

The list is deliberately explicit and ordered — it reads as the schema's
table list and keeps the import side effect obvious rather than magical.
"""

# Imported for their registration side effect on `Base.metadata`.
from app.models.user import User
from app.models.task import Task
from app.models.goal import Goal
from app.models.habit import Habit
from app.models.habit_completion import HabitCompletion
from app.models.planner_event import PlannerEvent
from app.models.note import Note
from app.models.transaction import Transaction
from app.models.notification import Notification
from app.models.user_preferences import UserPreferences
from app.models.reminder import Reminder

__all__ = [
    "User",
    "Task",
    "Goal",
    "Habit",
    "HabitCompletion",
    "PlannerEvent",
    "Note",
    "Transaction",
    "Notification",
    "UserPreferences",
    "Reminder",
]