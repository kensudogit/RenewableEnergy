from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from src.config import get_settings

_engine: Engine | None = None
SessionLocal: sessionmaker[Session] | None = None


def get_engine() -> Engine:
    global _engine, SessionLocal
    if _engine is None:
        settings = get_settings()
        _engine = create_engine(settings.database_url, pool_pre_ping=True)
        SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False)
    return _engine


@contextmanager
def get_session() -> Generator[Session, None, None]:
    get_engine()
    assert SessionLocal is not None
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_database() -> None:
    """Apply init.sql when DB is reachable; ignore if unavailable (sample mode)."""
    init_sql = Path(__file__).resolve().parent.parent / "db" / "init.sql"
    if not init_sql.exists():
        return
    try:
        engine = get_engine()
        with engine.begin() as conn:
            conn.execute(text(init_sql.read_text(encoding="utf-8")))
    except Exception:
        # Local sample forecasts still work without Postgres
        pass
