
from datetime import date
from app.extensions import db
from app.models.user import User
from app.models.department import Department
from app.models.attendance import Attendance
from app.models.overtime import Overtime
from app.models.leave import Leave
from app.models.enums import Role, RequestStatus, LeaveStatus
from app.services.award_service import compute_month_scores, set_weights

def test_award_scoring_basic(app):
    with app.app_context():
        d = Department(name="IT")
        db.session.add(d)
        u1 = User(email="a@x", first_name="A", last_name="One", role=Role.EMPLOYEE, department=d); u1.set_password("x")
        u2 = User(email="b@x", first_name="B", last_name="Two", role=Role.EMPLOYEE, department=d); u2.set_password("x")
        db.session.add_all([u1,u2]); db.session.commit()

        ym = date.today().strftime("%Y-%m")
        y, m = map(int, ym.split("-"))

        for day in range(1, 6):
            work_date = date(y,m,day)
            db.session.add(Attendance(user_id=u1.id, work_date=work_date, check_in="08:00", check_out="17:00", total_hours=9.0))
        for day in range(1, 4):
            work_date = date(y,m,day)
            db.session.add(Attendance(user_id=u2.id, work_date=work_date, check_in="09:00", check_out="17:00", total_hours=8.0))

        db.session.add(Overtime(user_id=u1.id, work_date=date(y,m,2), hours=2.0, status=RequestStatus.APPROVED))
        db.session.add(Leave(user_id=u2.id, start_date=date(y,m,3), end_date=date(y,m,4), status=LeaveStatus.APPROVED, type=None))

        db.session.commit()

        set_weights({"presence":0.5, "hours":0.3, "overtime":0.2, "leaves":-0.1})
        rows = compute_month_scores(ym)
        assert len(rows) >= 2
        assert rows[0].user_id == u1.id
