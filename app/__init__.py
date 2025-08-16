# app/__init__.py
from __future__ import annotations
import os
from flask import Flask
from .extensions import db, migrate, login_manager

def _as_bool(val: str | None) -> bool:
    if val is None:
        return False
    return str(val).strip().lower() in {"1", "true", "yes", "on"}

def create_app() -> Flask:
    app = Flask(__name__)

    # Config de base + paramètres utilisés par les features (QR, mails, retard, inscriptions)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev-secret"),
        SQLALCHEMY_DATABASE_URI=os.environ.get("DATABASE_URL", "sqlite:///rh.db"),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,

        # Inscriptions publiques (register)
        REGISTER_OPEN=True,  # override via env REGISTER_OPEN=0/1

        # QR / links publics
        PUBLIC_BASE_URL=os.environ.get("PUBLIC_BASE_URL", "http://127.0.0.1:5000"),

        # Retards / horaires
        WORK_START=os.environ.get("WORK_START", "09:00"),
        TARDINESS_GRACE_MIN=int(os.environ.get("TARDINESS_GRACE_MIN", "5")),

        # Email (désactivé par défaut)
        MAIL_ENABLED=_as_bool(os.environ.get("MAIL_ENABLED")),
        SMTP_HOST=os.environ.get("SMTP_HOST", ""),
        SMTP_PORT=int(os.environ.get("SMTP_PORT", "587")),
        SMTP_USER=os.environ.get("SMTP_USER"),
        SMTP_PASSWORD=os.environ.get("SMTP_PASSWORD"),
        SMTP_TLS=_as_bool(os.environ.get("SMTP_TLS") or "1"),
        MAIL_SENDER_NAME=os.environ.get("MAIL_SENDER_NAME", "RH Platform"),
        MAIL_SENDER=os.environ.get("MAIL_SENDER", "noreply@example.com"),
    )

    # Override bool explicite via env
    if "REGISTER_OPEN" in os.environ:
        app.config["REGISTER_OPEN"] = _as_bool(os.environ.get("REGISTER_OPEN"))

    # Init extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"

    # Blueprints
    from .routes import register_blueprints
    register_blueprints(app)

    # Enums / helpers injectés dans Jinja (⚠️ à l'intérieur de create_app)
    from .models.enums import Role

    @app.context_processor
    def inject_enums_and_config():
        # Permet d'utiliser {{ Role }} et {{ config }} dans les templates
        return {"Role": Role, "config": app.config}

    return app
