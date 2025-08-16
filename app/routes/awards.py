
from datetime import date
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required
from ..services.authz import roles_required
from ..models.enums import Role
from ..services.award_service import get_weights, set_weights, compute_month_scores, pick_winner
from ..models.award import Award

bp = Blueprint("awards", __name__, url_prefix="/admin/awards")

@bp.get("/")
@login_required
@roles_required(Role.ADMIN, Role.MANAGER)
def index():
    ym = request.args.get("month") or date.today().strftime("%Y-%m")
    weights = get_weights()
    scores = compute_month_scores(ym)
    winner = Award.query.filter_by(month=ym).first()
    return render_template("admin/awards.html", ym=ym, weights=weights, scores=scores, winner=winner)

@bp.post("/weights")
@login_required
@roles_required(Role.ADMIN, Role.MANAGER)
def save_weights():
    payload = request.form or request.json or {}
    w = {k: float(payload.get(k, 0)) for k in ("presence","hours","overtime","leaves")}
    set_weights(w)
    flash("Pondérations enregistrées.", "success")
    return redirect(url_for("awards.index", month=payload.get("month")))

@bp.post("/run")
@login_required
@roles_required(Role.ADMIN, Role.MANAGER)
def run_award():
    ym = request.form.get("month") or (request.json or {}).get("month")
    if not ym:
        return jsonify({"ok": False, "error": "Paramètre month requis (YYYY-MM)"}), 400
    a = pick_winner(ym)
    if not a:
        return jsonify({"ok": False, "error": "Aucune donnée pour ce mois"}), 400
    return jsonify({"ok": True, "winner_id": a.user_id, "month": a.month, "score": a.score})
