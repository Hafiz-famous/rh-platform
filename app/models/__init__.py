# app/models/__init__.py

# --- Imports stricts (présents dans ton projet) ---
from .user import User, Role               # Role doit exister dans user.py (Enum/Model)
from .department import Department
from .attendance import Attendance

# --- Imports tolérants / optionnels (selon tes noms de classes/fichiers) ---

# Leave / LeaveRequest
LeaveRequest = None
try:
    from .leave import LeaveRequest as _LV
    LeaveRequest = _LV
except Exception:
    try:
        from .leave import Leave as _LV
        LeaveRequest = _LV
    except Exception:
        try:
            from .leave import LeaveApplication as _LV
            LeaveRequest = _LV
        except Exception:
            try:
                from .leave import LeaveRecord as _LV
                LeaveRequest = _LV
            except Exception:
                LeaveRequest = None  # pas de module de congés détecté

# Overtime / ExtraHours
Overtime = None
try:
    from .overtime import Overtime as _OT
    Overtime = _OT
except Exception:
    try:
        from .overtime import OvertimeRequest as _OT
        Overtime = _OT
    except Exception:
        try:
            from .extra_hours import ExtraHours as _OT
            Overtime = _OT
        except Exception:
            Overtime = None  # pas de module d'heures sup détecté

# Award (facultatif)
try:
    from .award import Award
except Exception:
    Award = None

# --- Construction de __all__ dynamique ---
__all__ = [
    "User",
    "Role",
    "Department",
    "Attendance",
]

if LeaveRequest is not None:
    __all__.append("LeaveRequest")
if Overtime is not None:
    __all__.append("Overtime")
if Award is not None:
    __all__.append("Award")
