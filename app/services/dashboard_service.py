from datetime import date
from sqlalchemy import func
from app import db
from app.models.employee_of_month import EmployeeOfMonth

class DashboardService:
    @staticmethod
    def _employee_of_month_dict():
        period = db.session.query(func.max(EmployeeOfMonth.period)).scalar()
        if not period:
            return None
        e = (db.session.query(EmployeeOfMonth)
             .filter(EmployeeOfMonth.period == period)
             .join(EmployeeOfMonth.user)
             .first())
        if not e:
            return None
        full_name = f"{e.user.first_name} {e.user.last_name}".strip() or e.user.email
        return {
            "name": full_name,
            "department": getattr(getattr(e.user, "department", None), "name", None),
            "period_label": e.period.strftime("%B %Y").capitalize()
        }

    @staticmethod
    def global_overview(user_id=None):
        data = {}
        data["employee_of_month"] = DashboardService._employee_of_month_dict()
        return data
