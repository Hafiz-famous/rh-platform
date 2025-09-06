# config.py
import os
from pathlib import Path

# Charge .env s'il existe (facultatif)
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

BASE_DIR = Path(__file__).resolve().parent
INSTANCE_DIR = BASE_DIR / "instance"
INSTANCE_DIR.mkdir(exist_ok=True)  # utile pour SQLite

# ----------------------- Helpers ENV -----------------------
def _env_bool(name: str, default: bool = False) -> bool:
    v = os.environ.get(name)
    if v is None:
        return default
    return str(v).strip().lower() in {"1", "true", "t", "yes", "y", "on"}

def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except Exception:
        return default

def _env_float(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, default))
    except Exception:
        return default

def _database_url(default_sqlite_path: Path) -> str:
    # Corrige l'URL Heroku style "postgres://"
    url = os.environ.get("DATABASE_URL")
    if not url:
        return f"sqlite:///{default_sqlite_path.as_posix()}"
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return url


class Config:
    # --- Sécurité / Flask ---
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key")
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "dev-jwt-secret")

    # --- Base de données ---
    SQLALCHEMY_DATABASE_URI = _database_url(INSTANCE_DIR / "rh_platform.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}  # optionnel

    # --- CORS (si front séparé) ---
    CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "*")  # ex: "http://localhost:5173"

    # --- Emails (Flask-Mailman) ---
    MAIL_BACKEND = os.environ.get("MAIL_BACKEND", "console")  # "console" ou "smtp"
    MAIL_SERVER = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT = _env_int("MAIL_PORT", 587)
    MAIL_USE_TLS = _env_bool("MAIL_USE_TLS", True)
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME")          # ex: ton_email@gmail.com
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")          # ex: app password
    MAIL_DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER", "no-reply@rh.local")

    # --- URLs externes (utile pour liens absolus dans mails) ---
    PUBLIC_BASE_URL = os.environ.get("PUBLIC_BASE_URL")      # ex: https://mon-app.com
    PREFERRED_URL_SCHEME = os.environ.get("PREFERRED_URL_SCHEME", "http")

    # --- Qualité de vie dev ---
    TEMPLATES_AUTO_RELOAD = _env_bool("TEMPLATES_AUTO_RELOAD", True)
    JSON_SORT_KEYS = False

    # ---------------------------------------------------------------------
    #  HEURES SUPPLÉMENTAIRES : PILOTAGE DU COMPORTEMENT
    # ---------------------------------------------------------------------
    # "manual" : déclaration employé + validation
    # "auto"   : calcul automatique depuis les pointages (formulaire masqué côté UI)
    # "hybrid" : auto par défaut + possibilité de correction manuelle (soumise à validation)
    OVERTIME_MODE = (os.environ.get("OVERTIME_MODE", "manual") or "manual").strip().lower()
    # Compat UI : flag simple pour masquer le formulaire si 100% auto
    AUTO_OVERTIME = OVERTIME_MODE == "auto"

    # Autoriser la soumission manuelle ? (désactivée si AUTO strict)
    OVERTIME_ALLOW_MANUAL = _env_bool("OVERTIME_ALLOW_MANUAL", OVERTIME_MODE != "auto")

    # Auto-valider les heures sup calculées ? (sinon PENDING)
    OVERTIME_AUTO_APPROVE = _env_bool("OVERTIME_AUTO_APPROVE", False)

    # Politique d’heures supp (valeurs par défaut si pas de planning individuel)
    DEFAULT_DAILY_MINUTES   = _env_int("DEFAULT_DAILY_MINUTES", 480)  # 8h net/jour
    SHIFT_START_HOUR        = _env_int("SHIFT_START_HOUR", 8)
    SHIFT_START_MINUTE      = _env_int("SHIFT_START_MINUTE", 0)
    OVERTIME_GRACE_MINUTES  = _env_int("OVERTIME_GRACE_MINUTES", 10)  # tolérance
    OVERTIME_ROUND_STEP     = _env_int("OVERTIME_ROUND_STEP", 15)      # arrondi (min)
    OVERTIME_DAILY_CAP      = _env_int("OVERTIME_DAILY_CAP", 180)      # plafond/jour (min)
    OVERTIME_WEEKLY_BASE    = _env_int("OVERTIME_WEEKLY_BASE", 2400)   # 40h
    OVERTIME_COUNT_WEEKENDS_AS_OT = _env_bool("OVERTIME_COUNT_WEEKENDS_AS_OT", True)
    OVERTIME_COUNT_HOLIDAYS_AS_OT = _env_bool("OVERTIME_COUNT_HOLIDAYS_AS_OT", True)

    # Timezone applicative
    APP_TIMEZONE = os.environ.get("APP_TIMEZONE", "UTC")

    # Inscriptions ouvertes (ex: pour tests/démo)
    ALLOW_OPEN_REGISTRATION = _env_bool("ALLOW_OPEN_REGISTRATION", True)

    # ---------------------------------------------------------------------
    #  GÉOREPÉRAGE POINTAGE (site principal)
    # ---------------------------------------------------------------------
    ATTENDANCE_SITE_NAME      = os.environ.get("ATTENDANCE_SITE_NAME", "ESGIS Avédji")
    ATTENDANCE_SITE_LAT       = _env_float("ATTENDANCE_SITE_LAT", 6.1727)
    ATTENDANCE_SITE_LON       = _env_float("ATTENDANCE_SITE_LON", 1.2124)
    ATTENDANCE_SITE_RADIUS_M  = _env_int("ATTENDANCE_SITE_RADIUS_M", 50)  # mètres
    ATTENDANCE_RESTRICT_TO_SITE = _env_bool("ATTENDANCE_RESTRICT_TO_SITE", False)

    # ---------------------------------------------------------------------
    #  SCHEDULER (recalcul nocturne des heures sup auto)
    # ---------------------------------------------------------------------
    SCHEDULER_ENABLED = _env_bool("SCHEDULER_ENABLED", True)
    SCHEDULER_OT_RECOMPUTE_HOUR = _env_int("SCHEDULER_OT_RECOMPUTE_HOUR", 0)    # 00h30 par défaut...
    SCHEDULER_OT_RECOMPUTE_MIN  = _env_int("SCHEDULER_OT_RECOMPUTE_MIN", 30)    # ...si tu utilises APScheduler
