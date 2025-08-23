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
# S'assure que le répertoire instance existe (utile pour SQLite)
INSTANCE_DIR.mkdir(exist_ok=True)

def _env_bool(name: str, default: bool = False) -> bool:
    v = os.environ.get(name)
    if v is None:
        return default
    return str(v).strip().lower() in ("1", "true", "t", "yes", "y", "on")

class Config:
    # --- Sécurité / Flask ---
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key")

    # --- Base de données ---
    # Priorité à DATABASE_URL ; sinon, SQLite dans instance/rh_platform.db
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        f"sqlite:///{(INSTANCE_DIR / 'rh_platform.db').as_posix()}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # (optionnel) petits conforts pour la stabilité des connexions
    # SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}

    # --- Emails (Flask-Mailman) ---
    # En dev: MAIL_BACKEND=console -> les mails s'affichent dans le terminal
    # En prod: passer à MAIL_BACKEND=smtp + renseigner serveur/identifiants
    MAIL_BACKEND = os.environ.get("MAIL_BACKEND", "console")  # "console" ou "smtp"
    MAIL_SERVER = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT = int(os.environ.get("MAIL_PORT", "587"))
    MAIL_USE_TLS = _env_bool("MAIL_USE_TLS", True)
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME")          # ex: ton_email@gmail.com
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")          # ex: app password
    MAIL_DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER", "no-reply@rh.local")

    # --- URLs externes (optionnel, utile si tu génères des liens absolus dans les mails) ---
    PUBLIC_BASE_URL = os.environ.get("PUBLIC_BASE_URL")      # ex: https://mon-app.com
    PREFERRED_URL_SCHEME = os.environ.get("PREFERRED_URL_SCHEME", "http")

    # --- Qualité de vie dev ---
    TEMPLATES_AUTO_RELOAD = _env_bool("TEMPLATES_AUTO_RELOAD", True)
    JSON_SORT_KEYS = False
