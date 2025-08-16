# app/routes/auth.py
from urllib.parse import urlparse

from flask import (
    Blueprint, render_template, request, redirect, url_for, flash, current_app
)
from flask_login import (
    login_user, logout_user, current_user, login_required
)

from ..extensions import db, login_manager
from ..models.user import User
# Si ton modèle a une Enum Role avec défaut EMPLOYEE, pas besoin de l'importer ici.

bp = Blueprint("auth", __name__, url_prefix="/auth")


# ---------- Flask-Login ----------
@login_manager.user_loader
def load_user(user_id: str):
    # Compatible SQLAlchemy 2.0
    try:
        return db.session.get(User, int(user_id))
    except Exception:
        return User.query.get(int(user_id))  # fallback 1.x


# ---------- Helpers ----------
def _safe_redirect_next(default_endpoint: str = "dashboard.index"):
    nxt = request.args.get("next") or request.form.get("next")
    # n'autorise que des chemins relatifs internes (ex: /leaves/)
    if nxt:
        p = urlparse(nxt)
        if not p.scheme and not p.netloc and nxt.startswith("/"):
            return redirect(nxt)
    return redirect(url_for(default_endpoint))


# ---------- Connexion ----------
@bp.get("/login")
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))
    return render_template("auth/login.html", next=request.args.get("next", ""))


@bp.post("/login")
def login_post():
    email = (request.form.get("email") or "").strip().lower()
    password = request.form.get("password") or ""
    remember = bool(request.form.get("remember"))

    user = db.session.query(User).filter_by(email=email).first()

    if not user or not user.check_password(password):
        flash("Identifiants invalides.", "danger")
        return redirect(url_for("auth.login", next=request.form.get("next", "")))

    # Vérifie l'état actif avant login
    if not user.is_active:
        flash("Compte désactivé. Contactez l'administrateur.", "warning")
        return redirect(url_for("auth.login"))

    login_user(user, remember=remember, fresh=True)
    return _safe_redirect_next()


# ---------- Déconnexion ----------
@bp.get("/logout")
@login_required
def logout():
    logout_user()
    flash("Vous êtes déconnecté.", "success")
    return redirect(url_for("auth.login"))


# ---------- Inscription (ouverte si REGISTER_OPEN=True) ----------
@bp.get("/register")
def register_form():
    if not current_app.config.get("REGISTER_OPEN", True):
        flash("Les inscriptions sont fermées. Contactez un administrateur.", "warning")
        return redirect(url_for("auth.login"))
    return render_template("auth/register.html")


@bp.post("/register")
def register_submit():
    if not current_app.config.get("REGISTER_OPEN", True):
        flash("Les inscriptions sont fermées.", "warning")
        return redirect(url_for("auth.login"))

    email = (request.form.get("email") or "").strip().lower()
    password = (request.form.get("password") or "").strip()
    first_name = (request.form.get("first_name") or "").strip()
    last_name = (request.form.get("last_name") or "").strip()

    if not all([email, password, first_name, last_name]):
        flash("Tous les champs sont obligatoires.", "danger")
        return redirect(url_for("auth.register_form"))

    # Unicité email
    if db.session.query(User).filter_by(email=email).first():
        flash("Cet email est déjà utilisé.", "danger")
        return redirect(url_for("auth.register_form"))

    # Rôle par défaut défini dans le modèle (EMPLOYEE)
    user = User(email=email, first_name=first_name, last_name=last_name)
    user.set_password(password)

    db.session.add(user)
    db.session.commit()

    flash("Compte créé avec succès. Vous pouvez vous connecter.", "success")
    return redirect(url_for("auth.login"))
