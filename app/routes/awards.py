from __future__ import annotations

import re
from datetime import date
from typing import Dict, Any

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required

from ..extensions import db
from ..services.authz import roles_required
from ..models.enums import Role
from ..services.award_service import (
    get_weights,
    set_weights,
    compute_month_scores,
    pick_winner,  # doit retourner/ créer un Award
)
from ..models.award import Award

bp = Blueprint("awards", __name__, url_prefix="/admin/awards")

_MONTH_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


def _get_month_from_request() -> str:
    """Récupère un 'YYYY-MM' depuis query/form/json, avec fallback mois courant."""
    ym = (
        request.args.get("month")
        or request.form.get("month")
        or (request.json or {}).get("month")
        or date.today().strftime("%Y-%m")
    )
    # Validation légère YYYY-MM
    if not _MONTH_RE.match(ym):
        # fallback sûr
        ym = date.today().strftime("%Y-%m")
    return ym


def _wants_json() -> bool:
    ct = (request.headers.get("Accept") or "").lower()
    return "application/json" in ct or request.is_json


@bp.get("/")
@login_required
@roles_required(Role.ADMIN, Role.MANAGER)
def index():
    ym = _get_month_from_request()
    weights = get_weights()  # dict: presence/hours/overtime/leaves
    scores = compute_month_scores(ym)  # tableau de scores par user pour ym
    winner = Award.query.filter_by(month=ym).first()
    return render_template(
        "admin/awards.html",
        ym=ym,
        weights=weights,
        scores=scores,
        winner=winner,
    )


@bp.post("/weights")
@login_required
@roles_required(Role.ADMIN, Role.MANAGER)
def save_weights():
    payload: Dict[str, Any] = request.form or (request.json or {})
    ym = payload.get("month") or _get_month_from_request()

    # Coerce -> float avec défaut 0.0
    def fget(k: str) -> float:
        try:
            return float(payload.get(k, 0) or 0)
        except Exception:
            return 0.0

    w = {
        "presence": fget("presence"),
        "hours": fget("hours"),
        "overtime": fget("overtime"),
        "leaves": fget("leaves"),
    }
    set_weights(w)

    if _wants_json():
        return jsonify({"ok": True, "weights": w, "month": ym})

    flash("Pondérations enregistrées.", "success")
    return redirect(url_for("awards.index", month=ym))


@bp.post("/run")
@login_required
@roles_required(Role.ADMIN, Role.MANAGER)
def run_award():
    ym = _get_month_from_request()
    a = pick_winner(ym)  # => Award ou None (crée/maj le gagnant pour ym)

    if not a:
        msg = "Aucune donnée suffisante pour ce mois."
        if _wants_json():
            return jsonify({"ok": False, "error": msg}), 400
        flash(msg, "warning")
        return redirect(url_for("awards.index", month=ym))

    if _wants_json():
        return jsonify(
            {"ok": True, "winner_id": a.user_id, "month": a.month, "score": float(a.score)}
        )

    flash("Gagnant enregistré.", "success")
    return redirect(url_for("awards.index", month=ym))


@bp.post("/set")
@login_required
@roles_required(Role.ADMIN, Role.MANAGER)
def set_winner_manual():
    """
    Désigne/édite manuellement le gagnant du mois (et métadonnées).
    Accepte form HTML ou JSON :
      - month: 'YYYY-MM'
      - user_id: int
      - title, department, citation, photo_url (optionnels)
      - score (optionnel)
    """
    payload: Dict[str, Any] = request.form or (request.json or {})
    ym = payload.get("month") or _get_month_from_request()

    try:
        user_id = int(payload.get("user_id"))
    except Exception:
        msg = "Paramètre 'user_id' requis."
        if _wants_json():
            return jsonify({"ok": False, "error": msg}), 400
        flash(msg, "danger")
        return redirect(url_for("awards.index", month=ym))

    score = 0.0
    try:
        score = float(payload.get("score", 0) or 0)
    except Exception:
        pass

    # upsert gagnant
    aw = Award.upsert(
        ym=ym,
        user_id=user_id,
        score=score,
        details=None,
    )

    # métadonnées de présentation
    title = (payload.get("title") or "Employé·e du mois").strip()
    department = (payload.get("department") or "").strip()
    citation = (payload.get("citation") or "").strip()
    photo_url = (payload.get("photo_url") or "").strip()

    # range dans details pour standardiser l'affichage
    det = dict(aw.details or {})
    if title:
        det["title"] = title
    if department:
        det["department"] = department
    if citation:
        det["citation"] = citation
    if photo_url:
        det["photo_url"] = photo_url
    aw.details = det

    db.session.commit()

    if _wants_json():
        return jsonify(
            {
                "ok": True,
                "award": aw.to_dict(),
            }
        )

    flash("Gagnant du mois mis à jour.", "success")
    return redirect(url_for("awards.index", month=ym))


@bp.get("/winner.json")
@login_required
@roles_required(Role.ADMIN, Role.MANAGER)
def winner_json():
    """Renvoie le gagnant pour un mois donné (JSON)."""
    ym = _get_month_from_request()
    a = Award.query.filter_by(month=ym).first()
    if not a:
        return jsonify({"ok": True, "award": None, "month": ym})
    return jsonify({"ok": True, "award": a.to_dict(), "month": ym})
