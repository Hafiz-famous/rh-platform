# app/routes/overtime.py
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Optional

from flask import Blueprint, jsonify, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from sqlalchemy import func

# db: essaie extensions, sinon app.db
try:
    from ..extensions import db
except Exception:  # pragma: no cover
    from .. import db  # type: ignore

# Modèles
from ..models.overtime import Overtime
from ..models.enums import RequestStatus, Role
from ..models.user import User

# Ces deux imports sont "meilleurs efforts"
try:
    from ..models.punch import Punch     # check_in, check_out, user_id, ...
except Exception:  # pragma: no cover
    Punch = None  # type: ignore

try:
    from ..models.schedule import Schedule  # daily_hours, break_minutes, etc.
except Exception:  # pragma: no cover
    Schedule = None  # type: ignore

# Services existants
from ..services.overtime_service import declare_overtime, set_status
from ..services.authz import roles_required

# (optionnel) recalcul auto si tu as mis en place le service
try:
    from ..services.overtime_auto import compute_overtime_for_range  # (user_id, d1, d2)
except Exception:  # pragma: no cover
    compute_overtime_for_range = None

bp = Blueprint("overtime", __name__, url_prefix="/overtime")


# ----------------------------- Helpers -----------------------------
def _cfg(key: str, default):
    return current_app.config.get(key, default)

def _cfg_bool(key: str, default: int | bool = 0) -> bool:
    v = str(_cfg(key, default)).strip().lower()
    return v in {"1", "true", "yes", "y", "on"}

def _wants_json() -> bool:
    if request.is_json:
        return True
    accept = request.headers.get("Accept", "")
    return "application/json" in accept and "text/html" not in accept

def _parse_iso_date(s: str | None) -> date:
    if not s:
        raise ValueError("Date manquante")
    try:
        return date.fromisoformat(str(s).strip()[:10])
    except Exception as e:
        raise ValueError("Format de date invalide (attendu YYYY-MM-DD)") from e

def _parse_hours(x) -> float:
    if x is None or str(x).strip() == "":
        raise ValueError("Heures manquantes")
    try:
        v = float(str(x).replace(",", "."))
    except Exception as e:
        raise ValueError("Heures invalides") from e
    if v < 0:
        raise ValueError("Heures négatives interdites")

    # arrondi au pas (en minutes) -> heures
    step_min = int(_cfg("OVERTIME_ROUND_STEP", 15))
    step_h = max(step_min, 1) / 60.0
    v = (int(v / step_h)) * step_h  # floor
    return round(v + 1e-8, 4)

def _parse_status(s: str | None) -> RequestStatus:
    if not s:
        raise ValueError("Statut manquant")
    key = str(s).strip().upper()
    try:
        return RequestStatus[key]  # par name
    except Exception:
        pass
    try:
        return RequestStatus(key)  # par value
    except Exception as e:
        raise ValueError("Statut invalide") from e


# ---------- Fallback de calcul auto (si service non disponible) ----------
def _get_schedule_for_user_on(user_id: int, day: date):
    """Essaie plusieurs conventions de Schedule, sinon None."""
    if not Schedule:
        return None
    if hasattr(Schedule, "for_user_on"):
        try:
            return Schedule.for_user_on(user_id, day)  # type: ignore[attr-defined]
        except Exception:
            pass
    return None

