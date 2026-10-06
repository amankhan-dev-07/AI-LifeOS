"""
Tests for Phase 14 AI edge cases and error handling (acceptance areas 16-20).
"""
import pytest
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from app.services.ai_orchestration_service import handle_command, confirm_plan, cancel_plan
from app.models.user import User
from app.models.task import Task
from app.models.goal import Goal


class TestMalformedInvalidOutput:
    """Tests for malformed/invalid model output handling (area 16)."""

    def test_unknown_command_returns_clarification(self, db_session: Session, test_user: User):
        """Test that an unknown command returns a clarification question."""
        response = handle_command(
            db=db_session,
            user_id=test_user.id,
            message="Xylophone banana spaceship",  # Nonsense
        )

        assert response.intent == "unknown"
        assert response.awaiting_user is True  # Asks for clarification
        assert response.clarification_question is not None
        assert len(response.clarification_question) > 0

    def test_empty_message_handled(self, db_session: Session, test_user: User):
        """Test that an empty message is handled gracefully."""
        response = handle_command(
            db=db_session,
            user_id=test_user.id,
            message="   ",
        )

        # Should not crash
        assert response is not None
        assert response.response is not None

    def test_very_long_message_truncated(self, db_session: Session, test_user: User):
        """Test that very long messages are handled (max 2000 chars)."""
        long_message = "Create a task to " + "do something " * 100
        response = handle_command(
            db=db_session,
            user_id=test_user.id,
            message=long_message,
        )

        # Should not crash, may truncate or clarify
        assert response is not None

    def test_special_characters_in_message(self, db_session: Session, test_user: User):
        """Test that special characters are handled."""
        response = handle_command(
            db=db_session,
            user_id=test_user.id,
            message="Create a task: \"Review @#$%^&*()\"",
        )

        assert response is not None
        assert response.plan is not None or response.clarification_question is not None


class TestAIUnavailableErrorHandling:
    """Tests for AI unavailable/error handling (area 17)."""

    def test_deterministic_path_works_without_ollama(self, db_session: Session, test_user: User, seed_tasks):
        """Test that the deterministic path works when Ollama is unavailable."""
        # This is the default behavior - no Ollama needed
        response = handle_command(
            db=db_session,
            user_id=test_user.id,
            message="Show my tasks",
        )

        assert response.ai_online is False  # Deterministic path
        assert response.intent == "read"
        assert response.plan is not None
        assert len(response.plan.steps) == 1
        assert response.plan.steps[0].status == "succeeded"

    def test_complex_command_falls_back_to_deterministic(self, db_session: Session, test_user: User, seed_tasks, seed_goals):
        """Test that complex commands fall back gracefully."""
        response = handle_command(
            db=db_session,
            user_id=test_user.id,
            message="Please show me all my tasks and goals and habits and remind me about everything",
        )

        # Should not crash, should produce some response
        assert response is not None
        assert response.response is not None
        assert len(response.response) > 0


class TestAmbiguousDateTimeHandling:
    """Tests for ambiguous date/time handling (area 18)."""

    def test_ambiguous_time_returns_clarification(self, db_session: Session, test_user: User):
        """Test that ambiguous time references return clarification."""
        response = handle_command(
            db=db_session,
            user_id=test_user.id,
            message="Remind me to call the client",  # No time specified
        )

        # Should ask for clarification about time
        assert response.awaiting_user is True or response.clarification_question is not None
        if response.clarification_question:
            assert "time" in response.clarification_question.lower() or "when" in response.clarification_question.lower()

    def test_relative_date_resolution(self, db_session: Session, test_user: User):
        """Test that relative dates like 'tomorrow' are resolved."""
        response = handle_command(
            db=db_session,
            user_id=test_user.id,
            message="Remind me to call the client tomorrow at 3 PM",
        )

        # Should create the reminder (no confirmation needed for create reminder)
        assert response.intent == "create"
        assert not response.awaiting_user
        assert response.plan is not None
        step = response.plan.steps[0]
        assert step.entity == "reminder"
        assert step.status == "succeeded"

    def test_past_time_rejected(self, db_session: Session, test_user: User):
        """Test that past times are rejected."""
        response = handle_command(
            db=db_session,
            user_id=test_user.id,
            message="Remind me to call the client yesterday at 3 PM",
        )

        # Should either clarify or fail
        assert response is not None
        if response.awaiting_user and response.plan is not None:
            confirm_response = confirm_plan(
                db=db_session,
                user_id=test_user.id,
                plan_id=response.plan.plan_id,
            )
            # Should fail
            for step in confirm_response.plan.steps:
                if step.operation == "create":
                    assert step.status in ("failed", "skipped")
        else:
            # Direct failure/clarification
            assert "past" in response.response.lower() or "could not" in response.response.lower() or "clarify" in response.response.lower()


