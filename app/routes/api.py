# app/routes/api.py
from __future__ import annotations

from datetime import date, timedelta
from flask import Blueprint, jsonify, request, current_app
from flask_login import login_required
from sqlalchemy import func, distinct

from ..extensions import db
from ..models.attendance import Attendance
from ..models.overtime import Overtime
from ..models.leave import Leave
from ..models.user import User
from ..models.department import Department  # si présent
from ..models.enums import LeaveStatus, RequestStatus, Role
from ..services.cost_service import department_costs
from ..services.authz import roles_required

bp = Blueprint("api", __name__, url_prefix="/api")


# ---------- KPIs du tableau de bord ----------
@bp.get("/dashboard/stats")
@login_required
def dashboard_stats():
    """KPIs principaux du dashboard (jour courant)."""
    today = date.today()

    present = (
        db.session.query(func.count(distinct(Attendance.user_id)))
        .filter(Attendance.work_date == today, Attendance.check_in.isnot(None))
        .scalar()
        or 0
    )

    hours = (
        db.session.query(func.coalesce(func.sum(Attendance.total_hours), 0.0))
        .filter(Attendance.work_date == today)
        .scalar()
        or 0.0
    )

    # ✅ Leave.status -> LeaveStatus.*
    leaves_pending = (
        db.session.query(func.count(Leave.id))
        .filter(Leave.status == LeaveStatus.PENDING)
        .scalar()
        or 0
    )

    # ✅ Overtime.status -> RequestStatus.*
    ot_pending = (
        db.session.query(func.count(Overtime.id))
        .filter(Overtime.status == RequestStatus.PENDING)
        .scalar()
        or 0
    )

    return jsonify({
        "date": str(today),
        "present": int(present),
        "hours": float(hours),
        "leaves_pending": int(leaves_pending),
        "ot_pending": int(ot_pending),
    })


# ---------- Graphique : présence ----------
@bp.get("/charts/presence")
@login_required
def chart_presence():
    """Série J-13..J : nb de personnes distinctes ayant fait un check-in par jour."""
    try:
        days = max(1, int(request.args.get("days", 14)))
    except ValueError:
        days = 14

    end = date.today()
    start = end - timedelta(days=days - 1)

    labels, values = [], []
    for i in range(days):
        d = start + timedelta(days=i)
        labels.append(d.strftime("%d/%m"))
        c = (
            db.session.query(func.count(distinct(Attendance.user_id)))
            .filter(Attendance.work_date == d, Attendance.check_in.isnot(None))
            .scalar()
            or 0
        )
        values.append(int(c))

    return jsonify({"labels": labels, "values": values})


# ---------- Graphique : heures sup approuvées ----------
@bp.get("/charts/overtime")
@login_required
def chart_overtime():
    try:
        days = max(1, int(request.args.get("days", 14)))
    except ValueError:
        days = 14

    end = date.today()
    start = end - timedelta(days=days - 1)

    labels, values = [], []
    for i in range(days):
        d = start + timedelta(days=i)
        labels.append(d.strftime("%d/%m"))
        s = (
            db.session.query(func.coalesce(func.sum(Overtime.hours), 0.0))
            .filter(Overtime.work_date == d, Overtime.status == RequestStatus.APPROVED)
            .scalar()
            or 0.0
        )
        values.append(float(s))

    return jsonify({"labels": labels, "values": values})


# ---------- Graphique : coûts par département ----------
@bp.get("/charts/department-costs")
@login_required
def chart_dept_costs():
    """
    Retourne une LISTE d'objets: [{ "department": "...", "cost": 123.45 }, ...]
    Paramètre: ?ym=YYYY-MM (ou ?month=YYYY-MM). Défaut = mois courant.
    """
    ym = request.args.get("ym") or request.args.get("month")
    if not ym:
        t = date.today()
        ym = f"{t.year:04d}-{t.month:02d}"

    try:
        data = department_costs(ym)
        return jsonify(data)
    except Exception:
        current_app.logger.exception("department-costs failed for %s", ym)
        return jsonify([]), 200  # ne casse pas le dashboard


# ---------- Présents 'maintenant' (Admin & Manager) ----------
@bp.get("/present-today")
@login_required
@roles_required(Role.ADMIN, Role.MANAGER)   # mets seulement Role.MANAGER si tu veux restreindre
def present_today():
    """
    Liste des personnes 'présentes maintenant':
    - check_in aujourd'hui AND check_out IS NULL
    Sortie: {"count": N, "items": [...]}
    """
    q = (
        db.session.query(
            User.id.label("user_id"),
            User.first_name,
            User.last_name,
            User.email,
            Department.name.label("department"),
            Attendance.check_in,
            Attendance.source,
        )
        .join(Attendance, Attendance.user_id == User.id)
        .outerjoin(Department, Department.id == User.department_id)
        .filter(Attendance.work_date == date.today())
        .filter(Attendance.check_in.isnot(None))
        .filter(Attendance.check_out.is_(None))
        .order_by(Attendance.check_in.desc())
    )

    rows = q.all()
    items = [
        {
            "user_id": r.user_id,
            "name": (f"{(r.first_name or '').strip()} {(r.last_name or '').strip()}".strip()
                     or r.email.split("@")[0]),
            "email": r.email,
            "department": r.department or "—",
            "check_in": r.check_in.isoformat() if r.check_in else None,
            "source": r.source or "manual",
        }
        for r in rows
    ]
    return jsonify({"count": len(items), "items": items})


# ---------- No-cache pour l'API ----------
@bp.after_request
def _no_cache(resp):
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    resp.headers["Pragma"] = "no-cache"
    resp.headers["Expires"] = "0"
    return resp
