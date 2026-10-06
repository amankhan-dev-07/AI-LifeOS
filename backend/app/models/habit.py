from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Habit(Base):
    __tablename__ = "habits"

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

    goal_id: Mapped[int | None] = mapped_column(
        ForeignKey("goals.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    frequency: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="daily",
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    current_streak: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    longest_streak: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    last_completed_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
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
        back_populates="habits",
    )
    goal = relationship(
        "Goal",
        back_populates="habits",
    )
    completions = relationship(
        "HabitCompletion",
        back_populates="habit",
        cascade="all, delete-orphan",
    )
    planner_events = relationship(
        "PlannerEvent",
        back_populates="habit",
        cascade="all, delete-orphan",
    )
    # Cross-domain link from a reminder (SET NULL on delete).
    reminders = relationship(
        "Reminder",
        back_populates="habit",
    )

    __table_args__ = (
        Index(
            "ix_habits_user_active",
            "user_id",
            "is_active",
        ),
    )