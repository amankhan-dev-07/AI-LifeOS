from collections.abc import Generator

from sqlalchemy.orm import Session

from app.db.database import SessionLocal


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()

    try:
        yield db
    except Exception:
        # A request that raised mid-transaction leaves the session holding an
        # open, failed transaction. `Session.close()` returns the connection to
        # the pool, so without an explicit rollback the next request that
        # receives that same pooled connection inherits the aborted state.
        db.rollback()
        raise
    finally:
        db.close()