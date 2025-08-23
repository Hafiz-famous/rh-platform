from __future__ import annotations
from functools import wraps

from flask import (
    Blueprint, render_template, request, abort, jsonify,
    redirect, url_for, flash
)
from flask_login import login_required, current_user
from sqlalchemy.exc import IntegrityError

from ..extensions import db
from ..models.user import User
from ..models.enums import Role
from ..models.department import Department

bp = Blueprint("admin_users", __name__, url_prefix="/admin/users")

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
        users = [
            u for u in users
            if q in u.email.lower() or q in f"{u.first_name or ''} {u.last_name or ''}".lower()
        ]
    return render_template("admin/users.html", users=users, Role=Role)

@bp.route("/new", methods=["GET", "POST"])
@login_required
@role_required(Role.ADMIN, Role.MANAGER)
def new_user():
    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        first = (request.form.get("first_name") or "").strip()
        last = (request.form.get("last_name") or "").strip()
        role_name = (request.form.get("role") or "EMPLOYEE").upper()
        dept_id = request.form.get("department_id")
        hourly_rate = request.form.get("hourly_rate")
        password = request.form.get("password") or ""

        try:
            role = Role[role_name]
        except KeyError:
            flash("Rôle invalide.", "warning")
            return redirect(url_for("admin_users.new_user"))

        if not email or not password:
            flash("Email et mot de passe sont requis.", "warning")
            return redirect(url_for("admin_users.new_user"))

        if current_user.role == Role.MANAGER and role == Role.ADMIN:
            flash("Un manager ne peut pas créer un ADMIN.", "warning")
            return redirect(url_for("admin_users.new_user"))

        if db.session.execute(db.select(User).filter_by(email=email)).scalar_one_or_none():
            flash("Cet email existe déjà.", "warning")
            return redirect(url_for("admin_users.new_user"))

        u = User(
            email=email,
            first_name=first or None,
            last_name=last or None,
            role=role,
            is_active=True,
        )
        u.set_password(password)
        u.department_id = int(dept_id) if dept_id else None
        try:
            u.hourly_rate = float(hourly_rate) if hourly_rate not in (None, "",) else 0.0
        except ValueError:
            u.hourly_rate = 0.0

        db.session.add(u)
        db.session.commit()
        flash("Utilisateur créé.", "success")
        return redirect(url_for("admin_users.list_users"))

    depts = db.session.query(Department).order_by(Department.name).all()
    return render_template("admin/user_form.html", user=None, departments=depts, Role=Role)

@bp.route("/<int:user_id>/edit", methods=["GET", "POST"])
@login_required
@role_required(Role.ADMIN, Role.MANAGER)
def edit_user(user_id: int):
    u = db.session.get(User, user_id)
    if not u:
        abort(404)

    if request.method == "POST":
        first = (request.form.get("first_name") or "").strip()
        last = (request.form.get("last_name") or "").strip()
        role_name = (request.form.get("role") or u.role.name).upper()
        dept_id = request.form.get("department_id")
        hourly_rate = request.form.get("hourly_rate")
        password = request.form.get("password")  # optionnel

        try:
            new_role = Role[role_name]
        except KeyError:
            flash("Rôle invalide.", "warning")
            return redirect(url_for("admin_users.edit_user", user_id=user_id))

        if current_user.role == Role.MANAGER and new_role == Role.ADMIN:
            flash("Droits insuffisants pour promouvoir en ADMIN.", "warning")
            return redirect(url_for("admin_users.edit_user", user_id=user_id))

        u.first_name = first or None
        u.last_name = last or None
        u.role = new_role
        u.department_id = int(dept_id) if dept_id else None
        try:
            u.hourly_rate = float(hourly_rate) if hourly_rate not in (None, "",) else 0.0
        except ValueError:
            u.hourly_rate = 0.0

        if password:
            u.set_password(password)

        try:
            db.session.commit()
            flash("Utilisateur mis à jour.", "success")
        except IntegrityError:
            db.session.rollback()
            flash("Contrainte en base non respectée (email déjà utilisé ?).", "danger")

        return redirect(url_for("admin_users.list_users"))

    depts = db.session.query(Department).order_by(Department.name).all()
    return render_template("admin/user_form.html", user=u, departments=depts, Role=Role)

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
    if current_user.role == Role.MANAGER and new_role == Role.ADMIN:
        return jsonify({"ok": False, "error": "Droits insuffisants"}), 403
    u.role = new_role
    db.session.commit()
    return jsonify({"ok": True, "role": u.role.name})
