# app/__init__.py
from __future__ import annotations

import os
from datetime import date
from flask import Flask
from .extensions import db, migrate, login_manager, mail
from .utils import fmt_hours

# --- formatage FR (Babel si dispo, sinon strftime) ---
try:
    from babel.dates import format_date as _format_date  # pip install Babel

    def fr_month_label(d):  # ex: "août 2025"
        return _format_date(d, format="LLLL yyyy", locale="fr_FR")
except Exception:
    def fr_month_label(d):
        return d.strftime("%B %Y").capitalize()


def _normalize_sqlite_uri(app: Flask, uri: str) -> str:
    """Rend absolues et uniformes les URI sqlite:///..."""
    if not uri or not uri.startswith("sqlite:///"):
        return uri
    path = uri[len("sqlite:///") :].replace("\\", "/")
    if os.path.isabs(path):
        abs_path = path
    else:
        if path.startswith(("instance/", "instance\\")):
            rel = path.split("/", 1)[1] if "/" in path else ""
            abs_path = os.path.join(app.instance_path, rel)
        else:
            abs_path = os.path.join(app.root_path, path)
    return "sqlite:///" + os.path.abspath(abs_path).replace("\\", "/")


def _normalize_database_uri(uri: str) -> str:
    """Corrige 'postgres://' (Heroku) en 'postgresql://'."""
    if uri and uri.startswith("postgres://"):
        return uri.replace("postgres://", "postgresql://", 1)
    return uri


def _env_bool(name: str, default: bool = False) -> bool:
    v = os.environ.get(name)
    if v is None:
        return default
    return str(v).strip().lower() in {"1", "true", "t", "yes", "y", "on"}


def _safe_register(app: Flask, bp):
    """Enregistre un blueprint en évitant les doublons."""
    name = getattr(bp, "name", None) or getattr(bp, "import_name", None)
    if name in app.blueprints:
        app.logger.debug("Blueprint '%s' déjà enregistré, on ignore.", name)
        return
    app.register_blueprint(bp)


