
from io import BytesIO
from datetime import datetime, date
from typing import List, Tuple
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from ..extensions import db
from ..models.user import User
from ..models.attendance import Attendance
from ..models.overtime import Overtime
from ..models.leave import Leave
from ..models.enums import RequestStatus, LeaveStatus
from ..services.cost_service import department_costs
from ..services.award_service import compute_month_scores
from ..services.award_service import month_range

def _register_font():
    try:
        pdfmetrics.registerFont(TTFont("DejaVu", "DejaVuSans.ttf"))
        return "DejaVu"
    except Exception:
        return "Helvetica"

def _draw_header(c: canvas.Canvas, title: str, ym: str, font_name: str):
    c.setFont(font_name, 18)
    c.drawString(20*mm, 280*mm, title)
    c.setFont(font_name, 10)
    c.setFillColor(colors.grey)
    c.drawString(20*mm, 274*mm, f"Mois: {ym}   Généré: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    c.setFillColor(colors.black)
    c.line(20*mm, 272*mm, 190*mm, 272*mm)

def _para(c: canvas.Canvas, text: str, x_mm: float, y_mm: float, font_name: str, size: int=10):
    c.setFont(font_name, size)
    c.drawString(x_mm*mm, y_mm*mm, text)

def _table(c: canvas.Canvas, headers: List[str], rows: List[Tuple], x_mm: float, y_mm: float, col_w_mm: List[float], font_name: str):
    c.setFont(font_name, 10)
    y = y_mm*mm
    x = x_mm*mm
    h = 6*mm
    # header
    c.setFillColor(colors.lightgrey)
    c.rect(x, y, sum(col_w_mm)*mm, h, fill=True, stroke=False)
    c.setFillColor(colors.black)
    cx = x
    for i, head in enumerate(headers):
        c.drawString(cx + 2*mm, y + 2*mm, str(head))
        cx += col_w_mm[i]*mm
    y -= h
    # rows
    for r in rows:
        cx = x
        for i, head in enumerate(headers):
            val = r[i]
            c.drawString(cx + 2*mm, y + 2*mm, str(val))
            cx += col_w_mm[i]*mm
        y -= h
    return y / mm

def _bar_chart(c: canvas.Canvas, data: List[Tuple[str, float]], x_mm: float, y_mm: float, w_mm: float, h_mm: float, font_name: str):
    # simple horizontal bars for department costs
    x = x_mm*mm
    y = y_mm*mm
    w = w_mm*mm
    h = h_mm*mm
    c.setStrokeColor(colors.black)
    c.rect(x, y, w, h, fill=False)
    if not data:
        return
    maxv = max(v for _, v in data) or 1.0
    bar_h = h / max(1, len(data))
    for idx, (label, value) in enumerate(data):
        bh = bar_h*0.7
        by = y + h - (idx+1)*bar_h + (bar_h - bh)/2
        bw = (value / maxv) * (w - 30*mm)
        c.setFillColor(colors.darkblue)
        c.rect(x + 25*mm, by, bw, bh, fill=True, stroke=False)
        c.setFillColor(colors.black)
        c.setFont(font_name, 9)
        c.drawRightString(x + 23*mm, by + bh/2 - 2, label[:18])
        c.drawString(x + 26*mm + bw, by + bh/2 - 2, f"{value:,.0f}")

def build_month_report(ym: str) -> bytes:
    font_name = _register_font()
    start, end = month_range(ym)
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    c.setTitle(f"Rapport RH {ym}")

    # Header
    _draw_header(c, "Rapport RH — Synthèse mensuelle", ym, font_name)

    # KPIs rapides
    users_cnt = db.session.query(User).filter(User.is_active==True).count()
    presences = db.session.query(Attendance).filter(Attendance.work_date>=start, Attendance.work_date<=end, Attendance.check_in.isnot(None)).count()
    total_hours = db.session.query(db.func.sum(Attendance.total_hours)).filter(Attendance.work_date>=start, Attendance.work_date<=end).scalar() or 0
    ot_hours = db.session.query(db.func.sum(Overtime.hours)).filter(Overtime.work_date>=start, Overtime.work_date<=end, Overtime.status==RequestStatus.APPROVED).scalar() or 0
    leave_days = 0
    leaves = db.session.query(Leave).filter(Leave.start_date<=end, Leave.end_date>=start, Leave.status==LeaveStatus.APPROVED).all()
    from datetime import timedelta
    import math
    for l in leaves:
        d0 = max(l.start_date, start)
        d1 = min(l.end_date, end)
        cur = d0
        while cur <= d1:
            if cur.weekday() < 5:
                leave_days += 1
            cur += timedelta(days=1)

    _para(c, f"Employés actifs: {users_cnt}", 20, 264, font_name, 11)
    _para(c, f"Pointages (check-in): {presences}", 20, 256, font_name, 11)
    _para(c, f"Heures totales (mois): {total_hours:.2f} h", 20, 248, font_name, 11)
    _para(c, f"Heures sup approuvées: {ot_hours:.2f} h", 20, 240, font_name, 11)
    _para(c, f"Jours de congés approuvés: {leave_days}", 20, 232, font_name, 11)

    # Employé du mois (top 3)
    scores = compute_month_scores(ym)
    _para(c, "Employé du mois (Top 3)", 20, 222, font_name, 12)
    top_rows = []
    for i, s in enumerate(scores[:3]):
        top_rows.append((i+1, s.full_name, f"{s.present_days}/{s.workdays}", f"{s.total_hours:.1f}", f"{s.overtime_hours:.1f}", f"{s.leave_days:.0f}", f"{s.score:.3f}"))
    y_after = _table(c, ["#", "Employé", "Présence", "Heures", "H. sup", "Congés", "Score"],
                     top_rows, 20, 215, [8, 52, 28, 22, 22, 18, 20], font_name)

    # Coûts par département — tableau + mini bar chart
    _para(c, "Coûts RH par département", 20, y_after-6, font_name, 12)
    costs = department_costs(ym)  # list of dicts with 'department' and 'cost'
    rows = [(d["department"], int(d["cost"])) for d in costs]
    y_after2 = _table(c, ["Département", "Coût"], rows[:12], 20, y_after-12, [70, 25], font_name)

    # Chart (droite)
    chart_data = rows[:8]
    _bar_chart(c, chart_data, 115, 120, 80, 90, font_name)

    # Footer
    c.setFillColor(colors.grey)
    c.setFont(font_name, 8)
    c.drawRightString(200*mm, 12*mm, "RH Platform — Rapport PDF")
    c.setFillColor(colors.black)

    c.showPage()
    c.save()
    buf.seek(0)
    return buf.read()