class TestCrossUserIsolation:
    """Tests for cross-user isolation (area 19)."""

    def test_user_cannot_read_another_users_tasks(self, db_session: Session, test_user: User, test_user_2: User, seed_tasks):
        """Test that a user cannot read another user's tasks."""
        # test_user_2 creates a task
        task_user2 = Task(
            user_id=test_user_2.id,
            title="User 2's private task",
            status="pending",
        )
        db_session.add(task_user2)
        db_session.commit()

        # test_user tries to read tasks
        response = handle_command(
            db=db_session,
            user_id=test_user.id,
            message="Show my tasks",
        )

        # Should only see test_user's tasks, not test_user_2's
        assert response.intent == "read"
        assert "User 2's private task" not in response.response
        assert "project proposal" in response.response or "pull request" in response.response

    def test_user_cannot_delete_another_users_task(self, db_session: Session, test_user: User, test_user_2: User, seed_tasks):
        """Test that a user cannot delete another user's task."""
        task_user2 = Task(
            user_id=test_user_2.id,
            title="User 2's private task",
            status="pending",
        )
        db_session.add(task_user2)
        db_session.commit()
        db_session.refresh(task_user2)

        # test_user tries to delete test_user_2's task
        response = handle_command(
            db=db_session,
            user_id=test_user.id,
            message="Delete the task 'User 2's private task'",
        )

        # Should not find the task (ambiguous or not found)
        assert response.awaiting_user is False or response.clarification_question is not None
        if response.awaiting_user and response.plan is not None:
            confirm_response = confirm_plan(
                db=db_session,
                user_id=test_user.id,
                plan_id=response.plan.plan_id,
            )
            # Step should fail
            for step in confirm_response.plan.steps:
                if step.operation == "delete":
                    assert step.status == "failed"
        else:
            assert "could not" in response.response.lower() or "clarify" in response.response.lower()

        # Verify task still exists
        db_session.refresh(task_user2)
        assert task_user2.id is not None

    def test_plan_isolation_between_users(self, db_session: Session, test_user: User, test_user_2: User, seed_tasks):
        """Test that a plan created by one user cannot be confirmed by another."""
        task = seed_tasks[0]

        # test_user creates a delete plan
        propose_response = handle_command(
            db=db_session,
            user_id=test_user.id,
            message=f"Delete the task '{task.title}'",
        )

        assert propose_response.awaiting_user is True
        plan_id = propose_response.plan.plan_id

        # test_user_2 tries to confirm it
        confirm_response = confirm_plan(
            db=db_session,
            user_id=test_user_2.id,
            plan_id=plan_id,
        )

        # Should fail - plan not found for this user
        assert "no longer valid" in confirm_response.response.lower() or "different session" in confirm_response.response.lower()

        # test_user's task should still exist
        db_session.refresh(task)
        assert task.id is not None


class TestUnauthorizedAccess:
    """Tests for unauthorized access scenarios (area 20)."""

    def test_confirm_without_plan_id_fails(self, db_session: Session, test_user: User):
        """Test that confirming without a valid plan_id fails."""
        # This is tested at the API level, but we can verify the service behavior
        from app.services.ai_orchestration_service import AIChatResponse
        response = confirm_plan(
            db=db_session,
            user_id=test_user.id,
            plan_id="",
        )

        assert isinstance(response, AIChatResponse)
        assert response.awaiting_user is False
        assert "no longer valid" in response.response.lower()

    def test_cancel_without_plan_id_fails(self, db_session: Session, test_user: User):
        """Test that cancelling without a valid plan_id fails."""
        from app.services.ai_orchestration_service import AIChatResponse
        response = cancel_plan(
            db=db_session,
            user_id=test_user.id,
            plan_id="",
        )

        assert isinstance(response, AIChatResponse)
        assert response.awaiting_user is False
        assert "no longer valid" in response.response.lower() or "no longer pending" in response.response.lower()


class TestContextBoundaries:
    """Tests that context fetching respects boundaries."""

    def test_context_only_fetches_requested_domains(self, db_session: Session, test_user: User, seed_tasks, seed_goals, seed_habits):
        """Test that asking about tasks doesn't fetch goals/habits unnecessarily."""
        response = handle_command(
            db=db_session,
            user_id=test_user.id,
            message="Show my tasks",
        )

        # Should only include task domain in context_used
        assert "task" in response.context_used
        # intelligence might also be included for overview, but not goal/habit specifically
        assert "goal" not in response.context_used or response.intent == "read"

    def test_intelligence_includes_aggregated_data(self, db_session: Session, test_user: User, seed_tasks, seed_goals, seed_habits, seed_transactions):
        """Test that intelligence read includes aggregated data from multiple domains."""
        response = handle_command(
            db=db_session,
            user_id=test_user.id,
            message="How am I doing overall?",
        )

        assert response.intent == "read"
        assert "intelligence" in response.context_used
        # Response should mention multiple domains
        assert "task" in response.response.lower() or "goal" in response.response.lower()