"""
In-process reminder scheduler.

The backend has exactly one worker: an asyncio task started on FastAPI's
lifespan event. Every tick opens its own short-lived database session through
the existing `SessionLocal`, reads only pending reminders that are due, writes
one notification each, and stamps `notified_at` so a reminder can never be
delivered twice — not across ticks, and not across a restart.

No Redis, no Celery, no external worker. The only scheduling state is the
`reminders` table itself, which is what makes overdue reminders survive a
backend restart: after a restart the first tick simply re-reads the same rows.
"""

import asyncio
import contextlib
import logging
from datetime import datetime

from app.db.database import SessionLocal
from app.models.reminder import Reminder
from app.repositories.notification_repository import create_notification
from app.repositories.reminder_repository import get_due_reminders
from app.services.reminder_service import STATUS_COMPLETED

logger = logging.getLogger(__name__)

# One minute keeps a reminder firing within a minute of its time, at the cost
# of a single indexed range query. Deliberately low frequency — a slower tick
# would delay reminders, and a faster one would buy nothing for an in-app
# notification.
TICK_INTERVAL_SECONDS = 60

# Bounds the work done in a single tick so a large backlog (first run after a
# long downtime) can never monopolize the connection pool.
MAX_REMINDERS_PER_TICK = 50

# Longest single tick before we log and continue. A stuck query must not take
# the scheduler down for good.
TICK_TIMEOUT_SECONDS = 20


def build_notification_link(reminder: Reminder) -> str | None:
    """
    Map a reminder to the LifeOS page that gives it context.

    A link is only produced when the referenced row still exists — the FKs are
    SET NULL on delete, so a dangling reference must not navigate anywhere.
    """

    if reminder.task_id is not None:
        return "/tasks"

    if reminder.planner_event_id is not None:
        return "/planner"

    if reminder.habit_id is not None:
        return "/habits"

    return None


def build_notification_message(reminder: Reminder) -> str:
    if reminder.message and reminder.message.strip():
        return reminder.message.strip()

    return f"Reminder scheduled for {reminder.remind_at.isoformat()} UTC."


def process_due_reminders(db, now: datetime | None = None) -> int:
    """
    Deliver every due reminder once. Returns the number of notifications
    created.

    Marking `notified_at` and completing the reminder happen in the same
    session as the notification insert, so the row can never be left claiming
    to be pending after its notification exists.
    """

    now = now or datetime.utcnow()

    due_reminders = get_due_reminders(
        db=db,
        now=now,
        limit=MAX_REMINDERS_PER_TICK,
    )

    if not due_reminders:
        return 0

    delivered = 0

    for reminder in due_reminders:
        # Each reminder is delivered in its own transaction, so one bad row
        # cannot roll back the notifications already written for the others.
        # The notification insert and the `notified_at` stamp share that
        # transaction, so a reminder can never be left pending after its
        # notification exists.
        try:
            create_notification(
                db=db,
                user_id=reminder.user_id,
                title=reminder.title,
                message=build_notification_message(reminder),
                type="info",
                link=build_notification_link(reminder),
            )

            reminder.notified_at = now
            reminder.is_completed = True
            reminder.is_cancelled = False
            reminder.status = STATUS_COMPLETED
            db.commit()
        except Exception:
            db.rollback()
            logger.exception(
                "Failed to deliver reminder %s",
                reminder.id,
            )
            continue

        delivered += 1

    logger.info(
        "Reminder scheduler delivered %s reminder(s)",
        delivered,
    )

    return delivered


async def _run_tick() -> int:
    """Open a session, process due reminders, and always close the session."""

    db = SessionLocal()

    try:
        return process_due_reminders(db=db)
    except Exception:
        db.rollback()
        # Never let one bad tick kill the loop; the reminders stay pending in
        # PostgreSQL and are retried on the next tick.
        logger.exception("Reminder scheduler tick failed")
        return 0
    finally:
        db.close()


async def scheduler_loop() -> None:
    """
    The scheduler's main loop.

    The first tick runs immediately on startup so a backend restart delivers
    any reminders that came due while it was down, rather than waiting a full
    interval first.
    """

    logger.info("Reminder scheduler started")

    while True:
        try:
            await asyncio.wait_for(
                _run_tick(),
                timeout=TICK_TIMEOUT_SECONDS,
            )
        except asyncio.TimeoutError:
            logger.error("Reminder scheduler tick exceeded %ss", TICK_TIMEOUT_SECONDS)
        except asyncio.CancelledError:
            # Clean shutdown: re-raise so the task ends cancelled.
            logger.info("Reminder scheduler stopping")
            raise
        except Exception:
            logger.exception("Reminder scheduler loop error")

        await asyncio.sleep(TICK_INTERVAL_SECONDS)


def start_scheduler(app) -> None:
    """Attach the scheduler loop to the app's lifespan startup."""

    @contextlib.asynccontextmanager
    async def lifespan(_app):
        task = asyncio.create_task(scheduler_loop())

        try:
            yield
        finally:
            # Cancel the loop and wait for it to unwind so no tick is left
            # running against a closing event loop.
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    app.router.lifespan_context = lifespan
