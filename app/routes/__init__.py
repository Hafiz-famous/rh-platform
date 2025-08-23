# app/routes/__init__.py
from __future__ import annotations
from flask import Flask
import importlib
import typing as t

def _register(app: Flask, module: str, *, required: bool) -> None:
    """
    Importe app.routes.<module>, récupère l'attribut `bp` et l'enregistre.
    - required=True  : lève l'exception si l'import/registration échoue
    - required=False : log en debug et continue
    """
    pkg = __package__ or "app.routes"  # "app.routes"
    mod_path = f"{pkg}.{module}"
    try:
        mod = importlib.import_module(mod_path)
        bp = getattr(mod, "bp", None)
        if bp is None:
            raise AttributeError(f"{mod_path} n'expose pas `bp`")
        app.register_blueprint(bp)
        app.logger.debug("Blueprint chargé: %s", mod_path)
    except Exception as e:
        msg = f"Blueprint non enregistré ({mod_path}): {e}"
        if required:
            app.logger.error(msg)
            raise
        else:
            app.logger.debug(msg)

def register_blueprints(app: Flask) -> None:
    """
    Enregistre tous les blueprints. Les “de base” sont requis,
    les autres sont optionnels.
    """
    # Requis (lève si manquant)
    required = [
        "auth",
        "dashboard",
        "attendance",
        "admin",
        "api",
        "leaves",
        "overtime",
        "qr",
        "awards",
        "exports",
    ]
    for m in required:
        _register(app, m, required=True)

    # Optionnels (ignore si absents)
    optional = [
        "admin_users",
        "api_awards",
        "workflow",        # sprint 8
        "admin_geofence",  # sprint 8
        "exports_pdf",
    ]
    for m in optional:
        _register(app, m, required=False)
