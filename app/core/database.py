"""
Sanchay — Database Engine & Session Factory
=============================================
Manages the SQLAlchemy engine and session lifecycle.
Uses SQLite by default; can be swapped to PostgreSQL/MySQL
by changing DB_URL in config without touching this file.
"""

from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, Session, DeclarativeBase
from loguru import logger

from app.config import config


# ── Declarative Base ──────────────────────────────────────────────────────────

class Base(DeclarativeBase):
    """
    SQLAlchemy declarative base for all ORM models.
    All models inherit from this class.
    """
    pass


# ── Engine Factory ────────────────────────────────────────────────────────────

def _build_engine():
    """
    Build and configure the SQLAlchemy engine.
    Applies SQLite-specific pragmas for performance and integrity.
    """
    engine = create_engine(
        config.DB_URL,
        echo=config.DB_ECHO,
        connect_args={"check_same_thread": False},  # Required for SQLite + multi-thread Qt
    )

    # ── SQLite-specific optimizations ─────────────────────────────────────────
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")      # Better concurrency
        cursor.execute("PRAGMA synchronous=NORMAL")    # Balance safety/speed
        cursor.execute("PRAGMA foreign_keys=ON")       # Enforce FK constraints
        cursor.execute("PRAGMA cache_size=-64000")     # 64 MB cache
        cursor.execute("PRAGMA temp_store=MEMORY")     # Temp tables in RAM
        cursor.close()

    logger.info(f"Database engine created: {config.DB_URL}")
    return engine


# ── Session Factory ───────────────────────────────────────────────────────────

# Lazy initialization so tests can override DB_URL before building
_engine = None
_SessionFactory = None


def get_engine():
    global _engine
    if _engine is None:
        _engine = _build_engine()
    return _engine


def get_session_factory():
    global _SessionFactory
    if _SessionFactory is None:
        _SessionFactory = sessionmaker(
            bind=get_engine(),
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,
        )
    return _SessionFactory


# ── Context Manager ───────────────────────────────────────────────────────────

@contextmanager
def get_db() -> Generator[Session, None, None]:
    """
    Provide a transactional database session.
    
    Usage:
        with get_db() as db:
            result = db.query(User).all()
    
    Commits on success, rolls back on exception.
    """
    SessionFactory = get_session_factory()
    session: Session = SessionFactory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# ── Database Initialization ───────────────────────────────────────────────────

def init_db() -> None:
    """
    Create all tables defined in ORM models.
    Safe to call multiple times — only creates missing tables.
    Must import all models before calling this.
    """
    # Import all models to register them with Base.metadata
    from app.models import (  # noqa: F401
        user, organization, person, asset, transaction, audit
    )

    config.init_directories()
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables initialized.")


def drop_all_tables() -> None:
    """
    Drop all tables. USE WITH EXTREME CAUTION.
    Only for development/testing.
    """
    from app.models import (  # noqa: F401
        user, organization, person, asset, transaction, audit
    )
    engine = get_engine()
    Base.metadata.drop_all(bind=engine)
    logger.warning("All database tables dropped.")


def check_connection() -> bool:
    """Verify the database connection is working."""
    try:
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"Database connection check failed: {e}")
        return False
