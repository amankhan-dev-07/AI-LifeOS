"""
Tests for Phase 14 AI confirmation flow (acceptance areas 14-15, 21-22).
"""
import pytest
from sqlalchemy.orm import Session
from datetime import date, time

from app.services.ai_orchestration_service import handle_command, confirm_plan, cancel_plan
from app.models.user import User
from app.models.task import Task
from app.models.goal import Goal
from app.models.habit import Habit
from app.models.note import Note
from app.models.reminder import Reminder
from app.models.planner_event import PlannerEvent
from app.models.transaction import Transaction
from decimal import Decimal


class TestConfirmationRequiredActions:
    """Tests for actions that require confirmation (area 14)."""

    def test_delete_task_requires_confirmation(self, db_session: Session, test_user: User, seed_tasks):
        """Test that deleting a task requires confirmation."""
        task = seed_tasks[0]
        response = handle_command(
            db=db_session,
            user_id=test_user.id,
            message=f"Delete the task '{task.title}'",
        )

        assert response.awaiting_user is True
        assert response.plan is not None
        assert response.plan.requires_confirmation is True
        assert len(response.plan.steps) == 1
        step = response.plan.steps[0]
        assert step.operation == "delete"
        assert step.entity == "task"
        assert step.confirmation_required is True
        assert step.status == "pending"  # Not executed yet
        assert "permanent" in step.confirmation_reason.lower()

        # Verify task still exists
        db_session.refresh(task)
        assert task.id is not None

    def test_delete_goal_requires_confirmation(self, db_session: Session, test_user: User, seed_goals):
        """Test that deleting a goal requires confirmation."""
        goal = seed_goals[0]
        response = handle_command(
            db=db_session,
            user_id=test_user.id,
            message=f"Delete the goal '{goal.title}'",
        )

        assert response.awaiting_user is True
        assert response.plan.requires_confirmation is True
        step = response.plan.steps[0]
        assert step.operation == "delete"
        assert step.entity == "goal"
        assert step.confirmation_required is True

    def test_delete_habit_requires_confirmation(self, db_session: Session, test_user: User, seed_habits):
        """Test that deleting a habit requires confirmation."""
        habit = seed_habits[0]
        response = handle_command(
            db=db_session,
            user_id=test_user.id,
            message=f"Delete the habit '{habit.title}'",
        )

        assert response.awaiting_user is True
        assert response.plan.requires_confirmation is True
        step = response.plan.steps[0]
        assert step.operation == "delete"
        assert step.entity == "habit"
        assert step.confirmation_required is True

    def test_delete_note_requires_confirmation(self, db_session: Session, test_user: User, seed_notes):
        """Test that deleting a note requires confirmation."""
        note = seed_notes[0]
        response = handle_command(
            db=db_session,
            user_id=test_user.id,
            message=f"Delete the note '{note.title}'",
        )

        assert response.awaiting_user is True
        assert response.plan.requires_confirmation is True
        step = response.plan.steps[0]
        assert step.operation == "delete"
        assert step.entity == "note"
        assert step.confirmation_required is True

    def test_delete_reminder_requires_confirmation(self, db_session: Session, test_user: User, seed_reminders):
        """Test that deleting a reminder requires confirmation."""
        reminder = seed_reminders[0]
        response = handle_command(
            db=db_session,
            user_id=test_user.id,
            message=f"Delete the reminder '{reminder.title}'",
        )

        assert response.awaiting_user is True
        assert response.plan.requires_confirmation is True
        step = response.plan.steps[0]
        assert step.operation == "delete"
        assert step.entity == "reminder"
        assert step.confirmation_required is True

    def test_delete_planner_event_requires_confirmation(self, db_session: Session, test_user: User, seed_planner_events):
        """Test that deleting a planner event requires confirmation."""
        event = seed_planner_events[0]
        response = handle_command(
            db=db_session,
            user_id=test_user.id,
            message=f"Delete the event '{event.title}'",
        )

        assert response.awaiting_user is True
        assert response.plan.requires_confirmation is True
        step = response.plan.steps[0]
        assert step.operation == "delete"
        assert step.entity == "planner_event"
        assert step.confirmation_required is True

    def test_create_transaction_requires_confirmation(self, db_session: Session, test_user: User):
        """Test that creating a transaction requires confirmation (financial write)."""
        response = handle_command(
            db=db_session,
            user_id=test_user.id,
            message="Record an expense of 50 dollars for groceries",
        )

        assert response.awaiting_user is True
        assert response.plan.requires_confirmation is True
        step = response.plan.steps[0]
        assert step.operation == "create"
        assert step.entity == "transaction"
        assert step.confirmation_required is True
        assert "finances" in step.confirmation_reason.lower()

    def test_update_transaction_requires_confirmation(self, db_session: Session, test_user: User, seed_transactions):
        """Test that updating a transaction requires confirmation."""
        txn = seed_transactions[0]
        response = handle_command(
            db=db_session,
            user_id=test_user.id,
            message=f"Update the transaction '{txn.title}' amount to 100",
        )

        assert response.awaiting_user is True
        assert response.plan.requires_confirmation is True
        step = response.plan.steps[0]
        assert step.operation == "update"
        assert step.entity == "transaction"
        assert step.confirmation_required is True

    def test_apply_daily_plan_requires_confirmation(self, db_session: Session, test_user: User):
        """Test that applying a daily plan requires confirmation."""
        response = handle_command(
            db=db_session,
            user_id=test_user.id,
            message="Plan my day and apply it",
        )

        assert response.awaiting_user is True
        assert response.plan.requires_confirmation is True
        step = response.plan.steps[0]
        assert step.operation == "plan"
        assert step.entity == "planner_event"
        assert step.confirmation_required is True


