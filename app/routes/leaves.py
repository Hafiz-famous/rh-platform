from datetime import datetime
from flask import Blueprint, jsonify, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user

from ..models.leave import Leave
from ..models.enums import LeaveType, LeaveStatus, Role
from ..services.leave_service import request_leave, update_status
from ..services.authz import roles_required  # décorateur d'autorisation

bp = Blueprint("leaves", __name__, url_prefix="/leaves")


@bp.get("/")
@login_required
def index():
    """Liste des congés du user connecté."""
    items = (
        Leave.query
        .filter(Leave.user_id == current_user.id)
        .order_by(Leave.created_at.desc())
        .all()
    )
    return render_template("leaves/index.html", items=items)


@bp.post("/")
@login_required
def create():
    """Création d'une demande de congé par l'employé."""
    form = request.form or request.json or {}

    # type de congé (tolère 'annual' ou 'ANNUAL')
    lv_type_raw = (form.get("type") or "annual").strip()
    try:
        try:
            lv_type = LeaveType[lv_type_raw.upper()]
        except KeyError:
            lv_type = LeaveType(lv_type_raw.lower())
    except Exception:
        flash("Type de congé invalide.", "danger")
        return redirect(url_for("leaves.index"))

    try:
        start_date = datetime.fromisoformat(form["start_date"]).date()
        end_date = datetime.fromisoformat(form["end_date"]).date()
    except Exception:
        flash("Dates invalides (format attendu YYYY-MM-DD).", "danger")
        return redirect(url_for("leaves.index"))

    try:
        _lv = request_leave(
            user_id=current_user.id,
            lv_type=lv_type,
            start_date=start_date,
            end_date=end_date,
            reason=form.get("reason"),
        )
        flash("Demande de congé envoyée.", "success")
    except Exception as e:
        flash(f"Erreur: {e}", "danger")

    return redirect(url_for("leaves.index"))


@bp.get("/pending")
@login_required
@roles_required(Role.MANAGER)   # <-- MANAGER uniquement
def pending():
    """File d'attente des congés à valider (MANAGER uniquement)."""
    items = (
        Leave.query
        .filter(Leave.status == LeaveStatus.PENDING)
        .order_by(Leave.created_at.desc())
        .all()
    )
    return render_template("leaves/pending.html", items=items)


@bp.post("/<int:leave_id>/status")
@login_required
@roles_required(Role.MANAGER)   # <-- MANAGER uniquement
def set_status(leave_id: int):
    """Validation / refus d'un congé (MANAGER uniquement)."""
    payload = request.form or (request.json or {})
    st_raw = (payload.get("status") or "").strip()
    if not st_raw:
        return jsonify({"ok": False, "error": "status manquant"}), 400

    # Tolère 'approved' / 'APPROVED'
    try:
        try:
            status = LeaveStatus[st_raw.upper()]
        except KeyError:
            status = LeaveStatus(st_raw.lower())
    except Exception:
        return jsonify({"ok": False, "error": "status invalide"}), 400

    try:
        lv = update_status(leave_id, status)
        return jsonify({"ok": True, "status": lv.status.value})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 400
