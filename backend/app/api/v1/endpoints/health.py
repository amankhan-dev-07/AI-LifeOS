from fastapi import APIRouter
from sqlalchemy import text

from app.db.database import engine

router = APIRouter(tags=["Health"])


@router.get("/health")
def health_check():
    """
    Liveness plus a real database round-trip.

    Reporting "healthy" without touching the database would be a fake
    operational state: a container can pass its health check while every
    authenticated request fails on a broken connection or a missing migration.
    One cheap `SELECT 1` makes the check mean something.
    """

    database_ok = True

    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception:
        database_ok = False

    if database_ok:
        return {
            "status": "healthy",
            "database": "ok",
        }

    # The message changes with the status so a degraded response never reads
    # as a cheerful "API is running 🚀" while the database is unreachable.
    return {
        "status": "degraded",
        "database": "unavailable",
        "message": "The API is running but the database is not reachable.",
    }


@router.get("/health/live")
def liveness_check():
    """
    Process liveness only.

    Deliberately does not touch the database, so an orchestrator can tell
    "the process is wedged" apart from "the database is unreachable" and
    restart only in the first case.
    """

    return {"status": "alive"}
