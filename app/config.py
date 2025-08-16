import os
from dotenv import load_dotenv

def load_config(app):
    load_dotenv()
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret")
    # Étape 1: on ne branche pas encore la base. (mais on expose la var pour la suite)
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///rh_platform.db")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["PUBLIC_BASE_URL"] = os.getenv("PUBLIC_BASE_URL", "http://127.0.0.1:5000")

