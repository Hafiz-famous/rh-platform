# app/routes/costs.py
from __future__ import annotations

from datetime import datetime
from flask import Blueprint, request, render_template, jsonify
from flask_login import login_required
from ..services.costs_service import summarize_month
from ..services.authz import roles_required
from ..models.enums import Role

bp = Blueprint("costs", __name__, url_prefix="/costs")

@bp.get("/")
@login_required
@roles_required(Role.ADMIN, Role.MANAGER)
def index():
    # Initial period = current month
    today = datetime.utcnow().date()
    return render_template("costs/index.html", year=today.year, month=today.month)

@bp.get("/api/summary")
@login_required
@roles_required(Role.ADMIN, Role.MANAGER)
def api_summary():
    period = request.args.get("period")  # YYYY-MM
    if not period:
        today = datetime.utcnow().date()
        y, m = today.year, today.month
    else:
        y, m = map(int, period.split("-"))
    data = summarize_month(y, m)
    return jsonify(data)
