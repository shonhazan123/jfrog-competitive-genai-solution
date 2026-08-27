from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool, text

from app.models.base import Base
import app.models.capture  # noqa: F401
import app.models.delivery  # noqa: F401
import app.models.ledger  # noqa: F401
import app.models.registry  # noqa: F401
import app.models.signal  # noqa: F401
from app.settings import settings

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

MIGRATION_LOCK_KEY = 811223344556677


def run_migrations_offline() -> None:
    url = settings.database_url
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = settings.database_url
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        try:
            connection.execute(
                text("SELECT pg_advisory_lock(:k)"),
                {"k": MIGRATION_LOCK_KEY},
            )
            connection.commit()

            context.configure(
                connection=connection, target_metadata=target_metadata
            )

            with context.begin_transaction():
                context.run_migrations()
        finally:
            connection.execute(
                text("SELECT pg_advisory_unlock(:k)"),
                {"k": MIGRATION_LOCK_KEY},
            )
            connection.commit()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
