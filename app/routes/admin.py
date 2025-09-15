from __future__ import annotations

from flask import Blueprint, render_template, current_app
from flask_login import login_required

from ..models.enums import Role
from ..services.authz import roles_required
from ..models.user import User

bp = Blueprint("admin", __name__, url_prefix="/admin")


@bp.get("/")
@login_required
@roles_required(Role.ADMIN)
def admin_home():
    """
    Page d'accueil Admin.
    - Renvoie les 20 derniers utilisateurs (pour un aperçu rapide).
    - Passe `endpoints` au template pour afficher uniquement
      les raccourcis dont les routes existent vraiment.
    """
    users = (
        User.query
        .order_by(User.created_at.desc())
        .limit(20)
        .all()
    )

    endpoints = set(current_app.view_functions.keys())
    return render_template("admin/index.html", users=users, endpoints=endpoints)
