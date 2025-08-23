from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Dict, List, Tuple, Optional

from sqlalchemy import func, and_, distinct, select, text, inspect

from ..extensions import db
from ..models.user import User
from ..models.leave import Leave
from ..models.overtime import Overtime
from ..models.enums import LeaveStatus, RequestStatus
from ..models.attendance import Attendance
from ..models.settings import AppSetting
from ..models.award import Award


# -------------------------------
# Poids par défaut (modifiable via AppSetting "award_weights")
# -------------------------------
DEFAULT_WEIGHTS: Dict[str, float] = {
    "presence": 0.5,   # taux de présence (jours présents / jours ouvrés)
    "hours":    0.3,   # heures de travail totales
    "overtime": 0.1,   # heures supplémentaires approuvées
    "leaves":  -0.1,   # pénalité proportionnelle aux jours de congé approuvés
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


# -------------------------------
# Utilitaires de période
# -------------------------------
def month_range(ym: str) -> Tuple[date, date]:
    y, m = map(int, ym.split("-"))
    start = date(y, m, 1)
    if m == 12:
        end = date(y + 1, 1, 1) - timedelta(days=1)
    else:
        end = date(y, m + 1, 1) - timedelta(days=1)
    return start, end


def business_days(start: date, end: date) -> List[date]:
    days: List[date] = []
    cur = start
    while cur <= end:
        if cur.weekday() < 5:  # 0=Mon .. 4=Fri
            days.append(cur)
        cur += timedelta(days=1)
    return days


# -------------------------------
# Poids configurables
# -------------------------------
def get_weights() -> Dict[str, float]:
    cfg = AppSetting.get("award_weights", None)
    if not cfg:
        return DEFAULT_WEIGHTS.copy()
    # merge sécurisé
    w = DEFAULT_WEIGHTS.copy()
    try:
        w.update({k: float(v) for k, v in dict(cfg).items() if k in w})
    except Exception:
        pass
    return w


def set_weights(new_weights: Dict[str, float]) -> Dict[str, float]:
    w = get_weights()
    w.update({k: float(v) for k, v in new_weights.items() if k in w})
    AppSetting.set("award_weights", w)
    return w


# -------------------------------
# Calcul des scores mensuels
# -------------------------------
def compute_month_scores(ym: str) -> List[ScoreRow]:
    start, end = month_range(ym)
    workdays = business_days(start, end)
    wd_count = len(workdays)
    if wd_count == 0:
        return []

    # Présence: nb de jours distincts avec check_in
    present_rows = db.session.execute(
        select(Attendance.user_id, func.count(distinct(Attendance.work_date)))
        .where(
            and_(
                Attendance.work_date >= start,
                Attendance.work_date <= end,
                Attendance.check_in.isnot(None),
            )
        )
        .group_by(Attendance.user_id)
    ).all()
    present_map = {uid: int(cnt or 0) for uid, cnt in present_rows}

    # Heures totales pointées
    hours_rows = db.session.execute(
        select(Attendance.user_id, func.sum(Attendance.total_hours))
        .where(and_(Attendance.work_date >= start, Attendance.work_date <= end))
        .group_by(Attendance.user_id)
    ).all()
    hours_map = {uid: float(h or 0.0) for uid, h in hours_rows}

    # Heures supplémentaires approuvées
    ot_rows = db.session.execute(
        select(Overtime.user_id, func.sum(Overtime.hours))
        .where(
            and_(
                Overtime.work_date >= start,
                Overtime.work_date <= end,
                Overtime.status == RequestStatus.APPROVED,
            )
        )
        .group_by(Overtime.user_id)
    ).all()
    ot_map = {uid: float(h or 0.0) for uid, h in ot_rows}

    # Congés approuvés: compter uniquement les jours ouvrés dans l'intervalle
    leave_rows = db.session.execute(
        select(Leave.user_id, Leave.start_date, Leave.end_date)
        .where(
            and_(
                Leave.start_date <= end,
                Leave.end_date >= start,
                Leave.status == LeaveStatus.APPROVED,
            )
        )
    ).all()

    leave_days_map: Dict[int, float] = defaultdict(float)
    wd_set = set(workdays)
    for uid, s, e in leave_rows:
        d0 = max(s, start)
        d1 = min(e, end)
        cur = d0
        while cur <= d1:
            if cur in wd_set:
                leave_days_map[uid] += 1.0
            cur += timedelta(days=1)

    # Population: uniquement actifs
    users: List[User] = db.session.execute(
        select(User).where(User.is_active.is_(True))
    ).scalars().all()

    # Normalisations pour heures/overtime
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
            presence_rate * w["presence"]
            + nh * w["hours"]
            + noth * w["overtime"]
            + (ld / max(1.0, wd_count)) * w["leaves"]
        )

        results.append(
            ScoreRow(
                user_id=u.id,
                full_name=u.full_name,
                present_days=p,
                workdays=wd_count,
                presence_rate=presence_rate,
                total_hours=th,
                overtime_hours=oth,
                leave_days=ld,
                score=float(score),
            )
        )

    # Tri avec bris d’égalité : score desc, présence desc, heures desc, id asc
    results.sort(
        key=lambda r: (r.score, r.presence_rate, r.total_hours, -r.user_id),
        reverse=True,
    )
    return results


# -------------------------------
# EOM: choisir et enregistrer le/la gagnant·e
# -------------------------------
def pick_winner(ym: str, commit: bool = True) -> Optional[Award]:
    scores = compute_month_scores(ym)
    if not scores:
        return None
    top = scores[0]

    # Détails stockés (JSON-friendly)
    details = {
        "present_days": top.present_days,
        "workdays": top.workdays,
        "presence_rate": round(top.presence_rate, 4),
        "total_hours": round(top.total_hours, 2),
        "overtime_hours": round(top.overtime_hours, 2),
        "leave_days": round(top.leave_days, 2),
    }

    # Upsert par month
    existing: Optional[Award] = db.session.execute(
        select(Award).where(Award.month == ym)
    ).scalar_one_or_none()

    if existing:
        existing.user_id = top.user_id
        existing.score = float(top.score)
        existing.details = details
        if commit:
            db.session.commit()
        return existing

    a = Award(month=ym, user_id=top.user_id, score=float(top.score), details=details)
    db.session.add(a)
    if commit:
        db.session.commit()
    return a


# -------------------------------
# Nom pour affichage (Dashboard)
# -------------------------------
def get_employee_of_month_name(ym: Optional[str] = None) -> Optional[str]:
    """
    Retourne 'Prénom Nom' à partir de la table Award (month, user_id),
    sinon None si rien pour la période.
    """
    if ym is None:
        ym = date.today().strftime("%Y-%m")

    row = db.session.execute(
        select(User.first_name, User.last_name)
        .join(Award, Award.user_id == User.id)
        .where(Award.month == ym)
        .order_by(Award.id.desc())
        .limit(1)
    ).first()

    if not row:
        return None
    first, last = row[0], row[1]
    return f"{first} {last}".strip()
