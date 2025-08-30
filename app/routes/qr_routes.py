# app/routes/qr_routes.py
from flask import Blueprint, request, send_file, current_app
import io, qrcode
from app.services.qr_sign import sign_url

qr_bp = Blueprint("qr", __name__, url_prefix="/qr")

@qr_bp.get("/attendance")
def qr_attendance():
    action = request.args.get("action", "checkin")

    # 1) base = ENV/Config sinon l'hôte courant (IP si tu ouvres via l'IP)
    base = (current_app.config.get("PUBLIC_BASE_URL") or request.host_url).rstrip("/")

    # 2) on signe un chemin relatif
    path = f"/attendance/scan?action={action}"
    signed = sign_url(path, ttl=300)  # 5 min pour être tranquille pendant la démo

    url = f"{base}{signed}"

    # (utile pour vérifier dans la console)
    current_app.logger.info("QR target = %s", url)

    # 3) image QR et anti-cache
    img = qrcode.make(url)
    buf = io.BytesIO()
    img.save(buf, format="PNG"); buf.seek(0)
    resp = send_file(buf, mimetype="image/png")
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    return resp
