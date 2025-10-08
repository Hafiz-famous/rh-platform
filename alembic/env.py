# alembic/env.py
import os, sys
from alembic import context

# --- rendre importable "app" ---
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app import create_app
from app.extensions import db

config = context.config

# --- logging Alembic optionnel (ne pas planter si sections absentes) ---
try:
    from logging.config import fileConfig
    from configparser import ConfigParser
    if config.config_file_name:
        _cp = ConfigParser()
        _cp.read(config.config_file_name)
        if _cp.has_section("loggers"):
            fileConfig(config.config_file_name)
except Exception:
    pass

# --- Boot Flask et lie Alembic à la config de BDD ---
flask_app = create_app()
with flask_app.app_context():
    config.set_main_option("sqlalchemy.url", flask_app.config["SQLALCHEMY_DATABASE_URI"])
    target_metadata = db.metadata


def run_migrations_offline():
    """Mode offline : pas d’engine, URL directe."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Mode online : engine Flask **dans un app_context**."""
    with flask_app.app_context():
        connectable = db.engine
        with connectable.connect() as connection:
            context.configure(
                connection=connection,
                target_metadata=target_metadata,
                compare_type=True,
                compare_server_default=True,
            )
            with context.begin_transaction():
                context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
