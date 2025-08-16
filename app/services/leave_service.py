
from datetime import datetime
from ..extensions import db
from ..models.leave import Leave
from ..models.enums import LeaveStatus

def request_leave(user_id: int, lv_type, start_date, end_date, reason: str | None):
    lv = Leave(user_id=user_id, type=lv_type, start_date=start_date, end_date=end_date, reason=reason)
    db.session.add(lv)
    db.session.commit()
    return lv

def update_status(leave_id: int, status: LeaveStatus):
    lv = Leave.query.get_or_404(leave_id)
    lv.status = status
    lv.updated_at = datetime.utcnow()
    db.session.commit()
    return lv
