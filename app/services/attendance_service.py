
from datetime import datetime, date, time as dt_time
from ..extensions import db
from ..models.attendance import Attendance

DEFAULT_START = dt_time(8, 0)  # 08:00

def compute_late_minutes(check_in: datetime) -> float:
    if not check_in:
        return 0.0
    scheduled = datetime.combine(check_in.date(), DEFAULT_START)
    delta = (check_in - scheduled).total_seconds() / 60.0
    return max(0.0, round(delta, 2))

def compute_total_hours(check_in: datetime, check_out: datetime) -> float:
    if check_in and check_out and check_out > check_in:
        return round((check_out - check_in).total_seconds() / 3600.0, 2)
    return 0.0

def punch_in(user_id: int, lat: float | None, lon: float | None, source="manual") -> Attendance:
    now = datetime.utcnow()
    today = date.today()
    att = Attendance.query.filter_by(user_id=user_id, work_date=today).first()
    if not att:
        att = Attendance(user_id=user_id, work_date=today)
    att.check_in = now
    att.late_minutes = compute_late_minutes(now)
    att.latitude = lat
    att.longitude = lon
    att.source = source
    db.session.add(att)
    db.session.commit()
    return att

def punch_out(user_id: int, lat: float | None, lon: float | None, source="manual") -> Attendance:
    now = datetime.utcnow()
    today = date.today()
    att = Attendance.query.filter_by(user_id=user_id, work_date=today).first()
    if not att:
        att = Attendance(user_id=user_id, work_date=today, check_in=now)
        att.late_minutes = compute_late_minutes(now)
    att.check_out = now
    att.total_hours = compute_total_hours(att.check_in, att.check_out)
    att.latitude = lat
    att.longitude = lon
    att.source = source
    db.session.add(att)
    db.session.commit()
    return att
