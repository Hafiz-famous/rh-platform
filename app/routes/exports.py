# app/routes/exports.py
import csv, io, json
from datetime import date, datetime, time
from typing import Iterable, Any, Optional

from flask import Blueprint, Response, request, render_template, stream_with_context, current_app, make_response
from flask_login import login_required
from sqlalchemy import literal

from ..extensions import db
from ..models.attendance import Attendance
from ..models.overtime import Overtime
from ..models.leave import Leave
from ..models.user import User
from ..models.enums import Role, LeaveStatus, RequestStatus
from ..services.cost_service import department_costs
from ..services.authz import roles_required

bp = Blueprint("exports", __name__, url_prefix="/exports")


# ----------- Page index /exports/ -----------
@bp.get("/")
@login_required
def index():
    return render_template("exports/index.html")


# ----------- Helpers -----------
def _serialize_cell(v: Any) -> str:
    """CSV-safe: Enum -> value, date/datetime/time -> isoformat, dict/list -> json, None -> ''."""
    if v is None:
        return ""
    if hasattr(v, "value"):  # enum
        try:
            return str(v.value)
        except Exception:
            pass
    if isinstance(v, (datetime, date, time)):
        return v.isoformat()
    if isinstance(v, (dict, list)):
        return json.dumps(v, ensure_ascii=False)
    return str(v)


def _get_sep() -> str:
    """Séparateur CSV (par défaut ',' ; passer ?sep=; pour Excel FR)."""
    sep = (request.args.get("sep") or ",").strip()
    return ";" if sep == ";" else ","


