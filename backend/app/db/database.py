from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config.settings import settings


def _engine_kwargs_for_url(url: str) -> dict:
    """
    Return engine kwargs appropriate for the database dialect.

    SQLite does not support pool_size, max_overflow, pool_pre_ping, pool_recycle.
    PostgreSQL and other client-server databases benefit from these settings.
    """
    if url.startswith("sqlite"):
        # SQLite: minimal config, no pooling args
        return {"connect_args": {"check_same_thread": False}}

    # PostgreSQL (or other client-server): use production pool settings
    return {
        "pool_size": 5,
        "max_overflow": 5,
        "pool_pre_ping": True,
        "pool_recycle": 1800,
    }


engine = create_engine(
    settings.DATABASE_URL,
    **_engine_kwargs_for_url(settings.DATABASE_URL),
)

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)
