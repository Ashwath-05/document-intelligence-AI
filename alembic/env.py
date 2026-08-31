from logging.config import fileConfig

from sqlalchemy import create_engine, pool

from alembic import context

# Import our own app so Alembic can see the models and the real DB URL.
# Importing Document (not just Base) matters: a model only registers itself
# on Base.metadata by being imported somewhere. If a model exists but is
# never imported, Alembic won't know it exists and autogenerate will silently
# skip it. As you add models in later phases, they must be imported here too.
from app.core.config import get_settings
from app.core.database import Base
from app.models.document import Document  # noqa: F401 -- import registers the model

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# This is what makes `alembic revision --autogenerate` work: Alembic diffs
# the real database's current schema against Base.metadata (built from every
# model that subclasses Base) and writes the difference as a migration.
target_metadata = Base.metadata

# IMPORTANT: kept as a plain Python string, NEVER passed through
# config.set_main_option(...). Alembic's .ini-backed config is built on
# Python's ConfigParser, which treats `%` as ITS OWN special interpolation
# character (e.g. %(name)s). A password containing a URL-encoded character
# like %40 (an escaped @) gets misread as broken interpolation syntax and
# crashes with "invalid interpolation syntax" -- even though the URL itself
# is completely valid. Keeping it in a plain variable and passing it directly
# to create_engine()/context.configure() below sidesteps ConfigParser, and
# therefore this whole class of bug, entirely.
DATABASE_URL = get_settings().database_url


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode -- emits SQL without a live connection."""
    context.configure(
        url=DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode -- connects and applies directly."""
    connectable = create_engine(DATABASE_URL, poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()