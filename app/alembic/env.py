from __future__ import with_statement
import os
from logging.config import fileConfig

from sqlalchemy import create_engine, pool
from alembic import context

# Import your Base from wherever your models are defined
# Adjust this import path if needed
from app.db.models import Base
from app.core.config import settings  # Adjust if your settings are in a different place

# ---------------------------------------------------------
# Alembic Config object, which provides access to .ini file
# ---------------------------------------------------------
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set target metadata for 'autogenerate' support
target_metadata = Base.metadata


# ---------------------------------------------------------
# Database URL setup
# ---------------------------------------------------------
def get_sync_database_url() -> str:
    """
    Alembic cannot work with async drivers like +asyncpg.
    This function converts an async URL (postgresql+asyncpg://)
    into a sync one (postgresql://) for Alembic.
    """
    url = os.getenv("DOCKER_DATABASE_URL") or settings.DATABASE_URL
    if "+asyncpg" in url:
        url = url.replace("+asyncpg", "")
    return url


# ---------------------------------------------------------
# Offline mode: no DB connection, just generates SQL scripts
# ---------------------------------------------------------
def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = get_sync_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


# ---------------------------------------------------------
# Online mode: connect to DB and run migrations
# ---------------------------------------------------------
def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = create_engine(
        get_sync_database_url(),
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


# ---------------------------------------------------------
# Entry point
# ---------------------------------------------------------
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()