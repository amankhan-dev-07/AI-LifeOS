"""
Tests for Phase 14 AI write commands (acceptance areas 10-13).
"""
import pytest
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, date, time

from app.services.ai_orchestration_service import handle_command, confirm_plan, cancel_plan
from app.models.user import User
from app.models.task import Task
from app.models.goal import Goal
from app.models.habit import Habit
from app.models.reminder import Reminder


class TestCreateCommands:
    """Tests for create commands."""

    def test_create_task(self, db_session: Session, test_user: User):
        """Test creating a task (area 10)."""
        response = handle_command(
            db=db_session,
            user_id=test_user.id,
            message="Create a task to review the quarterly report",
        )

        assert response.intent == "create"
        assert not response.awaiting_user
        assert response.plan is not None
        assert len(response.plan.steps) == 1
        step = response.plan.steps[0]
        assert step.operation == "create"
        assert step.entity == "task"
        assert step.status == "succeeded"
        assert "review the quarterly report" in step.description.lower()

        # Verify task was actually created
        task = db_session.query(Task).filter(Task.user_id == test_user.id).first()
        assert task is not None
        assert "quarterly report" in task.title.lower()

    def test_create_task_with_priority_and_due_date(self, db_session: Session, test_user: User):
        """Test creating a task with priority and due date."""
        response = handle_command(
            db=db_session,
            user_id=test_user.id,
            message="Create a high priority task to finish the proposal by tomorrow",
        )

        assert response.intent == "create"
        assert not response.awaiting_user
        assert response.plan is not None
        step = response.plan.steps[0]
        assert step.status == "succeeded"

        task = db_session.query(Task).filter(Task.user_id == test_user.id).first()
        assert task is not None
        assert task.priority == "high"
        # Due date should be set (tomorrow)
        assert task.due_date is not None

    def test_create_goal(self, db_session: Session, test_user: User):
        """Test creating a goal."""
        response = handle_command(
            db=db_session,
            user_id=test_user.id,
            message="Create a goal to learn Spanish this year",
        )

        assert response.intent == "create"
        assert not response.awaiting_user
        step = response.plan.steps[0]
        assert step.operation == "create"
        assert step.entity == "goal"
        assert step.status == "succeeded"

        goal = db_session.query(Goal).filter(Goal.user_id == test_user.id).first()
        assert goal is not None
        assert "Spanish" in goal.title

    def test_create_habit(self, db_session: Session, test_user: User):
        """Test creating a habit."""
        response = handle_command(
            db=db_session,
            user_id=test_user.id,
            message="Create a daily habit to drink 8 glasses of water",
        )

        assert response.intent == "create"
        assert not response.awaiting_user
        step = response.plan.steps[0]
        assert step.operation == "create"
        assert step.entity == "habit"
        assert step.status == "succeeded"

        habit = db_session.query(Habit).filter(Habit.user_id == test_user.id).first()
        assert habit is not None
        assert "water" in habit.title.lower()
        assert habit.frequency == "daily"

    def test_create_reminder(self, db_session: Session, test_user: User):
        """Test creating a reminder (area 12)."""
        response = handle_command(
            db=db_session,
            user_id=test_user.id,
            message="Remind me to call the client tomorrow at 3 PM",
        )

        assert response.intent == "create"
        assert not response.awaiting_user
        step = response.plan.steps[0]
        assert step.operation == "create"
        assert step.entity == "reminder"
        assert step.status == "succeeded"

        reminder = db_session.query(Reminder).filter(Reminder.user_id == test_user.id).first()
        assert reminder is not None
        assert "client" in reminder.title.lower()
        assert reminder.remind_at is not None


