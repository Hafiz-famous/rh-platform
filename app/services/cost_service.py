# app/services/cost_service.py

from sqlalchemy import func
from app.models import db, Department, User, Attendance  # adapte les import selon ton projet

def department_costs(ym: str):
    """
    ym au format 'YYYY-MM', ex: '2025-08'
    Calcule le coût par département = somme(total_hours * hourly_rate)
    pour le mois donné.
    """

    dialect = db.engine.dialect.name  # 'sqlite', 'postgresql', ...
    if dialect == 'sqlite':
        # SQLite : strftime('%Y-%m', column)
        month_expr = func.strftime('%Y-%m', Attendance.work_date)
    else:
        # Postgres (et compatibles) : to_char(column, 'YYYY-MM')
        month_expr = func.to_char(Attendance.work_date, 'YYYY-MM')

    q = (
        db.session.query(
            Department.name.label('department'),
            func.sum(
                func.coalesce(Attendance.total_hours, 0) * func.coalesce(User.hourly_rate, 0)
            ).label('cost'),
        )
        .join(User, User.department_id == Department.id)
        .join(Attendance, Attendance.user_id == User.id)
        .filter(month_expr == ym)
        .group_by(Department.name)
    )

    return [{"department": d, "cost": float(c or 0)} for d, c in q.all()]
