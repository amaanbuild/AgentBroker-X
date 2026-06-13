"""Database engine, session factory, and declarative base."""
from __future__ import annotations

import time
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session

from .config import settings

_url = settings.normalized_database_url()
if _url.startswith("sqlite"):
    _connect_args = {"check_same_thread": False}
else:
    # Fail fast instead of hanging if the database is briefly unreachable at
    # boot (on Railway the private DNS may not be ready for a second or two).
    _connect_args = {"connect_timeout": 10}

engine = create_engine(
    _url,
    connect_args=_connect_args,
    pool_pre_ping=True,
    future=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a scoped session and always closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db(retries: int = 6, delay: float = 2.0) -> None:
    """Create tables, retrying briefly while the database becomes reachable.

    On first boot the database may take a moment to accept connections; we
    retry a few times so a transient delay does not crash startup.
    """
    from . import models  # noqa: F401  (ensure models are imported/registered)

    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            Base.metadata.create_all(bind=engine)
            return
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            print(f"[init_db] attempt {attempt}/{retries} failed: {exc}")
            time.sleep(delay)
    if last_error is not None:
        raise last_error
