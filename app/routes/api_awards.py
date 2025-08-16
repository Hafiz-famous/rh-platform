
from datetime import date
from flask import Blueprint, jsonify, request
from flask_login import login_required
from ..services.award_service import compute_month_scores, get_weights
from ..models.award import Award

bp = Blueprint("api_awards", __name__, url_prefix="/api/awards")

@bp.get("/current")
@login_required
def current():
    ym = request.args.get("month") or date.today().strftime("%Y-%m")
    stored = Award.query.filter_by(month=ym).first()
    if stored:
        return jsonify({"month": ym, "user_id": stored.user_id, "score": float(stored.score)})
    scores = compute_month_scores(ym)
    if not scores:
        return jsonify({"month": ym, "user_id": None, "score": None})
    top = scores[0]
    return jsonify({"month": ym, "user_id": top.user_id, "score": float(top.score)})
