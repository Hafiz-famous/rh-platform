# app/routes/admin_users.py
from __future__ import annotations
from functools import wraps

from flask import Blueprint, render_template, request, abort, jsonify
from flask_login import login_required, current_user

from ..extensions import db
from ..models.user import User
from ..models.enums import Role

bp = Blueprint("admin_users", __name__, url_prefix="/admin/users")

# Si tu n'as pas déjà un décorateur global role_required
def role_required(*roles: Role):
    def deco(fn):
        @wraps(fn)
        @login_required
        def wrapper(*args, **kwargs):
            if not getattr(current_user, "has_role", None) or not current_user.has_role(*roles):
                abort(403)
            return fn(*args, **kwargs)
        return wrapper
    return deco

@bp.get("/")
@login_required
@role_required(Role.ADMIN, Role.MANAGER)
def list_users():
    q = (request.args.get("q") or "").strip().lower()
    users = db.session.query(User).order_by(User.id.asc()).all()
    if q:
        users = [u for u in users if q in u.email.lower() or q in f"{u.first_name} {u.last_name}".lower()]
    return render_template("admin/users.html", users=users, Role=Role)

@bp.post("/<int:user_id>/toggle")
@login_required
@role_required(Role.ADMIN, Role.MANAGER)
def toggle_user(user_id: int):
    u = db.session.get(User, user_id)
    if not u:
        abort(404)
    if u.id == current_user.id:
        return jsonify({"ok": False, "error": "Impossible de désactiver votre propre compte."}), 400
    u.is_active = not u.is_active
    db.session.commit()
    return jsonify({"ok": True, "is_active": u.is_active})

@bp.post("/<int:user_id>/role")
@login_required
@role_required(Role.ADMIN, Role.MANAGER)
def set_role(user_id: int):
    u = db.session.get(User, user_id)
    if not u:
        abort(404)
    new_role_name = (request.form.get("role") or "").upper()
    try:
        new_role = Role[new_role_name]
    except Exception:
        return jsonify({"ok": False, "error": "Rôle invalide"}), 400
    # Un MANAGER ne peut pas promouvoir en ADMIN
    if current_user.role == Role.MANAGER and new_role == Role.ADMIN:
        return jsonify({"ok": False, "error": "Droits insuffisants"}), 403
    u.role = new_role
    db.session.commit()
    return jsonify({"ok": True, "role": u.role.name})
