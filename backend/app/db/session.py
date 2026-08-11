"""Database engine and session factory.

Uses DATABASE_URL when set (Neon Postgres). Falls back to local SQLite
so the full pipeline is runnable without cloud credentials.
"""

from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

DEFAULT_SQLITE = f"sqlite:///{Path(__file__).resolve().parents[2] / 'optichain.db'}"
DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_SQLITE)

# Neon / Render sometimes provide postgres:// — SQLAlchemy wants postgresql://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create all tables. Import models before calling."""
    from app.db import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
