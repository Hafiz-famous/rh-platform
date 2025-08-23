# app/__init__.py
from __future__ import annotations
import os
from flask import Flask
from .extensions import db, migrate, login_manager, mail

# --- formatage FR (Babel si dispo, sinon strftime) ---
try:
    from babel.dates import format_date as _format_date  # pip install Babel
    def fr_month_label(d):  # ex: "août 2025"
        return _format_date(d, format="LLLL yyyy", locale="fr_FR")
except Exception:
    def fr_month_label(d):
        return d.strftime("%B %Y").capitalize()


def _as_bool(val: str | None) -> bool:
    if val is None:
        return False
    return str(val).strip().lower() in {"1", "true", "yes", "on"}


def create_app() -> Flask:
    app = Flask(__name__)
    try:
        os.makedirs(app.instance_path, exist_ok=True)
    except Exception:
        pass

    default_db = "sqlite:///" + os.path.join(app.instance_path, "rh_platform.db")
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev-secret"),
        SQLALCHEMY_DATABASE_URI=os.environ.get("DATABASE_URL", default_db),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        REGISTER_OPEN=True,
        PUBLIC_BASE_URL=os.environ.get("PUBLIC_BASE_URL", "http://127.0.0.1:5000"),
        WORK_START=os.environ.get("WORK_START", "09:00"),
        TARDINESS_GRACE_MIN=int(os.environ.get("TARDINESS_GRACE_MIN", "5")),
        # Mail
        MAIL_ENABLED=_as_bool(os.environ.get("MAIL_ENABLED")),
        SMTP_HOST=os.environ.get("SMTP_HOST", ""),
        SMTP_PORT=int(os.environ.get("SMTP_PORT", "587")),
        SMTP_USER=os.environ.get("SMTP_USER"),
        SMTP_PASSWORD=os.environ.get("SMTP_PASSWORD"),
        SMTP_TLS=_as_bool(os.environ.get("SMTP_TLS") or "1"),
        SMTP_SSL=_as_bool(os.environ.get("SMTP_SSL") or "0"),
        MAIL_SENDER_NAME=os.environ.get("MAIL_SENDER_NAME", "RH Platform"),
        MAIL_SENDER=os.environ.get("MAIL_SENDER", "noreply@example.com"),
        MAIL_BACKEND=os.environ.get("MAIL_BACKEND"),
        # ADDED (dev confort) : rechargement auto des templates
        TEMPLATES_AUTO_RELOAD=True,
    )
    if "REGISTER_OPEN" in os.environ:
        app.config["REGISTER_OPEN"] = _as_bool(os.environ.get("REGISTER_OPEN"))

    # --- Extensions ---
    db.init_app(app)
    from . import models  # important pour que Migrate "voit" les modèles
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message_category = "warning"

    # --- Mail ---
    if mail is not None:
        if not app.config.get("MAIL_BACKEND"):
            app.config["MAIL_BACKEND"] = "smtp" if app.config["MAIL_ENABLED"] else "console"
        if app.config.get("SMTP_HOST"):
            app.config["MAIL_SERVER"] = app.config["SMTP_HOST"]
        if app.config.get("SMTP_PORT") is not None:
            app.config["MAIL_PORT"] = app.config["SMTP_PORT"]
        if app.config.get("SMTP_USER"):
            app.config["MAIL_USERNAME"] = app.config["SMTP_USER"]
        if app.config.get("SMTP_PASSWORD"):
            app.config["MAIL_PASSWORD"] = app.config["SMTP_PASSWORD"]
        app.config["MAIL_USE_TLS"] = app.config["SMTP_TLS"]
        app.config["MAIL_USE_SSL"] = app.config["SMTP_SSL"]
        app.config["MAIL_DEFAULT_SENDER"] = (
            app.config["MAIL_SENDER_NAME"],
            app.config["MAIL_SENDER"],
        )
        if app.config.get("MAIL_BACKEND") == "file":
            app.config.setdefault("MAIL_FILE_PATH", os.path.join(app.instance_path, "mailoutbox"))
        mail.init_app(app)
    else:
        app.logger.warning("Mail désactivé (Flask-Mailman non installé).")

    # --- Blueprints "globaux" ---
    from .routes import register_blueprints
    register_blueprints(app)

    # ADDED : enregistre explicitement les routes QR & API de pointage si présents
    try:
        from .routes.qr_routes import qr_bp
        app.register_blueprint(qr_bp)
    except Exception as e:
        app.logger.debug("QR routes non chargées: %s", e)

    try:
        from .routes.attendance_api import attendance_api
        app.register_blueprint(attendance_api)
    except Exception as e:
        app.logger.debug("Attendance API non chargée: %s", e)

    # ADDED : helpers accessibles dans les templates
    def url_public(path: str) -> str:
        base = app.config["PUBLIC_BASE_URL"].rstrip("/")
        return f"{base}{path}"
    app.jinja_env.globals["url_public"] = url_public
    app.jinja_env.filters["fr_month_label"] = fr_month_label  # {{ date|fr_month_label }}

    # --- Jinja context (Role + Employé·e du mois) ---
    from .models.enums import Role
    from sqlalchemy import func
    from .models.employee_of_month import EmployeeOfMonth

    @app.context_processor
    def inject_enums_and_config():
        eom_obj = None
        eom_name = None
        try:
            period = db.session.query(func.max(EmployeeOfMonth.period)).scalar()
            if period:
                e = db.session.query(EmployeeOfMonth).filter_by(period=period).first()
                if e and getattr(e, "user", None):
                    eom_name = (f"{e.user.first_name} {e.user.last_name}".strip() or e.user.email)
                    dept = getattr(getattr(e.user, "department", None), "name", None)
                    eom_obj = {
                        "name": eom_name,
                        "department": dept,
                        "period_label": fr_month_label(period),
                        "period": str(period),
                        "note": e.note or "",
                        "user_id": e.user_id,
                    }
        except Exception:
            eom_obj = None
            eom_name = None

        return {"Role": Role, "config": app.config, "eom_name": eom_name, "employee_of_month": eom_obj}

    # Logs utiles (DB + mail)
    app.logger.info("DB URI -> %s", app.config["SQLALCHEMY_DATABASE_URI"])
    app.logger.info(
        "MAIL -> backend=%s server=%s port=%s tls=%s ssl=%s sender=%s",
        app.config.get("MAIL_BACKEND"),
        app.config.get("MAIL_SERVER"),
        app.config.get("MAIL_PORT"),
        app.config.get("MAIL_USE_TLS"),
        app.config.get("MAIL_USE_SSL"),
        app.config.get("MAIL_DEFAULT_SENDER"),
    )
    return app
