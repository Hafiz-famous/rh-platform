# app/routes/exports_pdf.py
import re
from datetime import date
from flask import Blueprint, make_response, request, abort, current_app
from flask_login import login_required

from ..services.pdf_service import build_month_report

bp = Blueprint("exports_pdf", __name__, url_prefix="/exports")

_MONTH_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")

def _safe_month(val: str | None) -> str:
    """Retourne un mois valide 'YYYY-MM' (ou mois courant si invalide)."""
    if val and _MONTH_RE.match(val):
        return val
    return date.today().strftime("%Y-%m")

@bp.get("/report.pdf")
@login_required
def report_pdf():
    ym = _safe_month(request.args.get("month"))

    try:
        pdf_bytes = build_month_report(ym)  # doit renvoyer des bytes
    except Exception:
        current_app.logger.exception("Échec de génération PDF pour %s", ym)
        abort(500, description="Erreur lors de la génération du rapport.")

    if not pdf_bytes:
        abort(404, description="Rapport indisponible.")

    # ?dl=1 -> force téléchargement ; sinon affichage inline
    disposition = "attachment" if request.args.get("dl") in ("1", "true", "yes") else "inline"
    filename = f"rapport_{ym}.pdf"

    resp = make_response(pdf_bytes)
    resp.headers["Content-Type"] = "application/pdf"
    resp.headers["Content-Disposition"] = f'{disposition}; filename="{filename}"'
    resp.headers["Cache-Control"] = "no-store, max-age=0"
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["Content-Length"] = str(len(pdf_bytes))
    return resp
