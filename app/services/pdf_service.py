# app/services/pdf_service.py
from io import BytesIO
from datetime import datetime, date, timedelta
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
from ..services.award_service import compute_month_scores, month_range


# ---------------- UI helpers ----------------
def _register_font() -> str:
    """Essaie DejaVu pour les accents, sinon Helvetica."""
    try:
        pdfmetrics.registerFont(TTFont("DejaVu", "DejaVuSans.ttf"))
        return "DejaVu"
    except Exception:
        return "Helvetica"


def _draw_header(c: canvas.Canvas, title: str, ym: str, font_name: str):
    c.setFont(font_name, 18)
    c.drawString(20 * mm, 280 * mm, title)
    c.setFont(font_name, 10)
    c.setFillColor(colors.grey)
    c.drawString(
        20 * mm,
        274 * mm,
        f"Mois: {ym}   Généré: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
    )
    c.setFillColor(colors.black)
    c.line(20 * mm, 272 * mm, 190 * mm, 272 * mm)


def _para(
    c: canvas.Canvas, text: str, x_mm: float, y_mm: float, font_name: str, size: int = 10
):
    c.setFont(font_name, size)
    c.drawString(x_mm * mm, y_mm * mm, text)


def _table(
    c: canvas.Canvas,
    headers: List[str],
    rows: List[Tuple],
    x_mm: float,
    y_mm: float,
    col_w_mm: List[float],
    font_name: str,
) -> float:
    """Dessine un petit tableau. Retourne la nouvelle position Y (en mm) juste sous le tableau."""
    c.setFont(font_name, 10)
    y = y_mm * mm
    x = x_mm * mm
    h = 6 * mm

    # Header
    c.setFillColor(colors.lightgrey)
    c.rect(x, y, sum(col_w_mm) * mm, h, fill=True, stroke=False)
    c.setFillColor(colors.black)
    cx = x
    for i, head in enumerate(headers):
        c.drawString(cx + 2 * mm, y + 2 * mm, str(head))
        cx += col_w_mm[i] * mm
    y -= h

    # Rows
    for r in rows:
        cx = x
        for i in range(len(headers)):
            val = r[i] if i < len(r) else ""
            c.drawString(cx + 2 * mm, y + 2 * mm, str(val))
            cx += col_w_mm[i] * mm
        y -= h

    return y / mm


def _bar_chart(
    c: canvas.Canvas,
    data: List[Tuple[str, float]],
    x_mm: float,
    y_mm: float,
    w_mm: float,
    h_mm: float,
    font_name: str,
):
    """Mini bar chart horizontal (coûts par département)."""
    x = x_mm * mm
    y = y_mm * mm
    w = w_mm * mm
    h = h_mm * mm

    # cadre
    c.setStrokeColor(colors.black)
    c.rect(x, y, w, h, fill=False, stroke=True)

    if not data:
        return

    maxv = max(float(v or 0) for _, v in data) or 1.0
    bar_h = h / max(1, len(data))
    for idx, (label, value) in enumerate(data):
        value = float(value or 0)
        bh = bar_h * 0.7
        by = y + h - (idx + 1) * bar_h + (bar_h - bh) / 2
        bw = (value / maxv) * (w - 30 * mm)

        # barre + étiquettes
        c.setFillColor(colors.darkblue)
        c.rect(x + 25 * mm, by, bw, bh, fill=True, stroke=False)
        c.setFillColor(colors.black)
        c.setFont(font_name, 9)
        c.drawRightString(x + 23 * mm, by + bh / 2 - 2, (label or "")[:18])
        c.drawString(x + 26 * mm + bw, by + bh / 2 - 2, f"{value:,.0f}")