def _recalc_overtime_one_day(user_id: int, day: date) -> float:
    """
    Calcule et upsert l'OT 'auto' pour une journée :
    - 1er check-in et dernier check-out du jour,
    - pause planifiée (schedule.break_minutes) si dispo,
    - comparaison au standard (schedule.daily_hours ou OVERTIME_DAILY_STANDARD),
    - grâce (OVERTIME_GRACE_MINUTES) et plafond (OVERTIME_DAILY_CAP),
    - arrondi au pas (OVERTIME_ROUND_STEP),
    - enregistre dans Overtime(origin='auto'), status auto-approve selon OVERTIME_AUTO_APPROVE.
    """
    if not Punch:
        return 0.0

    # Éviter les surprises de typage (SQLite renvoie une chaîne pour date(...))
    punches = (
        Punch.query
        .filter(Punch.user_id == user_id)
        .filter(func.date(Punch.check_in) == day.isoformat())
        .all()
    )
    if not punches:
        return 0.0

    ins  = [p.check_in  for p in punches if getattr(p, "check_in", None)]
    outs = [p.check_out for p in punches if getattr(p, "check_out", None)]
    if not ins or not outs:
        # journée non clôturée => pas de HS
        return 0.0

    start, end = min(ins), max(outs)

    sched = _get_schedule_for_user_on(user_id, day)
    standard_h  = float(getattr(sched, "daily_hours", None) or _cfg("OVERTIME_DAILY_STANDARD", 8))
    break_min   = int(getattr(sched, "break_minutes", 0) or 0)
    grace_min   = int(_cfg("OVERTIME_GRACE_MINUTES", 0))
    cap_min     = int(_cfg("OVERTIME_DAILY_CAP", 0))  # 0 = pas de plafond

    worked_h = ((end - start).total_seconds() / 3600.0) - (break_min / 60.0)
    worked_h = max(0.0, round(worked_h, 2))
    overtime = max(0.0, round(worked_h - standard_h, 2))  # heures

    # Grâce (seuil) : si HS <= grâce => 0
    if grace_min > 0 and overtime * 60 <= grace_min:
        overtime = 0.0

    # Plafond quotidien (en minutes)
    if cap_min > 0:
        overtime = min(overtime, cap_min / 60.0)

    # Arrondi (vers le bas) sur les HS
    step_min = int(_cfg("OVERTIME_ROUND_STEP", 15))
    if step_min > 1 and overtime > 0:
        step_h = step_min / 60.0
        overtime = (int(overtime / step_h)) * step_h
        overtime = round(overtime + 1e-8, 2)

    # Upsert (origin="auto")
    rec = (
        Overtime.query
        .filter_by(user_id=user_id, work_date=day, origin="auto")
        .one_or_none()
    )
    if rec is None:
        default_status = RequestStatus.APPROVED if _cfg_bool("OVERTIME_AUTO_APPROVE", 0) else RequestStatus.PENDING
        rec = Overtime(
            user_id=user_id,
            work_date=day,
            origin="auto",
            status=default_status,
        )
        db.session.add(rec)

    rec.hours = overtime
    # Champs de note/horodatage compatibles avec ton template
    calc_note = f"worked={worked_h}h - std={standard_h}h - break={break_min/60}h"
    if hasattr(rec, "note_calc"):
        rec.note_calc = calc_note
    elif hasattr(rec, "calc_note"):
        rec.calc_note = calc_note
    now = datetime.utcnow()
    if hasattr(rec, "calc_at"):
        rec.calc_at = now
    elif hasattr(rec, "last_computed_at"):
        rec.last_computed_at = now

    db.session.commit()
    return overtime

def _recalc_range_for_user(user_id: int, d1: date, d2: date) -> float:
    if compute_overtime_for_range:
        compute_overtime_for_range(user_id, d1, d2)
        return 0.0  # le service gère la persistance + agrégat
    total = 0.0
    cur = d1
    while cur <= d2:
        total += _recalc_overtime_one_day(user_id, cur)
        cur += timedelta(days=1)
    return total


# ------------------------------ Routes ------------------------------
@bp.get("/")
@login_required
def index():
    q = (
        Overtime.query
        .filter(Overtime.user_id == current_user.id)
        .order_by(Overtime.created_at.desc())
    )
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
    allow_manual = bool(_cfg("OVERTIME_ALLOW_MANUAL", True))
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

        declare_overtime(user_id=current_user.id, work_date=work_date, hours=hours, note=note)

    except ValueError as ve:
        if _wants_json():
            return jsonify(ok=False, error=str(ve)), 422
        flash(f"Erreur: {ve}", "danger")
        return redirect(url_for("overtime.index"))
    except Exception:
        current_app.logger.exception("Overtime create failed")
        if _wants_json():
            return jsonify(ok=False, error="Erreur serveur"), 500
        flash("Erreur serveur", "danger")
        return redirect(url_for("overtime.index"))

    if _wants_json():
        return jsonify(ok=True), 201

    flash("Heures supplémentaires déclarées.", "success")
    return redirect(url_for("overtime.index"))


