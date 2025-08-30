# app/routes/attendance.py
from __future__ import annotations

from math import radians, sin, cos, asin, sqrt
from typing import Optional

from flask import Blueprint, request, jsonify, render_template
from flask_login import login_required, current_user

from ..services.attendance_service import punch_in, punch_out
from ..services.security import verify_token

bp = Blueprint("attendance", __name__, url_prefix="/attendance")

# ================== Géorepérage : ESGIS Avédji ==================
# Centre approximatif du site (à ajuster si tu as des coordonnées plus précises)
SITE_NAME = "ESGIS Avédji"
SITE_LAT  = 6.1727   # <- remplace par la latitude exacte si besoin
SITE_LON  = 1.2124   # <- remplace par la longitude exacte si besoin
SITE_RADIUS_M = 50  # rayon d'acceptation en mètres

# Si True: on REFUSE le pointage hors zone quand lat/lon sont fournis
RESTRICT_TO_SITE = False  # mets True si tu veux bloquer hors périmètre
# ================================================================


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distance en mètres entre 2 points (lat/lon) via Haversine."""
    R = 6371000.0  # rayon moyen de la Terre (m)
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    c = 2 * asin(min(1, sqrt(a)))
    return R * c


def _to_float(x) -> Optional[float]:
    try:
        if x is None or x == "":
            return None
        return float(x)
    except Exception:
        return None


@bp.get("/scan")
@login_required
def scanner():
    return render_template("attendance/scan.html")


@bp.post("/punch")
@login_required
def punch():
    """
    Corps accepté:
      - JSON:  {action: "checkin"|"checkout", lat, lon, token}
      - ou form: action=...&lat=...&lon=...&token=...
    Réponse JSON:
      { ok, attendance_id?, onsite, distance_m?, site, message? }
    """
    # Tolère JSON et formulaire
    payload = request.get_json(silent=True) or request.form or {}
    action  = (payload.get("action") or "").strip().lower()
    token   = payload.get("token")

    lat = _to_float(payload.get("lat"))
    lon = _to_float(payload.get("lon"))

    # Vérif QR si présent
    if token and not verify_token(token):
        return jsonify({"ok": False, "error": "QR invalide ou expiré"}), 400

    # Calcul zone si lat/lon fournis
    onsite = None
    distance_m = None
    if lat is not None and lon is not None:
        distance_m = _haversine_m(lat, lon, SITE_LAT, SITE_LON)
        onsite = distance_m <= SITE_RADIUS_M
        if RESTRICT_TO_SITE and not onsite:
            # On refuse si on a des coordonnées et que c'est hors zone
            return jsonify({
                "ok": False,
                "error": "Hors périmètre autorisé",
                "site": SITE_NAME,
                "distance_m": round(distance_m or 0, 2),
                "radius_m": SITE_RADIUS_M,
            }), 403

    # Source pour historiser
    source = "qr" if token else "manual"

    # Exécute l'action
    if action == "checkin":
        att = punch_in(current_user.id, lat, lon, source=source)
    elif action == "checkout":
        att = punch_out(current_user.id, lat, lon, source=source)
    else:
        return jsonify({"ok": False, "error": "Action invalide"}), 400

    return jsonify({
        "ok": True,
        "attendance_id": att.id,
        "onsite": onsite,
        "distance_m": round(distance_m, 2) if distance_m is not None else None,
        "site": SITE_NAME,
        "message": (
            f"Pointage enregistré {'sur site' if onsite else 'sans géolocalisation'}."
            if onsite is not False else "Pointage enregistré (hors site)."
        ),
    })
