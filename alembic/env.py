# migrations/env.py
import os
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

from app import create_app
from app.extensions import db
# Charge tous les modèles pour que metadata voie tout
from app import models as _models  # noqa

# --- Alembic config ---
config = context.config

# Logger Alembic (si alembic.ini présent)
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# --- Crée et pousse l'app Flask ---
app = create_app()
app.app_context().push()

# --- Choix/normalisation de l'URI DB ---
def _normalize_sqlite_uri(app, uri: str | None) -> str | None:
    if not uri or not uri.startswith("sqlite:///"):
        return uri
    path = uri[len("sqlite:///"):]
    # Absolu -> normaliser seulement les slashes
    if os.path.isabs(path):
        return "sqlite:///" + path.replace("\\", "/")
    # Relatif -> ancrer sur la racine du projet
    abs_path = os.path.join(app.root_path, path)
    return "sqlite:///" + os.path.abspath(abs_path).replace("\\", "/")

db_uri = os.getenv("DATABASE_URL") or app.config.get("SQLALCHEMY_DATABASE_URI")
db_uri = _normalize_sqlite_uri(app, db_uri)
if db_uri:
    config.set_main_option("sqlalchemy.url", db_uri)

# --- Target metadata ---
target_metadata = db.metadata

# --- Offline ---
def run_migrations_offline():
    context.configure(
        url=db_uri,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
        render_as_batch=(db_uri or "").startswith("sqlite:///"),
    )
    with context.begin_transaction():
        context.run_migrations()

# --- Online ---
def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",          # ✅ important
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        is_sqlite = (connection.dialect.name == "sqlite")
        if is_sqlite:
            # pour respecter les FK pendant les migrations SQLite
            connection.exec_driver_sql("PRAGMA foreign_keys=ON")

        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
            render_as_batch=is_sqlite,  # facilite ALTER TABLE sous SQLite
        )
        with context.begin_transaction():
            context.run_migrations()

# --- Runner ---
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
