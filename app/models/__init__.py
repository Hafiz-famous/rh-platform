# app/models/__init__.py
from app.extensions import db

# Importer les modèles ici pour qu'ils soient enregistrés auprès de SQLAlchemy
from .department import Department
from .user import User
from .attendance import Attendance
# (optionnel) si tu as ces fichiers :
# from .salary_cost import SalaryCost
# from .performance import Performance
# from .employee_of_month import EmployeeOfMonth
# from .leave_request import LeaveRequest

__all__ = [
    "db",
    "Department",
    "User",
    "Attendance",
    # "SalaryCost", "Performance", "EmployeeOfMonth", "LeaveRequest",
]
