# app/routes/attendance.py
from __future__ import annotations

from math import radians, sin, cos, asin, sqrt
from typing import Optional, Dict, Any, List, Set
from datetime import date

from flask import Blueprint, request, jsonify, render_template, current_app
from flask_login import login_required, current_user

from ..services.attendance_service import punch_in, punch_out
from ..services.security import verify_token
from ..services.overtime_auto import compute_overtime_for_user_day  # <- recalc OT

bp = Blueprint("attendance", __name__, url_prefix="/attendance")

# ================== Géorepérage (valeurs par défaut si non définies en config) ==================
# Dans config.py tu peux définir :
# ATTENDANCE_SITE_NAME, ATTENDANCE_SITE_LAT, ATTENDANCE_SITE_LON, ATTENDANCE_SITE_RADIUS_M, ATTENDANCE_RESTRICT_TO_SITE
DEFAULT_SITE = {
    "ATTENDANCE_SITE_NAME": "ESGIS Avédji",
    "ATTENDANCE_SITE_LAT":  6.1727,
    "ATTENDANCE_SITE_LON":  1.2124,
    "ATTENDANCE_SITE_RADIUS_M": 50,     # mètres
    "ATTENDANCE_RESTRICT_TO_SITE": False
}
# =================================================================================================


def _cfg(key: str, default: Any) -> Any:
    return current_app.config.get(key, default)


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distance en mètres entre 2 points (lat/lon) via Haversine."""
    R = 6371000.0  # rayon moyen de la Terre (m)
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    c = 2 * asin(min(1, sqrt(a)))
    return R * c


def _to_float(x) -> Optional[float]:
    """Convertit une entrée (str|float|None) en float, accepte '6,12'."""
    try:
        if x is None:
            return None
        if isinstance(x, (int, float)):
            return float(x)
        s = str(x).strip()
        if s == "":
            return None
        s = s.replace(",", ".")
        return float(s)
    except Exception:
        return None


@bp.get("/scan")
@login_required
def scanner():
    """Page de scan (QR / géoloc)."""
    return render_template("attendance/scan.html")


@bp.post("/punch")
@login_required
def punch():
    """
    Enregistre un pointage.
    Corps accepté:
      - JSON:  { action: "checkin"|"checkout", lat, lon, token }
      - FORM:  action=...&lat=...&lon=...&token=...
    Réponse JSON:
      { ok, attendance_id?, onsite, distance_m?, site, message,
        ot_days_recomputed?: [ "YYYY-MM-DD", ... ] }
    """
    payload = request.get_json(silent=True) or request.form or {}
    action  = str(payload.get("action") or "").strip().lower()
    token   = payload.get("token")

    lat = _to_float(payload.get("lat"))
    lon = _to_float(payload.get("lon"))

    # Vérif QR si présent
    if token and not verify_token(token):
        return jsonify({"ok": False, "error": "QR invalide ou expiré"}), 400

    # Charge config géorepérage
    site_name   = _cfg("ATTENDANCE_SITE_NAME", DEFAULT_SITE["ATTENDANCE_SITE_NAME"])
    site_lat    = _cfg("ATTENDANCE_SITE_LAT",  DEFAULT_SITE["ATTENDANCE_SITE_LAT"])
    site_lon    = _cfg("ATTENDANCE_SITE_LON",  DEFAULT_SITE["ATTENDANCE_SITE_LON"])
    site_radius = _cfg("ATTENDANCE_SITE_RADIUS_M", DEFAULT_SITE["ATTENDANCE_SITE_RADIUS_M"])
    restrict    = _cfg("ATTENDANCE_RESTRICT_TO_SITE", DEFAULT_SITE["ATTENDANCE_RESTRICT_TO_SITE"])

    # Calcul zone si lat/lon fournis
    onsite: Optional[bool] = None
    distance_m: Optional[float] = None
    if lat is not None and lon is not None:
        distance_m = _haversine_m(lat, lon, float(site_lat), float(site_lon))
        onsite = distance_m <= float(site_radius)
        if restrict and not onsite:
            # On refuse si coordonnées fournies + hors zone
            return jsonify({
                "ok": False,
                "error": "Hors périmètre autorisé",
                "site": site_name,
                "distance_m": round(distance_m or 0, 2),
                "radius_m": site_radius,
            }), 403

    # Source pour historiser
    source = "qr" if token else ("geo" if (lat is not None and lon is not None) else "manual")

    # Action
    if action == "checkin":
        att = punch_in(current_user.id, lat, lon, source=source)
    elif action == "checkout":
        att = punch_out(current_user.id, lat, lon, source=source)
    else:
        return jsonify({"ok": False, "error": "Action invalide (attendu: checkin|checkout)"}), 400

    # === Recalcul automatique des heures sup ===
    # On (re)calcule pour tous les jours touchés par ce pointage (utile si passage minuit).
    ot_days_recomputed: List[str] = []
    try:
        days: Set[date] = set()
        if getattr(att, "check_in", None):
            days.add(att.check_in.date())
        if getattr(att, "check_out", None):
            days.add(att.check_out.date())
        # Si checkout absent (encore ouvert), rien à recalculer de fiable.
        for d in days:
            compute_overtime_for_user_day(att.user_id, d)
            ot_days_recomputed.append(d.isoformat())
    except Exception as e:
        current_app.logger.exception("Recalcul OT échoué: %s", e)

    # Message UX
    if onsite is False:
        msg = "Pointage enregistré (hors site)."
    elif onsite is True:
        msg = "Pointage enregistré sur site."
    else:
        msg = "Pointage enregistré."

    return jsonify({
        "ok": True,
        "attendance_id": getattr(att, "id", None),
        "onsite": onsite,
        "distance_m": round(distance_m, 2) if distance_m is not None else None,
        "site": site_name,
        "message": msg,
        "ot_days_recomputed": ot_days_recomputed or None,
    })
