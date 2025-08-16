
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Dict, List, Tuple
from sqlalchemy import func, and_, distinct
from ..extensions import db
from ..models.user import User
from ..models.leave import Leave
from ..models.overtime import Overtime
from ..models.enums import LeaveStatus, RequestStatus
from ..models.attendance import Attendance
from ..models.settings import AppSetting
from ..models.award import Award

DEFAULT_WEIGHTS = {
    "presence": 0.5,
    "hours": 0.3,
    "overtime": 0.1,
    "leaves": -0.1,
}

@dataclass
class ScoreRow:
    user_id: int
    full_name: str
    present_days: int
    workdays: int
    presence_rate: float
    total_hours: float
    overtime_hours: float
    leave_days: float
    score: float

def month_range(ym: str) -> Tuple[date, date]:
    y, m = map(int, ym.split("-"))
    start = date(y, m, 1)
    end = date(y+1, 1, 1) - timedelta(days=1) if m == 12 else date(y, m+1, 1) - timedelta(days=1)
    return start, end

def business_days(start: date, end: date) -> List[date]:
    days = []
    d = start
    while d <= end:
        if d.weekday() < 5:
            days.append(d)
        d += timedelta(days=1)
    return days

def get_weights() -> Dict[str, float]:
    cfg = AppSetting.get("award_weights", None)
    if not cfg:
        return DEFAULT_WEIGHTS.copy()
    w = DEFAULT_WEIGHTS.copy()
    w.update({k: float(v) for k, v in cfg.items() if k in w})
    return w

def set_weights(new_weights: Dict[str, float]) -> Dict[str, float]:
    w = get_weights()
    w.update({k: float(v) for k, v in new_weights.items() if k in w})
    AppSetting.set("award_weights", w)
    return w

def compute_month_scores(ym: str) -> List[ScoreRow]:
    start, end = month_range(ym)
    workdays = business_days(start, end)
    wd_count = len(workdays)
    if wd_count == 0:
        return []

    present_q = (
        db.session.query(Attendance.user_id, func.count(distinct(Attendance.work_date)))
        .filter(and_(Attendance.work_date >= start, Attendance.work_date <= end, Attendance.check_in.isnot(None)))
        .group_by(Attendance.user_id)
        .all()
    )
    present_map = {uid: cnt for uid, cnt in present_q}

    hours_q = (
        db.session.query(Attendance.user_id, func.sum(Attendance.total_hours))
        .filter(and_(Attendance.work_date >= start, Attendance.work_date <= end))
        .group_by(Attendance.user_id)
        .all()
    )
    hours_map = {uid: float(h or 0) for uid, h in hours_q}

    ot_q = (
        db.session.query(Overtime.user_id, func.sum(Overtime.hours))
        .filter(and_(Overtime.work_date >= start, Overtime.work_date <= end, Overtime.status == RequestStatus.APPROVED))
        .group_by(Overtime.user_id)
        .all()
    )
    ot_map = {uid: float(h or 0) for uid, h in ot_q}

    leave_rows = (
        db.session.query(Leave.user_id, Leave.start_date, Leave.end_date)
        .filter(and_(Leave.start_date <= end, Leave.end_date >= start, Leave.status == LeaveStatus.APPROVED))
        .all()
    )
    leave_days_map = defaultdict(float)
    wd_set = set(workdays)
    for uid, s, e in leave_rows:
        d = max(s, start)
        last = min(e, end)
        cur = d
        while cur <= last:
            if cur in wd_set:
                leave_days_map[uid] += 1.0
            cur += timedelta(days=1)

    users = db.session.query(User).filter(User.is_active == True).all()
    max_hours = max([hours_map.get(u.id, 0.0) for u in users] + [1.0])
    max_ot = max([ot_map.get(u.id, 0.0) for u in users] + [1.0])
    w = get_weights()

    results: List[ScoreRow] = []
    for u in users:
        p = int(present_map.get(u.id, 0))
        presence_rate = (p / wd_count) if wd_count else 0.0
        th = float(hours_map.get(u.id, 0.0))
        oth = float(ot_map.get(u.id, 0.0))
        ld = float(leave_days_map.get(u.id, 0.0))

        nh = th / max_hours if max_hours else 0.0
        noth = oth / max_ot if max_ot else 0.0

        score = (
            presence_rate * w["presence"] +
            nh * w["hours"] +
            noth * w["overtime"] +
            (ld / max(1.0, wd_count)) * w["leaves"]
        )
        results.append(ScoreRow(
            user_id=u.id, full_name=u.full_name,
            present_days=p, workdays=wd_count, presence_rate=presence_rate,
            total_hours=th, overtime_hours=oth, leave_days=ld, score=score
        ))
    results.sort(key=lambda r: r.score, reverse=True)
    return results

def pick_winner(ym: str) -> Award | None:
    scores = compute_month_scores(ym)
    if not scores:
        return None
    top = scores[0]
    existing = Award.query.filter_by(month=ym).first()
    details = {
        "present_days": top.present_days,
        "workdays": top.workdays,
        "presence_rate": top.presence_rate,
        "total_hours": top.total_hours,
        "overtime_hours": top.overtime_hours,
        "leave_days": top.leave_days
    }
    if existing:
        existing.user_id = top.user_id
        existing.score = float(top.score)
        existing.details = details
        db.session.commit()
        return existing
    a = Award(month=ym, user_id=top.user_id, score=float(top.score), details=details)
    db.session.add(a)
    db.session.commit()
    return a
