# app/routes/__init__.py
from __future__ import annotations
from flask import Flask


def register_blueprints(app: Flask) -> None:
    """
    Enregistre tous les blueprints disponibles.
    Les modules optionnels sont chargés en try/except pour éviter un crash si absents.
    """

    # --- Blueprints de base (attendus) ---
    from .auth import bp as auth_bp
    from .dashboard import bp as dashboard_bp
    from .attendance import bp as attendance_bp
    from .admin import bp as admin_bp
    from .api import bp as api_bp
    from .leaves import bp as leaves_bp
    from .overtime import bp as overtime_bp
    from .qr import bp as qr_bp
    from .awards import bp as awards_bp
    from .exports import bp as exports_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(attendance_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(leaves_bp)
    app.register_blueprint(overtime_bp)
    app.register_blueprint(qr_bp)
    app.register_blueprint(awards_bp)
    app.register_blueprint(exports_bp)

    # --- Blueprints additionnels/optionnels ---
    # Admin → gestion des utilisateurs (activer/désactiver, changer le rôle)
    try:
        from .admin_users import bp as admin_users_bp
        app.register_blueprint(admin_users_bp)
    except Exception as e:
        app.logger.debug("admin_users non enregistré: %s", e)

    # API awards (si séparée)
    try:
        from .api_awards import bp as api_awards_bp
        app.register_blueprint(api_awards_bp)
    except Exception as e:
        app.logger.debug("api_awards non enregistré: %s", e)

    # Workflow (approbations, audit) – sprint 8
    try:
        from .workflow import bp as workflow_bp
        app.register_blueprint(workflow_bp)
    except Exception as e:
        app.logger.debug("workflow non enregistré: %s", e)

    # Admin geofencing – sprint 8
    try:
        from .admin_geofence import bp as admin_geofence_bp
        app.register_blueprint(admin_geofence_bp)
    except Exception as e:
        app.logger.debug("admin_geofence non enregistré: %s", e)

    # Exports PDF (rapport) – optionnel
    try:
        from .exports_pdf import bp as exports_pdf_bp
        app.register_blueprint(exports_pdf_bp)
    except Exception as e:
        app.logger.debug("exports_pdf non enregistré: %s", e)
