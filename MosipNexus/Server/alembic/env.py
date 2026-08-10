"""Alembic environment — uses PG_CONNECTION; only migrates app Base metadata."""

from __future__ import annotations

import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

# Server/ on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.settings import PG_CONNECTION  # noqa: E402
from db.base import Base  # noqa: E402
import db.models  # noqa: E402, F401 — register models

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata
# set_main_option() writes through a ConfigParser, which treats "%" as the
# start of interpolation syntax (%(name)s) — a password containing a
# percent-encoded character (e.g. "@" -> "%40") raises
# "invalid interpolation syntax" unless every literal "%" is escaped as "%%"
# first. ConfigParser un-escapes "%%" -> "%" again on read, so this round-trips
# back to the exact original PG_CONNECTION value.
config.set_main_option("sqlalchemy.url", PG_CONNECTION.replace("%", "%%"))

# Never touch LangChain-owned tables
_SKIP_TABLES = {
    "langchain_pg_collection",
    "langchain_pg_embedding",
    "alembic_version",
}


def include_object(object, name, type_, reflected, compare_to):
    if type_ == "table" and name in _SKIP_TABLES:
        return False
    if type_ == "table" and name and name.startswith("langchain_"):
        return False
    return True


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_object,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
