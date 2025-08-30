# app/routes/dashboard.py
from datetime import date
from flask import Blueprint, render_template
from flask_login import login_required
from sqlalchemy import func

from ..extensions import db
from ..models.user import User
from ..models.department import Department
from ..models.attendance import Attendance

bp = Blueprint("dashboard", __name__, url_prefix="/")


def _build_employee_of_month(today):
    """Retourne un dict normalisé pour l'employé·e du mois, ou None."""
    # 1) Service (si présent)
    try:
        from ..services.awards_service import get_employee_of_month  # adapte si ton nom diffère
        eom = get_employee_of_month(today.year, today.month)
        if not eom:
            return None

        if isinstance(eom, dict):
            return {
                "user_id": eom.get("user_id"),
                "name": eom.get("name"),
                "department": eom.get("department", "—"),
                "period_label": eom.get("period_label") or today.strftime("%B %Y"),
            }

        # Objet: on tente d'en extraire user/department
        try:
            u = getattr(eom, "user", None)
            if u:
                name = (
                    f"{(u.first_name or '').strip()} {(u.last_name or '').strip()}".strip()
                    or u.email.split("@")[0]
                )
                dept_name = getattr(getattr(u, "department", None), "name", None) or "—"
                return {
                    "user_id": getattr(u, "id", None),
                    "name": name,
                    "department": dept_name,
                    "period_label": getattr(eom, "period_label", None) or today.strftime("%B %Y"),
                }
        except Exception:
            pass
    except Exception:
        pass

    # 2) Fallback: modèle en base (si présent)
    try:
        from ..models.awards import EmployeeOfMonth  # adapte si besoin
    except Exception:
        return None

    row = (
        db.session.query(EmployeeOfMonth)
        .filter_by(year=today.year, month=today.month)
        .first()
    )
    if not row:
        return None

    u = db.session.get(User, row.user_id)
    if not u:
        return None

    # Récup nom département
    dept_name = None
    try:
        dept_name = getattr(getattr(u, "department", None), "name", None)
        if not dept_name and getattr(u, "department_id", None):
            dept_name = (
                db.session.query(Department.name)
                .filter(Department.id == u.department_id)
                .scalar()
            )
    except Exception:
        dept_name = None

    name = (
        f"{(u.first_name or '').strip()} {(u.last_name or '').strip()}".strip()
        or u.email.split("@")[0]
    )
    return {
        "user_id": u.id,
        "name": name,
        "department": dept_name or "—",
        "period_label": today.strftime("%B %Y"),
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

    # Employé·e du mois FRAIS (pas de cache)
    employee_of_month = _build_employee_of_month(today)

    return render_template(
        "dashboard/index.html",
        stats=stats,
        today=today,
        employee_of_month=employee_of_month,
    )
