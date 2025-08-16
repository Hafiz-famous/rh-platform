import csv, io
from datetime import date
from flask import Blueprint, Response, request, render_template
from flask_login import login_required
from sqlalchemy import func, literal
from ..extensions import db
from ..models.attendance import Attendance   # ⚠️ modèle anglais sans accent
from ..models.overtime import Overtime
from ..models.leave import Leave
from ..models.user import User
from ..services.cost_service import department_costs

bp = Blueprint("exports", __name__, url_prefix="/exports")

# Index /exports/ (page avec liens)
@bp.get("/")
@login_required
def index():
    return render_template("exports/index.html")

def stream_csv(rows, headers, filename):
    def generate():
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(headers)
        yield output.getvalue()
        output.seek(0); output.truncate(0)
        for row in rows:
            writer.writerow(row)
            yield output.getvalue()
            output.seek(0); output.truncate(0)
    return Response(
        generate(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@bp.get("/attendance.csv")
@login_required
def export_attendance():
    """
    Exporte les pointages. Tolérant aux schémas :
      - source facultatif
      - geo_lat/geo_lon ou lat/lon facultatifs
    """
    # Colonnes optionnelles
    source_col = getattr(Attendance, "source", literal(None).label("source"))

    if hasattr(Attendance, "geo_lat") and hasattr(Attendance, "geo_lon"):
        lat_col = getattr(Attendance, "geo_lat")
        lon_col = getattr(Attendance, "geo_lon")
        lat_label, lon_label = "geo_lat", "geo_lon"
    elif hasattr(Attendance, "lat") and hasattr(Attendance, "lon"):
        lat_col = getattr(Attendance, "lat")
        lon_col = getattr(Attendance, "lon")
        lat_label, lon_label = "lat", "lon"
    else:
        lat_col = literal(None).label("lat")
        lon_col = literal(None).label("lon")
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
    )
    rows = q.all()
    headers = ["id","email","date","check_in","check_out","total_hours","source",lat_label,lon_label]
    return stream_csv(rows, headers, "attendance.csv")

@bp.get("/overtime.csv")
@login_required
def export_overtime():
    q = (
        db.session.query(
            Overtime.id, User.email, Overtime.work_date, Overtime.hours, Overtime.status, Overtime.note
        )
        .join(User, User.id == Overtime.user_id)
        .order_by(Overtime.work_date.desc(), Overtime.id.desc())
    )
    rows = q.all()
    headers = ["id","email","date","hours","status","note"]
    return stream_csv(rows, headers, "overtime.csv")

@bp.get("/leaves.csv")
@login_required
def export_leaves():
    q = (
        db.session.query(
            Leave.id, User.email, Leave.start_date, Leave.end_date, Leave.type, Leave.status, Leave.reason
        )
        .join(User, User.id == Leave.user_id)
        .order_by(Leave.start_date.desc(), Leave.id.desc())
    )
    rows = q.all()
    headers = ["id","email","start_date","end_date","type","status","reason"]
    return stream_csv(rows, headers, "leaves.csv")

@bp.get("/department_costs.csv")
@login_required
def export_costs():
    ym = request.args.get("month")
    data = department_costs(ym)
    rows = [(r["department"], r["cost"]) for r in data]
    headers = ["department","cost"]
    return stream_csv(rows, headers, f"department_costs_{(ym or date.today().strftime('%Y-%m'))}.csv")
