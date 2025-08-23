# app/routes/api.py
from __future__ import annotations
from datetime import date, timedelta
from flask import Blueprint, jsonify, request, current_app
from flask_login import login_required
from sqlalchemy import func, distinct

from ..extensions import db
from ..models.attendance import Attendance
from ..models.overtime import Overtime
from ..models.enums import RequestStatus
from ..services.cost_service import department_costs

bp = Blueprint("api", __name__, url_prefix="/api")

@bp.get("/dashboard/stats")
@login_required
def dashboard_stats():
    today = date.today()
    present = db.session.query(
        func.count(distinct(Attendance.user_id))
    ).filter(
        Attendance.work_date == today,
        Attendance.check_in.isnot(None)
    ).scalar() or 0
    hours = db.session.query(
        func.sum(Attendance.total_hours)
    ).filter(
        Attendance.work_date == today
    ).scalar() or 0.0
    return jsonify({"date": str(today), "present": int(present), "hours": float(hours)})

@bp.get("/charts/presence")
@login_required
def chart_presence():
    days = int(request.args.get("days", 14))
    end = date.today()
    start = end - timedelta(days=days - 1)
    labels, values = [], []
    for i in range(days):
        d = start + timedelta(days=i)
        labels.append(d.strftime("%d/%m"))
        c = db.session.query(
            func.count(distinct(Attendance.user_id))
        ).filter(
            Attendance.work_date == d,
            Attendance.check_in.isnot(None)
        ).scalar() or 0
        values.append(int(c))
    return jsonify({"labels": labels, "values": values})

@bp.get("/charts/overtime")
@login_required
def chart_overtime():
    days = int(request.args.get("days", 14))
    end = date.today()
    start = end - timedelta(days=days - 1)
    labels, values = [], []
    for i in range(days):
        d = start + timedelta(days=i)
        labels.append(d.strftime("%d/%m"))
        s = db.session.query(
            func.sum(Overtime.hours)
        ).filter(
            Overtime.work_date == d,
            Overtime.status == RequestStatus.APPROVED
        ).scalar() or 0.0
        values.append(float(s))
    return jsonify({"labels": labels, "values": values})

@bp.get("/charts/department-costs")
@login_required
def chart_dept_costs():
    # accepte ?ym=YYYY-MM ou ?month=YYYY-MM ; défaut = mois courant
    ym = request.args.get("ym") or request.args.get("month")
    if not ym:
        t = date.today()
        ym = f"{t.year:04d}-{t.month:02d}"

    try:
        data = department_costs(ym)  # -> [{department, cost}, ...]
        return jsonify(data)         # << renvoie une LISTE d’objets
    except Exception:
        current_app.logger.exception("department-costs failed for %s", ym)
        # pour ne pas casser le dashboard si une erreur survient :
        return jsonify([]), 200
