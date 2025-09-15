# app/routes/auth.py
from urllib.parse import urlparse
from datetime import timedelta

from flask import (
    Blueprint, render_template, request, redirect, url_for, flash, current_app
)
from flask_login import (
    login_user, logout_user, current_user, login_required
)

from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
import os, smtplib
from email.mime.text import MIMEText

from ..extensions import db, login_manager
from ..models.user import User
# Le modèle User doit exposer: .check_password(pwd) et .set_password(pwd)

bp = Blueprint("auth", __name__, url_prefix="/auth")

# ---------- Flask-Login ----------
@login_manager.user_loader
def load_user(user_id: str):
    # Compatible SQLAlchemy 2.0
    try:
        return db.session.get(User, int(user_id))
    except Exception:
        return User.query.get(int(user_id))  # fallback 1.x


# ---------- Helpers communs ----------
def _safe_redirect_next(default_endpoint: str = "dashboard.index"):
    nxt = request.args.get("next") or request.form.get("next")
    # n'autorise que des chemins relatifs internes (ex: /leaves/)
    if nxt:
        p = urlparse(nxt)
        if not p.scheme and not p.netloc and nxt.startswith("/"):
            return redirect(nxt)
    return redirect(url_for(default_endpoint))


def _serializer():
    """Génère un sérialiseur de jetons signé pour reset password."""
    secret = current_app.config["SECRET_KEY"]
    salt = current_app.config.get("SECURITY_PASSWORD_SALT", "pwd-reset")
    return URLSafeTimedSerializer(secret_key=secret, salt=salt)


def _reset_ttl_seconds() -> int:
    """Durée de validité du lien de réinitialisation (sec)."""
    return int(current_app.config.get("SECURITY_PASSWORD_RESET_EXPIRY", 3600))


def _send_mail(to_email: str, subject: str, body: str):
    """Envoie l'e-mail via SMTP si configuré, sinon affiche en console (DEV)."""
    host = os.getenv("SMTP_HOST")
    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.getenv("SMTP_USER")
    pwd  = os.getenv("SMTP_PASS")
    sender = os.getenv("SMTP_FROM", user or "no-reply@example.com")

    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = to_email

    if host and user and pwd:
        with smtplib.SMTP(host, port) as s:
            try:
                s.starttls()
            except smtplib.SMTPException:
                # si le serveur ne supporte pas STARTTLS, on tente en clair (DEV)
                pass
            if user and pwd:
                s.login(user, pwd)
            s.sendmail(sender, [to_email], msg.as_string())
    else:
        print(f"[DEV] Mail à {to_email} — {subject}\n{body}")


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
        # message neutre (évite l'énumération)
        flash("Identifiants invalides.", "danger")
        return redirect(url_for("auth.login", next=request.form.get("next", "")))

    # Vérifie l'état actif avant login
    if hasattr(user, "is_active") and not user.is_active:
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


# ---------- Mot de passe oublié ----------
@bp.route("/forgot", methods=["GET", "POST"])
def forgot():
    """Affiche le formulaire de demande et envoie un lien de reset si email trouvé.
    Ne révèle pas si l'email existe (message neutre)."""
    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()

        user = None
        if email:
            user = db.session.query(User).filter_by(email=email).first()

        if user:
            token = _serializer().dumps({"uid": user.id})
            reset_url = url_for("auth.reset", token=token, _external=True)
            body = (
                "Bonjour,\n\n"
                "Vous avez demandé la réinitialisation de votre mot de passe.\n"
                f"Cliquez sur le lien suivant (valide {int(_reset_ttl_seconds()/60)} min) :\n"
                f"{reset_url}\n\n"
                "Si vous n'êtes pas à l'origine de cette demande, ignorez ce message."
            )
            _send_mail(email, "Réinitialisation de votre mot de passe", body)

        flash("Si cet e-mail existe, un lien de réinitialisation a été envoyé.", "info")
        return redirect(url_for("auth.login"))

    return render_template("auth/forgot.html")


# ---------- Réinitialisation via jeton ----------
@bp.route("/reset/<token>", methods=["GET", "POST"])
def reset(token):
    """Valide le jeton, et permet de définir un nouveau mot de passe."""
    try:
        data = _serializer().loads(token, max_age=_reset_ttl_seconds())
        user = db.session.get(User, int(data["uid"]))
        if not user:
            raise BadSignature("user not found")
    except SignatureExpired:
        flash("Lien expiré. Merci de redemander un nouveau lien.", "danger")
        return redirect(url_for("auth.forgot"))
    except BadSignature:
        flash("Lien invalide. Merci de redemander un nouveau lien.", "danger")
        return redirect(url_for("auth.forgot"))

    if request.method == "POST":
        pwd1 = (request.form.get("password") or "")
        pwd2 = (request.form.get("password2") or "")

        if len(pwd1) < 8:
            flash("Le mot de passe doit contenir au moins 8 caractères.", "danger")
            return redirect(request.url)
        if pwd1 != pwd2:
            flash("Les deux mots de passe ne correspondent pas.", "danger")
            return redirect(request.url)

        user.set_password(pwd1)
        db.session.commit()
        flash("Mot de passe mis à jour. Vous pouvez vous connecter.", "success")
        return redirect(url_for("auth.login"))

    # GET: affiche le formulaire
    return render_template("auth/reset.html", token=token)
