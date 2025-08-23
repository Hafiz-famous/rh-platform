# app/routes/qr_routes.py
from flask import Blueprint, request, send_file, abort, current_app
import io, qrcode
from app.services.qr_sign import sign_url

qr_bp = Blueprint("qr", __name__, url_prefix="/qr")

@qr_bp.get("/attendance")
def qr_attendance():
    action = request.args.get("action", "checkin")
    base = current_app.config["PUBLIC_BASE_URL"].rstrip("/")
    path = f"/attendance/scan?action={action}"
    signed = sign_url(path, ttl=60)  # lien valide 60s
    url = f"{base}{signed}"

    img = qrcode.make(url)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return send_file(buf, mimetype="image/png")
