# services/overtime_auto.py
from datetime import datetime, date, time, timedelta
from sqlalchemy import and_, or_, func
from ..extensions import db
from ..models.overtime import Overtime
from ..models.enums import RequestStatus, OvertimeSource
from ..models.schedule import WorkSchedule, Holiday
from ..models.attendance import Attendance  # adapte l'import au tien

ROUND_STEP = 0.25  # heures, arrondi au 1/4 d’heure
COUNT_WEEKENDS_AS_OT = True   # optionnel: tout travail le weekend = heures sup
COUNT_HOLIDAYS_AS_OT = True   # optionnel: tout travail les jours fériés = heures sup

def _hours(td: timedelta) -> float:
    return max(td.total_seconds(), 0) / 3600.0

def _round_down_quarter(h: float) -> float:
    # Arrondi par défaut vers le bas au 1/4 d'heure (0.25)
    return (int(h / ROUND_STEP)) * ROUND_STEP

def planned_hours_for(user_id: int, d: date) -> float:
    # weekend
    if d.weekday() >= 5:  # 5=Sam, 6=Dim
        return 0.0 if (COUNT_WEEKENDS_AS_OT or True) else 0.0  # base 0, tout travail au-delà compte OT
    # férié
    if Holiday.query.get(d):
        return 0.0 if COUNT_HOLIDAYS_AS_OT else 0.0

    ws = WorkSchedule.query.filter_by(user_id=user_id, weekday=d.weekday()).first()
    if not ws:
        return 0.0
    start_dt = datetime.combine(d, ws.start_time)
    end_dt   = datetime.combine(d, ws.end_time)
    if end_dt < start_dt:
        end_dt += timedelta(days=1)  # shift qui dépasse minuit
    planned = _hours(end_dt - start_dt) - (ws.break_minutes or 0)/60.0
    return max(planned, 0.0)

def worked_hours_for(user_id: int, d: date) -> float:
    # Récupère tous les tronçons de pointage qui touchent le jour d
    day_start = datetime.combine(d, time.min)
    day_end   = datetime.combine(d, time.max)
    q = Attendance.query.filter(
        Attendance.user_id == user_id,
        or_(
            and_(Attendance.check_in  >= day_start, Attendance.check_in  <= day_end),
            and_(Attendance.check_out >= day_start, Attendance.check_out <= day_end),
            and_(Attendance.check_in  <= day_start, Attendance.check_out >= day_end),
        )
    )
    total = 0.0
    for a in q:
        ci = max(a.check_in,  day_start)
        co = min(a.check_out or datetime.utcnow(), day_end)
        if co > ci:
            total += _hours(co - ci)
    return total

def compute_overtime_for_user_day(user_id: int, d: date) -> Overtime | None:
    worked = worked_hours_for(user_id, d)
    planned = planned_hours_for(user_id, d)

    # Règles :
    # - jours fériés/weekends: toutes les heures = OT (planned = 0)
    # - jours ouvrés: max(0, worked - planned)
    ot_hours_raw = worked - planned
    # si jour férié/weekend, planned vaut 0 => ot_hours_raw = worked
    ot_hours = _round_down_quarter(max(0.0, ot_hours_raw))

    # Upsert la ligne AUTO
    ot = Overtime.query.filter_by(user_id=user_id, work_date=d, source=OvertimeSource.AUTO).first()
    if not ot:
        if ot_hours <= 0:  # rien à créer
            return None
        ot = Overtime(user_id=user_id, work_date=d, source=OvertimeSource.AUTO)

    if ot_hours <= 0:
        # plus d'OT pour ce jour: supprime la ligne auto si elle existait
        if ot.id:
            db.session.delete(ot)
            db.session.commit()
        return None

    ot.hours = ot_hours
    ot.status = RequestStatus.PENDING   # ou APPROVED si tu veux auto-valider
    ot.calc_note = f"Auto: worked={worked:.2f}h, planned={planned:.2f}h, ot={ot_hours:.2f}h"
    ot.last_computed_at = datetime.utcnow()
    db.session.add(ot)
    db.session.commit()
    return ot

def compute_overtime_for_range(user_id: int, start: date, end: date):
    cur = start
    out = []
    while cur <= end:
        out.append(compute_overtime_for_user_day(user_id, cur))
        cur += timedelta(days=1)
    return out
