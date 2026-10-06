from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Reminder(Base):
    """
    A persistent, scheduled reminder owned by a single user.

    `remind_at` is a naive UTC datetime, matching the convention used by every
    other timestamp in this project. The scheduler reads pending rows where
    `remind_at <= now`, so the composite (status, remind_at) index is the one
    that matters for the hot query.
    """

    __tablename__ = "reminders"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    remind_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
    )

    # pending | completed | cancelled
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
    )

    is_completed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    is_cancelled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    # Set once the scheduler has delivered the notification. A reminder that
    # is already notified is never picked up again, which makes delivery
    # idempotent across restarts.
    notified_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    task_id: Mapped[int | None] = mapped_column(
        ForeignKey("tasks.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    habit_id: Mapped[int | None] = mapped_column(
        ForeignKey("habits.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    planner_event_id: Mapped[int | None] = mapped_column(
        ForeignKey("planner_events.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    user = relationship(
        "User",
        back_populates="reminders",
    )
    task = relationship(
        "Task",
        back_populates="reminders",
    )
    habit = relationship(
        "Habit",
        back_populates="reminders",
    )
    planner_event = relationship(
        "PlannerEvent",
        back_populates="reminders",
    )

    __table_args__ = (
        # Serves the scheduler's due query (status + remind_at) and the
        # per-user list ordering in one index.
        Index(
            "ix_reminders_status_remind_at",
            "status",
            "remind_at",
        ),
    )
