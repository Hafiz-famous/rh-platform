from app.extensions import db

from .department import Department
from .user import User
from .attendance import Attendance
from .employee_of_month import EmployeeOfMonth   # <— IMPORTANT

__all__ = ["db", "Department", "User", "Attendance", "EmployeeOfMonth"]
