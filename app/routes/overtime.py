
from datetime import datetime
from flask import Blueprint, jsonify, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from ..models.overtime import Overtime
from ..models.enums import RequestStatus, Role
from ..services.overtime_service import declare_overtime, set_status
from ..services.authz import roles_required

bp = Blueprint("overtime", __name__, url_prefix="/overtime")

@bp.get("/")
@login_required
def index():
    items = (Overtime.query
             .filter(Overtime.user_id == current_user.id)
             .order_by(Overtime.created_at.desc())
             .all())
    return render_template("overtime/index.html", items=items)

@bp.post("/")
@login_required
def create():
    form = request.form or request.json or {}
    try:
        ot = declare_overtime(
            user_id=current_user.id,
            work_date=datetime.fromisoformat(form["work_date"]).date(),
            hours=float(form["hours"]),
            note=form.get("note"))
        flash("Heures supplémentaires déclarées.", "success")
        return redirect(url_for("overtime.index"))
    except Exception as e:
        flash(f"Erreur: {e}", "danger")
        return redirect(url_for("overtime.index"))

@bp.get("/pending")
@login_required
@roles_required(Role.ADMIN, Role.MANAGER)
def pending():
    items = (Overtime.query
             .filter(Overtime.status == RequestStatus.PENDING)
             .order_by(Overtime.created_at.desc())
             .all())
    return render_template("overtime/pending.html", items=items)

@bp.post("/<int:ot_id>/status")
@login_required
@roles_required(Role.ADMIN, Role.MANAGER)
def status_ot(ot_id):
    st = request.form.get("status") or (request.json or {}).get("status")
    ot = set_status(ot_id, RequestStatus(st))
    return jsonify({"ok": True, "status": ot.status.value})