def create_app() -> Flask:
    app = Flask(__name__, instance_relative_config=True)

    # S'assure que le dossier instance existe (important pour SQLite)
    try:
        os.makedirs(app.instance_path, exist_ok=True)
    except Exception:
        pass

    # ---------- Config ----------
    # 1) Config objet (lit .env si prévu dans config.py)
    app.config.from_object("config.Config")

    # 2) Overrides ponctuels par ENV
    if "SECRET_KEY" in os.environ:
        app.config["SECRET_KEY"] = os.environ["SECRET_KEY"]
    if "DATABASE_URL" in os.environ:
        app.config["SQLALCHEMY_DATABASE_URI"] = os.environ["DATABASE_URL"]

    # Normalise l'URI DB
    app.config["SQLALCHEMY_DATABASE_URI"] = _normalize_database_uri(
        app.config.get("SQLALCHEMY_DATABASE_URI", "")
    )
    app.config["SQLALCHEMY_DATABASE_URI"] = _normalize_sqlite_uri(
        app, app.config.get("SQLALCHEMY_DATABASE_URI", "")
    )

    # Défauts utiles
    app.config.setdefault("SQLALCHEMY_TRACK_MODIFICATIONS", False)
    app.config.setdefault("PUBLIC_BASE_URL", "http://127.0.0.1:5000")
    app.config.setdefault("TEMPLATES_AUTO_RELOAD", True)

    # ---------- Heures supplémentaires : flags toujours présents ----------
    mode = (
        (os.environ.get("OVERTIME_MODE") or app.config.get("OVERTIME_MODE") or "manual")
        .strip()
        .lower()
    )
    allow_manual = app.config.get("OVERTIME_ALLOW_MANUAL")
    if allow_manual is None:
        allow_manual = _env_bool("OVERTIME_ALLOW_MANUAL", default=(mode != "auto"))
    auto = app.config.get("AUTO_OVERTIME")
    if auto is None:
        auto = (mode == "auto")

    app.config.update(
        OVERTIME_MODE=mode,
        OVERTIME_ALLOW_MANUAL=bool(allow_manual),
        AUTO_OVERTIME=bool(auto),
    )

    # Rendre la config dispo dans Jinja (utile pour AUTO_OVERTIME, etc.)
    app.jinja_env.globals.update(config=app.config)

    # ---------- Extensions ----------
    db.init_app(app)
    # importer les modèles pour que Migrate les voie
    from . import models  # noqa: F401
    migrate.init_app(app, db)

    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message_category = "warning"

    # ---------- Mail ----------
    if mail is not None:
        if not app.config.get("MAIL_BACKEND"):
            app.config["MAIL_BACKEND"] = "smtp" if app.config.get("MAIL_ENABLED") else "console"
        if app.config.get("SMTP_HOST"):
            app.config["MAIL_SERVER"] = app.config["SMTP_HOST"]
        if app.config.get("SMTP_PORT") is not None:
            app.config["MAIL_PORT"] = app.config["SMTP_PORT"]
        if app.config.get("SMTP_USER"):
            app.config["MAIL_USERNAME"] = app.config["SMTP_USER"]
        if app.config.get("SMTP_PASSWORD"):
            app.config["MAIL_PASSWORD"] = app.config["SMTP_PASSWORD"]
        app.config["MAIL_USE_TLS"] = app.config.get("SMTP_TLS", True)
        app.config["MAIL_USE_SSL"] = app.config.get("SMTP_SSL", False)
        app.config["MAIL_DEFAULT_SENDER"] = (
            app.config.get("MAIL_SENDER_NAME", "RH Platform"),
            app.config.get("MAIL_SENDER", "noreply@example.com"),
        )
        if app.config.get("MAIL_BACKEND") == "file":
            outbox = app.config.setdefault(
                "MAIL_FILE_PATH", os.path.join(app.instance_path, "mailoutbox")
            )
            os.makedirs(outbox, exist_ok=True)
        mail.init_app(app)
    else:
        app.logger.warning("Mail désactivé (Flask-Mailman non installé).")

    # ---------- Blueprints globaux ----------
    from .routes import register_blueprints
    register_blueprints(app)

    # Enregistre explicitement certaines routes SI elles n'existent pas déjà
    try:
        from .routes.qr_routes import qr_bp
        _safe_register(app, qr_bp)
    except Exception as e:
        app.logger.debug("QR routes non chargées: %s", e)

    try:
        from .routes.attendance_api import attendance_api
        _safe_register(app, attendance_api)
    except Exception as e:
        app.logger.debug("Attendance API non chargée: %s", e)

    # ---------- Helpers & filtres Jinja ----------
    def url_public(path: str) -> str:
        base = app.config["PUBLIC_BASE_URL"].rstrip("/")
        return f"{base}{path}"

    app.jinja_env.globals["url_public"] = url_public
    app.jinja_env.filters["fr_month_label"] = fr_month_label
    app.jinja_env.filters["fmt_hours"] = fmt_hours  # {{ 1.75|fmt_hours }} -> "1 h 45"

    # ---------- Jinja context (Role + Employé·e du mois + AUTO_OVERTIME) ----------
    from .models.enums import Role
    from .models.award import Award  # <-- utilise la table awards comme source unique

    @app.context_processor
    def inject_enums_and_config():
        eom_obj = None
        eom_name = None
        try:
            ym_today = date.today().strftime("%Y-%m")
            # 1) Mois courant, sinon dernier enregistrement
            award = (
                db.session.query(Award)
                .filter(Award.month == ym_today)
                .first()
            ) or (
                db.session.query(Award)
                .order_by(Award.month.desc())
                .first()
            )

            if award and getattr(award, "user", None):
                u = award.user
                name = (f"{(u.first_name or '').strip()} {(u.last_name or '').strip()}".strip()) or u.email
                dept = getattr(getattr(u, "department", None), "name", None)
                # Libellé période
                try:
                    y, m = map(int, (award.month or "").split("-"))
                    per_label = fr_month_label(date(y, m, 1))
                except Exception:
                    per_label = award.month or "—"

                eom_name = name
                eom_obj = {
                    "name": name,
                    "department": dept,
                    "period_label": per_label,
                    "period": award.month,
                    "note": "",           # Award n'a pas de note → champ laissé vide
                    "user_id": u.id,
                }
        except Exception as e:
            app.logger.debug("Context EOM non injecté: %s", e)
            eom_obj = None
            eom_name = None

        return {
            "Role": Role,
            "config": app.config,
            "AUTO_OVERTIME": app.config.get("AUTO_OVERTIME", False),
            "eom_name": eom_name,
            "employee_of_month": eom_obj,
        }

    # ---------- Scheduler (optionnel) ----------
    try:
        if app.config.get("SCHEDULER_ENABLED", False):
            from flask_pscheduler import APScheduler  # type: ignore
            scheduler = APScheduler()
            scheduler.init_app(app)
            try:
                from .jobs.overtime_jobs import nightly_recompute  # type: ignore
                hour = int(app.config.get("SCHEDULER_OT_RECOMPUTE_HOUR", 0))
                minute = int(app.config.get("SCHEDULER_OT_RECOMPUTE_MIN", 30))
                scheduler.add_job(
                    id="ot_nightly",
                    func=nightly_recompute,
                    trigger="cron",
                    hour=hour,
                    minute=minute,
                )
                scheduler.start()
                app.logger.info("APScheduler démarré (OT nightly %02d:%02d)", hour, minute)
            except Exception as e:
                app.logger.warning("Scheduler actif mais job OT non chargé: %s", e)
    except Exception as e:
        app.logger.debug("APScheduler indisponible: %s", e)

    # ---------- Logs utiles (DB + mail + OT mode) ----------
    safe_db_uri = app.config["SQLALCHEMY_DATABASE_URI"]
    if "@" in safe_db_uri:
        try:
            scheme, rest = safe_db_uri.split("://", 1)
            _, host = rest.split("@", 1)
            safe_db_uri = f"{scheme}://***:***@{host}"
        except Exception:
            pass

    app.logger.info("DB URI -> %s", safe_db_uri)
    app.logger.info(
        "MAIL -> backend=%s server=%s port=%s tls=%s ssl=%s sender=%s",
        app.config.get("MAIL_BACKEND"),
        app.config.get("MAIL_SERVER"),
        app.config.get("MAIL_PORT"),
        app.config.get("MAIL_USE_TLS"),
        app.config.get("MAIL_USE_SSL"),
        app.config.get("MAIL_DEFAULT_SENDER"),
    )
    app.logger.info(
        "OVERTIME -> mode=%s auto=%s allow_manual=%s",
        app.config.get("OVERTIME_MODE"),
        app.config.get("AUTO_OVERTIME"),
        app.config.get("OVERTIME_ALLOW_MANUAL"),
    )
    return app
