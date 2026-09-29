from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

from app.models.base import Base
from app.models import entities  # noqa: F401
from app.services import scheduler_service  # noqa: F401
from app.models import rbac  # noqa: F401

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _resolved_url() -> str:
    from pathlib import Path
    from app.models.base import DATABASE_URL
    if DATABASE_URL.startswith("sqlite:"):
        prefix = "sqlite:///"
        path_part = DATABASE_URL[len(prefix):]
        p = Path(path_part)
        p.parent.mkdir(parents=True, exist_ok=True)
        return f"{prefix}{p.as_posix()}"
    return DATABASE_URL


def run_migrations_offline() -> None:
    url = _resolved_url()
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True,
                      dialect_opts={"paramstyle": "named"})
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    config.set_main_option("sqlalchemy.url", _resolved_url())
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.", poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
