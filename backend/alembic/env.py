from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.config import settings
from app.database import Base
# Импорт нужен ради побочного эффекта: модели регистрируются в Base.metadata для autogenerate.
from app import models  # noqa

config = context.config
# URL берётся из настроек приложения, значение из alembic.ini игнорируется.
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

if config.config_file_name is not None:
    # Настройки логирования берутся из секций [logger_*] alembic.ini.
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


# offline: генерирует SQL-скрипт без подключения к БД (alembic upgrade --sql).
def run_migrations_offline():
    # literal_binds подставляет значения прямо в текст SQL вместо параметров.
    context.configure(url=settings.DATABASE_URL, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        # NullPool: миграции - разовый процесс, пул соединений не нужен.
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
