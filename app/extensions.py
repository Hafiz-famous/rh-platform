# app/extensions.py
from __future__ import annotations

from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager

# Email (optionnel) : Flask-Mailman si disponible
try:
    from flask_mailman import Mail  # pip install Flask-Mailman
except Exception:
    Mail = None  # type: ignore

db = SQLAlchemy()
migrate = Migrate()

login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message_category = "warning"

# Instancie le mailer seulement si Flask-Mailman est présent
mail = Mail() if Mail else None