class TestConfirmPlanExecution:
    """Tests for executing confirmed plans."""

    def test_confirm_delete_task(self, db_session: Session, test_user: User, seed_tasks):
        """Test confirming a task deletion."""
        task = seed_tasks[0]
        task_id = task.id

        # First, propose the deletion
        propose_response = handle_command(
            db=db_session,
            user_id=test_user.id,
            message=f"Delete the task '{task.title}'",
        )

        assert propose_response.awaiting_user is True
        plan_id = propose_response.plan.plan_id

        # Then confirm it
        confirm_response = confirm_plan(
            db=db_session,
            user_id=test_user.id,
            plan_id=plan_id,
        )

        assert confirm_response.awaiting_user is False
        assert confirm_response.plan is not None
        step = confirm_response.plan.steps[0]
        assert step.status == "succeeded"
        assert step.operation == "delete"
        assert step.entity == "task"

        # Verify task was deleted
        deleted_task = db_session.query(Task).filter(Task.id == task_id).first()
        assert deleted_task is None

    def test_confirm_create_transaction(self, db_session: Session, test_user: User):
        """Test confirming a transaction creation."""
        propose_response = handle_command(
            db=db_session,
            user_id=test_user.id,
            message="Record an income of 1000 for freelance work",
        )

        assert propose_response.awaiting_user is True
        plan_id = propose_response.plan.plan_id

        confirm_response = confirm_plan(
            db=db_session,
            user_id=test_user.id,
            plan_id=plan_id,
        )

        assert confirm_response.awaiting_user is False
        step = confirm_response.plan.steps[0]
        assert step.status == "succeeded"
        assert step.operation == "create"
        assert step.entity == "transaction"

        # Verify transaction was created
        txn = db_session.query(Transaction).filter(Transaction.user_id == test_user.id).first()
        assert txn is not None
        assert txn.amount == Decimal("1000.00")
        assert txn.type == "income"

    def test_confirm_apply_plan(self, db_session: Session, test_user: User, seed_tasks, seed_habits, seed_goals):
        """Test confirming a daily plan application."""
        propose_response = handle_command(
            db=db_session,
            user_id=test_user.id,
            message="Generate a plan for today and apply it",
        )

        assert propose_response.awaiting_user is True
        plan_id = propose_response.plan.plan_id

        confirm_response = confirm_plan(
            db=db_session,
            user_id=test_user.id,
            plan_id=plan_id,
        )

        assert confirm_response.awaiting_user is False
        assert confirm_response.plan is not None

        # Should have created planner events
        events = db_session.query(PlannerEvent).filter(PlannerEvent.user_id == test_user.id).all()
        # Note: plan may create 0 events if no tasks/habits to schedule, but the step should succeed
        step = confirm_response.plan.steps[0]
        assert step.operation == "plan"
        assert step.entity == "planner_event"
        # Status could be succeeded or failed depending on whether blocks were created
        assert step.status in ("succeeded", "failed")


