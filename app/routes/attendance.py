
from flask import Blueprint, request, jsonify, render_template
from flask_login import login_required, current_user
from ..services.attendance_service import punch_in, punch_out
from ..services.security import verify_token

bp = Blueprint("attendance", __name__, url_prefix="/attendance")

@bp.get("/scan")
@login_required
def scanner():
    return render_template("attendance/scan.html")

@bp.post("/punch")
@login_required
def punch():
    payload = request.json or {}
    action = payload.get("action")
    lat = payload.get("lat")
    lon = payload.get("lon")
    token = payload.get("token")

    if token and not verify_token(token):
        return jsonify({"ok": False, "error": "QR invalide ou expiré"}), 400

    if action == "checkin":
        att = punch_in(current_user.id, lat, lon, source="qr" if token else "manual")
    elif action == "checkout":
        att = punch_out(current_user.id, lat, lon, source="qr" if token else "manual")
    else:
        return jsonify({"ok": False, "error": "Action invalide"}), 400

    return jsonify({"ok": True, "attendance_id": att.id})