@bp.get("/pending")
@login_required
@roles_required(Role.ADMIN, Role.MANAGER)
def pending():
    q = (
        Overtime.query
        .filter(Overtime.status == RequestStatus.PENDING)
        .order_by(Overtime.created_at.desc())
    )
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
        ot = set_status(ot_id, st)
        return jsonify({"ok": True, "status": ot.status.value})
    except ValueError as ve:
        return jsonify({"ok": False, "error": str(ve)}), 400
    except LookupError:
        return jsonify({"ok": False, "error": "Enregistrement introuvable"}), 404
    except Exception:
        current_app.logger.exception("Overtime status change failed")
        return jsonify({"ok": False, "error": "Erreur serveur"}), 500


# -------- Recalcul auto côté utilisateur (2 URLs pour compatibilité) --------
def _handle_recalc_request():
    """
    Recalcule les HS automatiques sur [from, to] (ISO).
    Si pas de paramètres, utilise aujourd'hui.
    """
    payload = request.get_json(silent=True) or {}
    f = request.args.get("from") or payload.get("from")
    t = request.args.get("to")   or payload.get("to")
    try:
        if not f and not t:
            today = date.today()
            f = t = today.isoformat()
        d1 = _parse_iso_date(f)
        d2 = _parse_iso_date(t)
        if d2 < d1:
            raise ValueError("Intervalle invalide (to < from)")
        total = _recalc_range_for_user(current_user.id, d1, d2)
        return jsonify(ok=True, _from=d1.isoformat(), _to=d2.isoformat(), hours=round(total, 2))
    except ValueError as ve:
        return jsonify(ok=False, error=str(ve)), 422
    except Exception:
        current_app.logger.exception("Overtime recalculation failed")
        return jsonify(ok=False, error="Erreur serveur"), 500

@bp.post("/recalc")
@login_required
def recalc():
    return _handle_recalc_request()

@bp.post("/recompute")  # alias pour compat
@login_required
def recompute_self():
    return _handle_recalc_request()


# -------- Recalcul de masse (ADMIN) --------------------------------
@bp.post("/admin/recalc")
@login_required
@roles_required(Role.ADMIN)
def admin_recalc():
    """
    Recalcule les HS automatiques pour un user (user_id) ou pour tous,
    sur [from, to] (ISO). Si dates absentes: du 1er du mois -> aujourd'hui.
    """
    payload = request.get_json(silent=True) or {}
    try:
        d1 = _parse_iso_date(payload.get("from")) if payload.get("from") else None
        d2 = _parse_iso_date(payload.get("to"))   if payload.get("to")   else None
        if not d1 or not d2:
            today = date.today()
            d1 = d1 or today.replace(day=1)
            d2 = d2 or today

        user_id = payload.get("user_id")
        if user_id:
            user = User.query.get(int(user_id))
            if not user:
                return jsonify(ok=False, error="Utilisateur introuvable"), 404
            users = [user]
        else:
            users = User.query.all()

        total = 0.0
        for u in users:
            total += _recalc_range_for_user(u.id, d1, d2)

        return jsonify(ok=True, users=len(users), hours=round(total, 2),
                       _from=d1.isoformat(), _to=d2.isoformat())
    except ValueError as ve:
        return jsonify(ok=False, error=str(ve)), 422
    except Exception:
        current_app.logger.exception("Admin overtime recalculation failed")
        return jsonify(ok=False, error="Erreur serveur"), 500
