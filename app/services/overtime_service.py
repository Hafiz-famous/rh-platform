
from ..extensions import db
from ..models.overtime import Overtime
from ..models.enums import RequestStatus

def declare_overtime(user_id: int, work_date, hours: float, note: str | None):
    ot = Overtime(user_id=user_id, work_date=work_date, hours=hours, note=note)
    db.session.add(ot)
    db.session.commit()
    return ot

def set_status(ot_id: int, status: RequestStatus):
    ot = Overtime.query.get_or_404(ot_id)
    ot.status = status
    db.session.commit()
    return ot
