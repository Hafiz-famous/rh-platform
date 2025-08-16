
from datetime import date
from flask import Blueprint, render_template
from flask_login import login_required
from sqlalchemy import func
from ..extensions import db
from ..models.user import User
from ..models.department import Department
from ..models.attendance import Attendance

bp = Blueprint("dashboard", __name__, url_prefix="/")

@bp.get("/")
@login_required
def index():
    today = date.today()
    total_users = db.session.query(func.count(User.id)).scalar() or 0
    total_departments = db.session.query(func.count(Department.id)).scalar() or 0
    todays_att = (
        db.session.query(func.count(Attendance.id))
        .filter(Attendance.work_date == today)
        .scalar() or 0
    )
    return render_template("dashboard/index.html",
                           stats=dict(users=total_users, depts=total_departments, today=todays_att),
                           today=today)
