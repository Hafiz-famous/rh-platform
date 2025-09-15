# app/models/__init__.py
from .user import User
from .department import Department
from .attendance import Attendance
# importe Overtime si tu l'as :
# from .overtime import Overtime
from .award import Award  # ✅ OK une fois award.py corrigé

__all__ = ["User", "Department", "Attendance", "Award"]  # + "Overtime" si présent
