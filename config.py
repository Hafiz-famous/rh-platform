# config.py
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()  # charge le fichier .env s'il existe
except Exception:
    # pas bloquant si python-dotenv n'est pas installé
    pass

BASE_DIR = Path(__file__).resolve().parent

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key")

    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        f"sqlite:///{BASE_DIR / 'app.db'}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Optionnel (utile si tu génères des URLs externes)
    PUBLIC_BASE_URL = os.environ.get("PUBLIC_BASE_URL")
