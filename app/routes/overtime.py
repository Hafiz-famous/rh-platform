# app/routes/overtime.py
from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from flask import Blueprint, jsonify, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user

from ..models.overtime import Overtime
from ..models.enums import RequestStatus, Role
from ..services.overtime_service import declare_overtime, set_status
from ..services.authz import roles_required

# (optionnel) recalcul auto si tu as mis en place le service
try:
    from ..services.overtime_auto import compute_overtime_for_range
except Exception:  # pragma: no cover
    compute_overtime_for_range = None

bp = Blueprint("overtime", __name__, url_prefix="/overtime")


# ----------------------------- Helpers -----------------------------
def _wants_json() -> bool:
    if request.is_json:
        return True
    accept = request.headers.get("Accept", "")
    return "application/json" in accept and "text/html" not in accept

def _parse_iso_date(s: str | None) -> date:
    if not s:
        raise ValueError("Date manquante")
    # On accepte 'YYYY-MM-DD' uniquement
    try:
        return date.fromisoformat(s.strip()[:10])
    except Exception as e:
        raise ValueError("Format de date invalide (attendu YYYY-MM-DD)") from e

def _parse_hours(x) -> float:
    if x is None or str(x).strip() == "":
        raise ValueError("Heures manquantes")
    try:
        # accepte "1,5"
        v = float(str(x).replace(",", "."))
    except Exception as e:
        raise ValueError("Heures invalides") from e
    if v < 0:
        raise ValueError("Heures négatives interdites")
    # arrondi au pas configuré (en minutes) -> heures
    step_min = int(current_app.config.get("OVERTIME_ROUND_STEP", 15))
    step_h = max(step_min, 1) / 60.0
    # arrondi "vers le bas" au pas (évite surestimation)
    v = (int(v / step_h)) * step_h
    # évite les flottants bizarres
    return round(v + 1e-8, 4)

def _parse_status(s: str | None) -> RequestStatus:
    if not s:
        raise ValueError("Statut manquant")
    key = str(s).strip().upper()
    # tolère valeur ou nom (e.g. "approved" ou "APPROVED")
    try:
        # via name
        return RequestStatus[key]
    except Exception:
        pass
    try:
        # via value
        return RequestStatus(key)
    except Exception as e:
        raise ValueError("Statut invalide") from e


# ------------------------------ Routes ------------------------------
@bp.get("/")
@login_required
def index():
    # historique de l'utilisateur courant
    q = (Overtime.query
         .filter(Overtime.user_id == current_user.id)
         .order_by(Overtime.created_at.desc()))
    items = q.all()
    return render_template("overtime/index.html", items=items)


@bp.post("/")
@login_required
def create():
    """
    Crée une déclaration d'heures sup (MANUELLE).
    Refusée si OVERTIME_ALLOW_MANUAL=False (mode auto strict).
    Accepte FORM ou JSON.
    """
    allow_manual = bool(current_app.config.get("OVERTIME_ALLOW_MANUAL", True))
    if not allow_manual:
        msg = "La déclaration manuelle est désactivée (heures calculées automatiquement)."
        if _wants_json():
            return jsonify(ok=False, error=msg), 403
        flash(msg, "warning")
        return redirect(url_for("overtime.index"))

    payload = request.get_json(silent=True) or request.form or {}
    try:
        work_date = _parse_iso_date(payload.get("work_date"))
        hours = _parse_hours(payload.get("hours"))
        note = (payload.get("note") or "").strip() or None

        # délègue à ton service (qui commit/valide)
        declare_overtime(
            user_id=current_user.id,
            work_date=work_date,
            hours=hours,
            note=note,
        )

    except ValueError as ve:
        if _wants_json():
            return jsonify(ok=False, error=str(ve)), 422
        flash(f"Erreur: {ve}", "danger")
        return redirect(url_for("overtime.index"))
    except Exception as e:
        if _wants_json():
            return jsonify(ok=False, error="Erreur serveur"), 500
        flash(f"Erreur: {e}", "danger")
        return redirect(url_for("overtime.index"))

    if _wants_json():
        return jsonify(ok=True), 201

    flash("Heures supplémentaires déclarées.", "success")
    return redirect(url_for("overtime.index"))


@bp.get("/pending")
@login_required
@roles_required(Role.ADMIN, Role.MANAGER)
def pending():
    # vue de validation côté RH/manager
    q = (Overtime.query
         .filter(Overtime.status == RequestStatus.PENDING)
         .order_by(Overtime.created_at.desc()))
    items = q.all()
    return render_template("overtime/pending.html", items=items)


@bp.post("/<int:ot_id>/status")
@login_required
@roles_required(Role.ADMIN, Role.MANAGER)
def status_ot(ot_id: int):
    """
    Change le statut d'une ligne d'OT.
    Body: JSON {status:"APPROVED|REJECTED"} ou form 'status=...'
    """
    payload = request.get_json(silent=True) or request.form or {}
    try:
        st = _parse_status(payload.get("status"))
        ot = set_status(ot_id, st)  # ton service gère l'autorisation/commit
        return jsonify({"ok": True, "status": ot.status.value})
    except ValueError as ve:
        return jsonify({"ok": False, "error": str(ve)}), 400
    except LookupError:
        return jsonify({"ok": False, "error": "Enregistrement introuvable"}), 404
    except Exception:
        return jsonify({"ok": False, "error": "Erreur serveur"}), 500


# ----------- (Optionnel) Recalcul auto côté utilisateur -----------
@bp.post("/recompute")
@login_required
def recompute_self():
    """
    Recalcule les heures sup AUTOMATIQUES sur un intervalle [from, to] (ISO).
    Utile si l'utilisateur corrige un pointage.
    Si les services auto ne sont pas installés, renvoie 501.
    """
    if compute_overtime_for_range is None:
        return jsonify(ok=False, error="Service non disponible"), 501

    f = request.args.get("from") or (request.json or {}).get("from")
    t = request.args.get("to")   or (request.json or {}).get("to")
    try:
        if not f and not t:
            today = date.today()
            f = t = today.isoformat()
        d1 = _parse_iso_date(f)
        d2 = _parse_iso_date(t)
        if d2 < d1:
            raise ValueError("Intervalle invalide (to < from)")
        compute_overtime_for_range(current_user.id, d1, d2)
        return jsonify(ok=True, _from=d1.isoformat(), _to=d2.isoformat())
    except ValueError as ve:
        return jsonify(ok=False, error=str(ve)), 422
    except Exception:
        return jsonify(ok=False, error="Erreur serveur"), 500