def stream_csv(rows_iterable: Iterable, headers: list[str], filename: str) -> Response:
    """
    Génère un CSV streamé (UTF-8 + BOM) avec séparateur configurable.
    ⚠️ Enveloppe le générateur dans `stream_with_context` pour garder le contexte Flask.
    """
    delimiter = _get_sep()

    def generate():
        # BOM pour Excel
        yield "\ufeff"
        output = io.StringIO(newline="")
        writer = csv.writer(output, delimiter=delimiter)

        # En-têtes
        writer.writerow(headers)
        yield output.getvalue()
        output.seek(0); output.truncate(0)

        # Lignes
        for row in rows_iterable:
            try:
                values = list(row)  # SQLA Row (séquence-like)
            except TypeError:
                values = list(getattr(row, "_mapping", {}).values()) if hasattr(row, "_mapping") else list(row)
            writer.writerow([_serialize_cell(v) for v in values])
            yield output.getvalue()
            output.seek(0); output.truncate(0)

    return Response(
        stream_with_context(generate()),  # ✅ garde le contexte app pendant le streaming
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


def _parse_date(val: Optional[str]) -> Optional[date]:
    if not val:
        return None
    try:
        return datetime.fromisoformat(val).date()
    except Exception:
        return None


# ----------- Exports CSV -----------
@bp.get("/attendance.csv")
@login_required
@roles_required(Role.ADMIN, Role.MANAGER)
def export_attendance():
    """
    Exporte les pointages.
    Filtres optionnels:
      - from (YYYY-MM-DD)
      - to   (YYYY-MM-DD)
      - email (ex: user@domaine.tg)
    Colonnes optionnelles gérées : source, (geo_lat/geo_lon) ou (lat/lon), total_hours.
    """
    d_from = _parse_date(request.args.get("from") or request.args.get("date_from"))
    d_to   = _parse_date(request.args.get("to")   or request.args.get("date_to"))
    email  = (request.args.get("email") or "").strip()

    source_col = getattr(Attendance, "source", literal(None).label("source"))

    if hasattr(Attendance, "geo_lat") and hasattr(Attendance, "geo_lon"):
        lat_col, lon_col = getattr(Attendance, "geo_lat"), getattr(Attendance, "geo_lon")
        lat_label, lon_label = "geo_lat", "geo_lon"
    elif hasattr(Attendance, "lat") and hasattr(Attendance, "lon"):
        lat_col, lon_col = getattr(Attendance, "lat"), getattr(Attendance, "lon")
        lat_label, lon_label = "lat", "lon"
    else:
        lat_col, lon_col = literal(None).label("lat"), literal(None).label("lon")
        lat_label, lon_label = "lat", "lon"

    total_hours_col = getattr(Attendance, "total_hours", literal(0).label("total_hours"))

    q = (
        db.session.query(
            Attendance.id,
            User.email,
            Attendance.work_date,
            Attendance.check_in,
            Attendance.check_out,
            total_hours_col,
            source_col,
            lat_col,
            lon_col,
        )
        .join(User, User.id == Attendance.user_id)
        .order_by(Attendance.work_date.desc(), Attendance.id.desc())
    ).execution_options(yield_per=1000)  # ✅ streaming efficace

    if d_from:
        q = q.filter(Attendance.work_date >= d_from)
    if d_to:
        q = q.filter(Attendance.work_date <= d_to)
    if email:
        q = q.filter(User.email == email)

    headers = ["id","email","date","check_in","check_out","total_hours","source",lat_label,lon_label]
    return stream_csv(q, headers, "attendance.csv")


@bp.get("/overtime.csv")
@login_required
@roles_required(Role.ADMIN, Role.MANAGER)
def export_overtime():
    """
    Exporte les heures supplémentaires.
    Filtres optionnels:
      - from/to (YYYY-MM-DD)
      - status: PENDING | APPROVED | REJECTED | CANCELLED
      - email
    """
    d_from = _parse_date(request.args.get("from") or request.args.get("date_from"))
    d_to   = _parse_date(request.args.get("to")   or request.args.get("date_to"))
    status = (request.args.get("status") or "").upper().strip()
    email  = (request.args.get("email")  or "").strip()

    q = (
        db.session.query(
            Overtime.id,
            User.email,
            Overtime.work_date,
            Overtime.hours,
            Overtime.status,
            Overtime.note,
        )
        .join(User, User.id == Overtime.user_id)
        .order_by(Overtime.work_date.desc(), Overtime.id.desc())
    ).execution_options(yield_per=1000)

    if d_from:
        q = q.filter(Overtime.work_date >= d_from)
    if d_to:
        q = q.filter(Overtime.work_date <= d_to)
    if status:
        try:
            st = RequestStatus[status]
            q = q.filter(Overtime.status == st)
        except KeyError:
            pass
    if email:
        q = q.filter(User.email == email)

    headers = ["id","email","date","hours","status","note"]
    return stream_csv(q, headers, "overtime.csv")


@bp.get("/leaves.csv")
@login_required
@roles_required(Role.ADMIN, Role.MANAGER)
def export_leaves():
    """
    Exporte les congés.
    Filtres optionnels:
      - from/to (YYYY-MM-DD) sur start_date
      - status: PENDING | APPROVED | REJECTED | CANCELLED
      - email
    """
    d_from = _parse_date(request.args.get("from") or request.args.get("date_from"))
    d_to   = _parse_date(request.args.get("to")   or request.args.get("date_to"))
    status = (request.args.get("status") or "").upper().strip()
    email  = (request.args.get("email")  or "").strip()

    q = (
        db.session.query(
            Leave.id,
            User.email,
            Leave.start_date,
            Leave.end_date,
            Leave.type,
            Leave.status,
            Leave.reason,
        )
        .join(User, User.id == Leave.user_id)
        .order_by(Leave.start_date.desc(), Leave.id.desc())
    ).execution_options(yield_per=1000)

    if d_from:
        q = q.filter(Leave.start_date >= d_from)
    if d_to:
        q = q.filter(Leave.start_date <= d_to)
    if status:
        try:
            st = LeaveStatus[status]
            q = q.filter(Leave.status == st)
        except KeyError:
            pass
    if email:
        q = q.filter(User.email == email)

    headers = ["id","email","start_date","end_date","type","status","reason"]
    return stream_csv(q, headers, "leaves.csv")


@bp.get("/department_costs.csv")
@login_required
@roles_required(Role.ADMIN, Role.MANAGER)
def export_costs():
    """
    Exporte les coûts par département du mois demandé.
    Paramètres :
      - month=YYYY-MM (défaut: mois courant)
    """
    ym = request.args.get("month") or date.today().strftime("%Y-%m")
    data = department_costs(ym) or []  # [{department, cost}]
    rows = ((r.get("department", ""), r.get("cost", 0)) for r in data)

    headers = ["department", "cost"]
    return stream_csv(rows, headers, f"department_costs_{ym}.csv")


# ----------- Rapport "PDF" (placeholder HTML) -----------
@bp.get("/report/pdf", endpoint="report_pdf")
@login_required
@roles_required(Role.ADMIN, Role.MANAGER)
def report_pdf():
    """
    Endpoint attendu par le template: url_for('exports.report_pdf')
    Pour l'instant, renvoie un HTML minimal (placeholder).
    Remplace par une génération PDF (WeasyPrint, xhtml2pdf, etc.) quand tu es prêt.
    """
    ym = request.args.get("month") or date.today().strftime("%Y-%m")
    data = department_costs(ym) or []  # [{department, cost}]

    # Si tu as un template Jinja, dé-commente:
    # html = render_template("exports/report.html", month=ym, rows=data)

    # Placeholder HTML inline pour éviter une dépendance PDF immédiate
    rows_html = "\n".join(
        f"<tr><td>{_serialize_cell(r.get('department'))}</td><td>{_serialize_cell(r.get('cost'))}</td></tr>"
        for r in data
    )
    html = f"""
    <!doctype html>
    <html><head><meta charset="utf-8"><title>Rapport {ym}</title></head>
    <body>
      <h1>Rapport des coûts par département — {ym}</h1>
      <table border="1" cellpadding="6" cellspacing="0">
        <thead><tr><th>Département</th><th>Coût</th></tr></thead>
        <tbody>{rows_html or '<tr><td colspan="2">Aucune donnée</td></tr>'}</tbody>
      </table>
    </body></html>
    """

    resp = make_response(html)
    resp.headers["Content-Type"] = "text/html; charset=utf-8"
    # Quand tu implémentes le PDF, remplace ci-dessus par 'application/pdf'
    # et retourne les bytes PDF.
    return resp
