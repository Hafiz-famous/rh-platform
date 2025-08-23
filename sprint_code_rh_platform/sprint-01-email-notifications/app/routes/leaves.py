# app/routes/leaves.py (remplacement complet suggéré)
from __future__ import annotations
from datetime import datetime
from flask import Blueprint, jsonify, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from ..models.leave import Leave
from ..models.enums import LeaveType, LeaveStatus, Role
from ..services.leave_service import request_leave, update_status
from ..services.authz import roles_required

bp = Blueprint("leaves", __name__, url_prefix="/leaves")

@bp.get("/")
@login_required
def index():
    items = (Leave.query
            .filter(Leave.user_id == current_user.id)
            .order_by(Leave.created_at.desc())
            .all())
    return render_template("leaves/index.html", items=items)

@bp.post("/")
@login_required
def create():
    form = request.form or request.json or {}
    try:
        lv = request_leave(
            user_id=current_user.id,
            lv_type=form.get("type", "annual"),
            start_date=datetime.fromisoformat(form["start_date"]).date(),
            end_date=datetime.fromisoformat(form["end_date"]).date(),
            reason=form.get("reason"),
        )
        flash("Demande de congé envoyée.", "success")
        return redirect(url_for("leaves.index"))
    except Exception as e:
        flash(f"Erreur: {e}", "danger")
        return redirect(url_for("leaves.index"))

@bp.get("/pending")
@login_required
@roles_required(Role.ADMIN, Role.MANAGER)
def pending():
    items = (Leave.query
             .filter(Leave.status == LeaveStatus.PENDING)
             .order_by(Leave.created_at.desc())
             .all())
    return render_template("leaves/pending.html", items=items)

@bp.post("/<int:leave_id>/status")
@login_required
@roles_required(Role.ADMIN, Role.MANAGER)
def set_status(leave_id):
    st = request.form.get("status") or (request.json or {}).get("status")
    lv = update_status(leave_id, st, actor_user_id=current_user.id)
    return jsonify({"ok": True, "status": getattr(lv.status, "value", str(lv.status))})
