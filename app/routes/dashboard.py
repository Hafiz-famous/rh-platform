# app/routes/dashboard.py
from __future__ import annotations

from datetime import date
from flask import Blueprint, render_template
from flask_login import login_required
from sqlalchemy import func
from sqlalchemy.orm import joinedload

from ..extensions import db
from ..models.user import User
from ..models.department import Department
from ..models.attendance import Attendance
from ..models.award import Award  # <-- IMPORTANT : ton modèle Award (awards)

bp = Blueprint("dashboard", __name__, url_prefix="/")


def _fr_period_label(d: date) -> str:
    # Libellé "Septembre 2025" sans dépendre du locale système
    mois = [
        "janvier","février","mars","avril","mai","juin",
        "juillet","août","septembre","octobre","novembre","décembre"
    ]
    return f"{mois[d.month - 1].capitalize()} {d.year}"


def _display_name(u: User) -> str:
    fn = (getattr(u, "first_name", "") or "").strip()
    ln = (getattr(u, "last_name", "") or "").strip()
    full = (f"{fn} {ln}".strip())
    if full:
        return full
    # fallback sur la partie locale de l'email
    try:
        return u.email.split("@")[0]
    except Exception:
        return getattr(u, "email", "").strip() or "—"


def _build_employee_of_month(today: date) -> dict | None:
    """Retourne un dict normalisé pour l'employé·e du mois, ou None."""
    ym = today.strftime("%Y-%m")
    award = (
        db.session.query(Award)
        .options(joinedload(Award.user).joinedload(User.department))
        .filter(Award.month == ym)
        .first()
    )
    if not award or not award.user:
        return None

    u = award.user
    dept_name = getattr(getattr(u, "department", None), "name", None) or "—"

    return {
        "user_id": getattr(u, "id", None),
        "name": _display_name(u),
        "department": dept_name,
        "period_label": _fr_period_label(today),
        "score": getattr(award, "score", None),
    }


@bp.get("/")
@login_required
def index():
    today = date.today()

    # Stats rapides
    total_users = db.session.query(func.count(User.id)).scalar() or 0
    total_departments = db.session.query(func.count(Department.id)).scalar() or 0
    todays_att = (
        db.session.query(func.count(Attendance.id))
        .filter(Attendance.work_date == today)
        .scalar()
        or 0
    )
    stats = dict(users=total_users, depts=total_departments, today=todays_att)

    # Employé·e du mois: table awards comme source unique
    employee_of_month = _build_employee_of_month(today)

    return render_template(
        "dashboard/index.html",
        stats=stats,
        today=today,
        employee_of_month=employee_of_month,
    )
