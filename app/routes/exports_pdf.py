
from flask import Blueprint, make_response, request
from flask_login import login_required
from datetime import date
from ..services.pdf_service import build_month_report

bp = Blueprint("exports_pdf", __name__, url_prefix="/exports")

@bp.get("/report.pdf")
@login_required
def report_pdf():
    ym = request.args.get("month") or date.today().strftime("%Y-%m")
    pdf_bytes = build_month_report(ym)
    resp = make_response(pdf_bytes)
    resp.headers.set("Content-Type", "application/pdf")
    resp.headers.set("Content-Disposition", f"inline; filename=rapport_{ym}.pdf")
    return resp