class TestUpdateCommands:
    """Tests for update commands (area 11)."""

    def test_update_task_priority(self, db_session: Session, test_user: User, seed_tasks):
        """Test updating a task's priority."""
        task = seed_tasks[0]
        response = handle_command(
            db=db_session,
            user_id=test_user.id,
            message=f"Set priority of '{task.title}' to high",
        )

        assert response.intent == "update"
        assert not response.awaiting_user
        step = response.plan.steps[0]
        assert step.operation == "update"
        assert step.entity == "task"
        assert step.status == "succeeded"

        # Verify update
        db_session.refresh(task)
        assert task.priority == "high"

    def test_update_task_due_date(self, db_session: Session, test_user: User, seed_tasks):
        """Test updating a task's due date (reschedule)."""
        task = seed_tasks[0]
        response = handle_command(
            db=db_session,
            user_id=test_user.id,
            message=f"Move '{task.title}' to tomorrow",
        )

        assert response.intent == "update"
        assert not response.awaiting_user
        step = response.plan.steps[0]
        assert step.operation == "update"
        assert step.entity == "task"
        assert step.status == "succeeded"

        db_session.refresh(task)
        assert task.due_date is not None

    def test_update_goal_progress(self, db_session: Session, test_user: User, seed_goals):
        """Test updating a goal's progress."""
        goal = seed_goals[0]
        response = handle_command(
            db=db_session,
            user_id=test_user.id,
            message=f"Set progress of '{goal.title}' to 75 percent",
        )

        assert response.intent == "update"
        assert not response.awaiting_user
        step = response.plan.steps[0]
        assert step.operation == "update"
        assert step.entity == "goal"
        assert step.status == "succeeded"

        db_session.refresh(goal)
        assert goal.progress == 75


class TestCompleteCommands:
    """Tests for complete commands."""

    def test_complete_task(self, db_session: Session, test_user: User, seed_tasks):
        """Test completing a task."""
        task = seed_tasks[0]
        response = handle_command(
            db=db_session,
            user_id=test_user.id,
            message=f"Mark '{task.title}' as complete",
        )

        assert response.intent == "complete"
        assert not response.awaiting_user
        step = response.plan.steps[0]
        assert step.operation == "complete"
        assert step.entity == "task"
        assert step.status == "succeeded"

        db_session.refresh(task)
        assert task.status == "completed"

    def test_complete_habit(self, db_session: Session, test_user: User, seed_habits):
        """Test completing a habit (logs a completion)."""
        habit = seed_habits[0]
        initial_streak = habit.current_streak
        response = handle_command(
            db=db_session,
            user_id=test_user.id,
            message=f"Complete habit '{habit.title}'",
        )

        assert response.intent == "complete"
        assert not response.awaiting_user
        step = response.plan.steps[0]
        assert step.operation == "complete"
        assert step.entity == "habit"
        assert step.status == "succeeded"

        db_session.refresh(habit)
        # Streak should increment
        assert habit.current_streak == initial_streak + 1


class TestMultiStepCommands:
    """Tests for multi-step commands (area 13)."""

    def test_multi_step_create_task_and_reminder(self, db_session: Session, test_user: User):
        """Test a command that creates both a task and a reminder."""
        response = handle_command(
            db=db_session,
            user_id=test_user.id,
            message="Create a task to call the vendor and remind me to call them tomorrow at 10 AM",
        )

        assert response.intent in ("create", "unknown")  # may be parsed as two steps
        assert response.plan is not None
        # Should have at least one step
        assert len(response.plan.steps) >= 1

    def test_multi_step_complete_task_and_create_note(self, db_session: Session, test_user: User, seed_tasks):
        """Test completing a task and creating a note in one command."""
        task = seed_tasks[0]
        response = handle_command(
            db=db_session,
            user_id=test_user.id,
            message=f"Complete '{task.title}' and create a note about the outcome",
        )

        assert response.plan is not None
        assert len(response.plan.steps) >= 1


class TestSearchCommands:
    """Tests for search integration (area 9)."""

    def test_search_across_domains(self, db_session: Session, test_user: User, seed_tasks, seed_goals, seed_notes):
        """Test searching across all domains (area 9)."""
        response = handle_command(
            db=db_session,
            user_id=test_user.id,
            message="Search for project",
        )

        assert response.intent == "search"
        assert not response.awaiting_user
        assert response.plan is not None
        step = response.plan.steps[0]
        assert step.operation == "search"
        assert step.entity == "intelligence"
        assert step.status == "succeeded"

        # Response should mention matches
        assert "found" in response.response.lower() or "match" in response.response.lower()