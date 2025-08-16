import io, qrcode
from flask import Blueprint, send_file, request, current_app, url_for
from flask_login import login_required, current_user
from ..services.security import sign_token

bp = Blueprint("qr", __name__, url_prefix="/qr")

@bp.get("/attendance")
@login_required
def gen_attendance_qr():
    # action securisée
    action = (request.args.get("action") or "checkin").lower()
    if action not in {"checkin", "checkout"}:
        action = "checkin"

    # token court
    payload = f"action:{action}|user:{current_user.id}"
    token = sign_token(payload, ttl_seconds=120)

    # URL absolue : privilégie PUBLIC_BASE_URL si défini, sinon fabrique depuis Flask
    base = current_app.config.get("PUBLIC_BASE_URL")
    if base:
        punch_url = f"{base.rstrip('/')}/attendance/scan?token={token}"
    else:
        try:
            # adapte l'endpoint si besoin (ex: "attendance.scan")
            punch_url = url_for("attendance.scan", token=token, _external=True)
        except Exception:
            punch_url = request.url_root.rstrip("/") + f"/attendance/scan?token={token}"

    # Génération du QR
    img = qrcode.make(punch_url)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return send_file(buf, mimetype="image/png")
