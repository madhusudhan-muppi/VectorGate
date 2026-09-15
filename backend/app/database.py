"""Configurable SQLAlchemy database setup."""

from __future__ import annotations

import os
from collections.abc import Generator
from pathlib import Path

from datetime import datetime, timezone

from sqlalchemy import DateTime, create_engine
from sqlalchemy.types import TypeDecorator
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

DEFAULT_DATABASE_URL = "sqlite:///data/vectorgate.db"


def database_url() -> str:
    return os.getenv("VECTORGATE_DATABASE_URL", DEFAULT_DATABASE_URL)


def _connect_args(url: str) -> dict[str, object]:
    return {"check_same_thread": False} if url.startswith("sqlite") else {}


def _ensure_sqlite_parent(url: str) -> None:
    if not url.startswith("sqlite:///") or url == "sqlite:///:memory:":
        return
    path = Path(url.removeprefix("sqlite:///"))
    path.parent.mkdir(parents=True, exist_ok=True)


class Base(DeclarativeBase):
    pass


class UTCDateTime(TypeDecorator[datetime]):
    """Store UTC timestamps portably and return timezone-aware datetimes."""

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: object) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamps must be timezone-aware")
        return value.astimezone(timezone.utc).replace(tzinfo=None)

    def process_result_value(self, value: datetime | None, dialect: object) -> datetime | None:
        return value.replace(tzinfo=timezone.utc) if value is not None else None


engine = None
SessionLocal = sessionmaker(autoflush=False, expire_on_commit=False)


def configure_database(url: str | None = None) -> None:
    """Configure the process-local engine, primarily for app factories/tests."""
    global engine
    selected_url = url or database_url()
    _ensure_sqlite_parent(selected_url)
    engine = create_engine(selected_url, connect_args=_connect_args(selected_url))
    SessionLocal.configure(bind=engine)


configure_database()


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    from . import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