# ---------------- Report builder ----------------
def build_month_report(ym: str) -> bytes:
    font_name = _register_font()
    start, end = month_range(ym)

    # Champs tolérants au schéma
    att_date_col = getattr(Attendance, "work_date", None) or getattr(Attendance, "date", None)
    ot_date_col  = getattr(Overtime,   "work_date", None) or getattr(Overtime,   "date", None)
    # total_hours ou hours
    att_hours_col = getattr(Attendance, "total_hours", None) or getattr(Attendance, "hours", None)

    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    c.setTitle(f"Rapport RH {ym}")

    # Header
    _draw_header(c, "Rapport RH — Synthèse mensuelle", ym, font_name)

    # ---- KPIs rapides (tolérance nom de colonnes) ----
    users_cnt = db.session.query(User).filter(User.is_active == True).count()

    presences_q = db.session.query(Attendance)
    if att_date_col is not None:
        presences_q = presences_q.filter(att_date_col >= start, att_date_col <= end)
    presences = presences_q.filter(Attendance.check_in.isnot(None)).count()

    total_hours_q = db.session.query(db.func.coalesce(db.func.sum(att_hours_col), 0.0))
    if att_date_col is not None:
        total_hours_q = total_hours_q.filter(att_date_col >= start, att_date_col <= end)
    total_hours = float(total_hours_q.scalar() or 0.0)

    ot_hours_q = db.session.query(db.func.coalesce(db.func.sum(Overtime.hours), 0.0))
    if ot_date_col is not None:
        ot_hours_q = ot_hours_q.filter(ot_date_col >= start, ot_date_col <= end)
    ot_hours = float(
        ot_hours_q.filter(Overtime.status == RequestStatus.APPROVED).scalar() or 0.0
    )

    # Jours de congés ouvrés approuvés
    leave_days = 0
    leaves = (
        db.session.query(Leave)
        .filter(Leave.start_date <= end, Leave.end_date >= start, Leave.status == LeaveStatus.APPROVED)
        .all()
    )
    for l in leaves:
        d0 = max(l.start_date, start)
        d1 = min(l.end_date, end)
        cur = d0
        while cur <= d1:
            if cur.weekday() < 5:  # lun-ven
                leave_days += 1
            cur += timedelta(days=1)

    _para(c, f"Employés actifs: {users_cnt}", 20, 264, font_name, 11)
    _para(c, f"Pointages (check-in): {presences}", 20, 256, font_name, 11)
    _para(c, f"Heures totales (mois): {total_hours:.2f} h", 20, 248, font_name, 11)
    _para(c, f"Heures sup approuvées: {ot_hours:.2f} h", 20, 240, font_name, 11)
    _para(c, f"Jours de congés approuvés: {leave_days}", 20, 232, font_name, 11)

    # ---- Employé·e du mois (Top 3) ----
    scores = compute_month_scores(ym) or []
    _para(c, "Employé·e du mois (Top 3)", 20, 222, font_name, 12)

    top_rows: List[Tuple] = []
    for i, s in enumerate(scores[:3]):
        top_rows.append(
            (
                i + 1,
                getattr(s, "full_name", "") or getattr(s, "name", ""),
                f"{getattr(s, 'present_days', 0)}/{getattr(s, 'workdays', 0)}",
                f"{getattr(s, 'total_hours', 0.0):.1f}",
                f"{getattr(s, 'overtime_hours', 0.0):.1f}",
                f"{getattr(s, 'leave_days', 0):.0f}",
                f"{getattr(s, 'score', 0.0):.3f}",
            )
        )

    y_after_top = _table(
        c,
        ["#", "Employé", "Présence", "Heures", "H. sup", "Congés", "Score"],
        top_rows,
        20,
        215,
        [8, 52, 28, 22, 22, 18, 20],
        font_name,
    )

    # ---- Coûts par département (table + graphe sans chevauchement) ----
    _para(c, "Coûts RH par département", 20, y_after_top - 6, font_name, 12)
    costs = department_costs(ym) or []  # [{'department':..., 'cost':...}]
    rows = [(str(d.get("department", "")), float(d.get("cost", 0))) for d in costs]

    y_after_costs = _table(
        c,
        ["Département", "Coût"],
        [(d, int(v)) for d, v in rows[:12]],
        20,
        y_after_top - 12,
        [70, 25],
        font_name,
    )

    # Place le graphe à droite SANS chevauchement : son haut ne doit pas monter au-dessus
    # du plus bas des deux tableaux.
    chart_w, chart_h = 80, 90  # mm
    top_limit = min(215, y_after_costs)  # zone sûre sous les tables
    y_chart = max(30, top_limit - chart_h - 4)  # bas de page min 30mm
    _bar_chart(c, rows[:8], 115, y_chart, chart_w, chart_h, font_name)

    # Footer
    c.setFillColor(colors.grey)
    c.setFont(font_name, 8)
    c.drawRightString(200 * mm, 12 * mm, "RH Platform — Rapport PDF")
    c.setFillColor(colors.black)

    c.showPage()
    c.save()
    buf.seek(0)
    return buf.read()
