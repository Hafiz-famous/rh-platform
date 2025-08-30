# app/routes/exports.py
import csv, io, json
from datetime import date, datetime, time
from typing import Iterable, Any, Optional

from flask import Blueprint, Response, request, render_template
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
    # Enum (SQLAlchemy ou Python)
    if hasattr(v, "value"):
        try:
            return str(v.value)
        except Exception:
            pass
    # Dates & heures
    if isinstance(v, (datetime, date, time)):
        return v.isoformat()
    # Objets complexes -> JSON
    if isinstance(v, (dict, list)):
        return json.dumps(v, ensure_ascii=False)
    return str(v)


def _get_sep() -> str:
    """Séparateur CSV (par défaut ',' ; passer ?sep=; pour Excel FR)."""
    sep = (request.args.get("sep") or ",").strip()
    return ";" if sep == ";" else ","


def stream_csv(rows_iterable: Iterable, headers: list[str], filename: str) -> Response:
    """Génère un CSV streamé (UTF-8 + BOM) avec séparateur configurable."""
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
                # Row SQLA 2.x est séquence-like
                values = list(row)
            except TypeError:
                # Fallback mapping
                values = list(row._mapping.values()) if hasattr(row, "_mapping") else list(row)
            writer.writerow([_serialize_cell(v) for v in values])
            yield output.getvalue()
            output.seek(0); output.truncate(0)

    return Response(
        generate(),
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


def _parse_date(val: Optional[str]) -> Optional[date]:
    if not val:
        return None
    try:
        return datetime.fromisoformat(val).date()
    except Exception:
        return None


# ----------- Exports -----------
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

    # Colonnes potentiellement absentes suivant le schéma
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
    )

    if d_from:
        q = q.filter(Attendance.work_date >= d_from)
    if d_to:
        q = q.filter(Attendance.work_date <= d_to)
    if email:
        q = q.filter(User.email == email)

    q = q.order_by(Attendance.work_date.desc(), Attendance.id.desc())

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
            Overtime.status,   # Enum -> value via _serialize_cell
            Overtime.note,
        )
        .join(User, User.id == Overtime.user_id)
    )

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

    q = q.order_by(Overtime.work_date.desc(), Overtime.id.desc())

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
            Leave.type,     # Enum -> value via _serialize_cell
            Leave.status,   # Enum -> value via _serialize_cell
            Leave.reason,
        )
        .join(User, User.id == Leave.user_id)
    )

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

    q = q.order_by(Leave.start_date.desc(), Leave.id.desc())

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
    data = department_costs(ym)  # [{department, cost}]
    rows = ((r.get("department", ""), r.get("cost", 0)) for r in (data or []))
    headers = ["department","cost"]
    return stream_csv(rows, headers, f"department_costs_{ym}.csv")