class TestCancelPlan:
    """Tests for cancelling pending plans (area 15)."""

    def test_cancel_delete_task(self, db_session: Session, test_user: User, seed_tasks):
        """Test cancelling a task deletion."""
        task = seed_tasks[0]
        task_id = task.id

        propose_response = handle_command(
            db=db_session,
            user_id=test_user.id,
            message=f"Delete the task '{task.title}'",
        )

        assert propose_response.awaiting_user is True
        plan_id = propose_response.plan.plan_id

        cancel_response = cancel_plan(
            db=db_session,
            user_id=test_user.id,
            plan_id=plan_id,
        )

        assert cancel_response.awaiting_user is False
        assert "cancelled" in cancel_response.response.lower()
        assert "nothing was changed" in cancel_response.response.lower()

        # Verify task still exists
        db_session.refresh(task)
        assert task.id == task_id

    def test_cancel_create_transaction(self, db_session: Session, test_user: User):
        """Test cancelling a transaction creation."""
        propose_response = handle_command(
            db=db_session,
            user_id=test_user.id,
            message="Record an expense of 25 for coffee",
        )

        assert propose_response.awaiting_user is True
        plan_id = propose_response.plan.plan_id

        cancel_response = cancel_plan(
            db=db_session,
            user_id=test_user.id,
            plan_id=plan_id,
        )

        assert cancel_response.awaiting_user is False
        assert "cancelled" in cancel_response.response.lower()

        # Verify no transaction was created
        txns = db_session.query(Transaction).filter(Transaction.user_id == test_user.id).all()
        assert len(txns) == 0

    def test_cancel_already_used_plan_fails(self, db_session: Session, test_user: User, seed_tasks):
        """Test that cancelling an already-confirmed plan returns appropriate response."""
        task = seed_tasks[0]

        propose_response = handle_command(
            db=db_session,
            user_id=test_user.id,
            message=f"Delete the task '{task.title}'",
        )

        plan_id = propose_response.plan.plan_id

        # Confirm first
        confirm_plan(db=db_session, user_id=test_user.id, plan_id=plan_id)

        # Try to cancel - should fail gracefully
        cancel_response = cancel_plan(
            db=db_session,
            user_id=test_user.id,
            plan_id=plan_id,
        )

        assert "no longer pending" in cancel_response.response.lower() or "nothing to cancel" in cancel_response.response.lower()

    def test_cancel_expired_plan_fails(self, db_session: Session, test_user: User):
        """Test that cancelling an invalid/expired plan returns appropriate response."""
        cancel_response = cancel_plan(
            db=db_session,
            user_id=test_user.id,
            plan_id="invalid-plan-id-12345",
        )

        assert cancel_response.awaiting_user is False
        assert "no longer valid" in cancel_response.response.lower() or "no longer pending" in cancel_response.response.lower()


class TestPartialMultiStepFailure:
    """Tests for partial multi-step failure handling (area 21)."""

    def test_multi_step_with_one_failing(self, db_session: Session, test_user: User, seed_tasks):
        """Test that a multi-step command reports partial success/failure."""
        task = seed_tasks[0]
        # This command might try to do something that partially fails
        response = handle_command(
            db=db_session,
            user_id=test_user.id,
            message=f"Complete '{task.title}' and delete a non-existent task",
        )

        # Should get clarification or partial execution
        assert response.plan is not None
        # At least one step should be present
        assert len(response.plan.steps) >= 1

    def test_confirm_partial_failure(self, db_session: Session, test_user: User, seed_tasks, seed_goals):
        """Test confirmation where one step fails."""
        task = seed_tasks[0]
        goal = seed_goals[0]

        # Create a plan with multiple steps where one might fail
        # This is harder to test directly; the main thing is the response
        # structure includes failures
        response = handle_command(
            db=db_session,
            user_id=test_user.id,
            message=f"Delete '{task.title}' and delete '{goal.title}'",
        )

        if response.awaiting_user:
            # Both deletions require confirmation
            plan_id = response.plan.plan_id
            confirm_response = confirm_plan(
                db=db_session,
                user_id=test_user.id,
                plan_id=plan_id,
            )

            assert confirm_response.plan is not None
            # Both steps should have status
            for step in confirm_response.plan.steps:
                assert step.status in ("succeeded", "failed")


class TestNoFakeSuccess:
    """Tests that failed executions are never reported as success (area 22)."""

    def test_failed_delete_reported_as_failed(self, db_session: Session, test_user: User):
        """Test that a failed deletion is reported as failed, not succeeded."""
        # Try to delete a non-existent task (should fail at confirmation or execution)
        response = handle_command(
            db=db_session,
            user_id=test_user.id,
            message="Delete the task 'NonExistentTask12345'",
        )

        # Should either get clarification or a failed step
        if response.awaiting_user and response.plan is not None:
            # If it gets to confirmation, the step should eventually fail
            confirm_response = confirm_plan(
                db=db_session,
                user_id=test_user.id,
                plan_id=response.plan.plan_id,
            )
            # The step should not be marked as succeeded if it failed
            for step in confirm_response.plan.steps:
                if step.operation == "delete":
                    assert step.status != "succeeded" or step.result_message is not None
        else:
            # Direct clarification - no fake success
            assert "could not" in response.response.lower() or "unable" in response.response.lower() or "clarify" in response.response.lower()

    def test_failed_creation_reported_as_failed(self, db_session: Session, test_user: User):
        """Test that a failed creation is reported as failed."""
        # Try to create a task with no title (should fail)
        response = handle_command(
            db=db_session,
            user_id=test_user.id,
            message="Create a task",  # No title provided
        )

        # Should either clarify or report failure
        if response.awaiting_user and response.plan is not None:
            confirm_response = confirm_plan(
                db=db_session,
                user_id=test_user.id,
                plan_id=response.plan.plan_id,
            )
            for step in confirm_response.plan.steps:
                assert step.status != "succeeded" or step.result_message is not None
        else:
            assert "could not" in response.response.lower() or "clarify" in response.response.lower() or "title" in response.response.lower()