# app/services/cost_service.py
from datetime import date
from sqlalchemy import func, and_
from app.extensions import db
from app.models.department import Department
from app.models.user import User
from app.models.attendance import Attendance

def department_costs(ym: str | None = None):
    """
    Calcule coût par département = SUM(attendance.total_hours * user.hourly_rate)
    pour le mois 'YYYY-MM'. Retourne aussi les départements sans données avec coût = 0.
    """
    if not ym:
        ym = date.today().strftime("%Y-%m")

    dialect = db.engine.dialect.name  # 'sqlite', 'postgresql', ...
    if dialect == "sqlite":
        month_expr = func.strftime("%Y-%m", Attendance.work_date)
    else:
        month_expr = func.to_char(Attendance.work_date, "YYYY-MM")

    # point de départ = Department (pour les inclure tous)
    q = (
        db.session.query(
            Department.name.label("department"),
            func.coalesce(
                func.sum(
                    func.coalesce(Attendance.total_hours, 0.0)
                    * func.coalesce(User.hourly_rate, 0.0)
                ),
                0.0,
            ).label("cost"),
        )
        .outerjoin(User, User.department_id == Department.id)
        # IMPORTANT: filtre de mois DANS la condition de jointure, pas dans WHERE
        .outerjoin(
            Attendance,
            and_(Attendance.user_id == User.id, month_expr == ym),
        )
        .group_by(Department.name)
        .order_by(Department.name.asc())
    )

    return [{"department": d, "cost": float(c or 0.0)} for d, c in q.all()]
