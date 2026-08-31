"""Database engine and session management.

Three things live here, and nowhere else should construct them directly:
  1. `get_engine()`          -- lazily builds and caches the connection pool
  2. `get_session_factory()` -- lazily builds and caches the session factory
  3. `get_db()`               -- the FastAPI dependency that yields a Session
  4. `Base`                   -- the class every ORM model inherits from

Deliberately synchronous (psycopg2, not asyncpg). A `def` route (not
`async def`) that does blocking DB work gets offloaded to a threadpool
automatically -- the exact rule from Phase 1's health check, just applied
in the other direction. Async SQLAlchemy exists and is faster under heavy
concurrency, but it stacks async session syntax on top of ORM syntax you're
still learning. Sync first; revisit later once the ORM itself is familiar.
"""

from collections.abc import Generator
from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings


class Base(DeclarativeBase):
    """Base class every ORM model inherits from.

    SQLAlchemy uses this to collect metadata about every table you define
    (via subclasses) in one place -- Alembic reads that metadata to figure
    out what your schema *should* look like, and diffs it against what the
    database actually has.
    """

    pass


@lru_cache
def get_engine() -> Engine:
    """Build and cache the database engine -- on first use, not at import.

    This was a real bug in the first version of this file: calling
    create_engine(settings.database_url) directly at module import time
    meant the ENTIRE app -- including the already-working Phase 1 /health
    endpoint -- crashed on startup the moment DATABASE_URL was empty.
    Importing app.main imports the documents router, which imports this
    file, which ran create_engine() immediately.

    Wrapping it in a cached function means the engine is only constructed
    the first time something actually calls get_db() -- so the app still
    boots and /health still works with no database configured at all. Only
    requests that touch a document route fail, and only when called, with
    a clear error explaining why.

    pool_pre_ping issues a cheap "is this connection still alive" check
    before handing a pooled connection to your code -- without it, a
    connection Supabase silently closed after idling surfaces as a
    confusing mid-request error instead of a clean automatic reconnect.
    """
    settings = get_settings()
    if not settings.database_url:
        raise RuntimeError(
            "DATABASE_URL is not set. Add your Supabase connection string "
            "to .env -- see README.md's Phase 2 setup section."
        )
    return create_engine(settings.database_url, pool_pre_ping=True)


@lru_cache
def get_session_factory() -> sessionmaker[Session]:
    """Build and cache the session factory, bound to the cached engine.

    A sessionmaker is cheap to construct, but there's no reason to rebuild
    it on every single request when get_db() is called dozens of times a
    second under load. Caching it here mirrors get_engine() exactly -- built
    once, reused everywhere, still lazy (only happens on first real use).

    autocommit=False: changes only persist on an explicit session.commit()
    -- accidental writes can't slip through.
    autoflush=False: SQLAlchemy won't silently send pending changes to the
    database mid-query without being asked.
    """
    return sessionmaker(autocommit=False, autoflush=False, bind=get_engine())


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields one Session per request.

    Note the `yield` instead of `return` -- everything before `yield` runs
    before your route handler; everything after runs after the handler
    finishes, even if it raised an exception. That's what guarantees
    db.close() always runs: the session gets returned to the pool whether
    the request succeeded or failed.

    Same Depends(...) mechanism as Phase 1's get_settings, just with
    teardown added.
    """
    db = get_session_factory()()
    try:
        yield db
    finally:
        db.close()
