# app/services/leave_service.py
from __future__ import annotations

from datetime import datetime, date
from typing import Optional, Union

from werkzeug.exceptions import BadRequest, NotFound

from ..extensions import db
from ..models.leave import Leave
from ..models.enums import LeaveStatus, LeaveType


# --- Normalisation du type de congé vers les valeurs attendues par LeaveType ---
_ALIAS_TYPE = {
    # annual
    "annuel": "annual",
    "annual leave": "annual",
    "conge": "annual",
    "congé": "annual",
    "conges": "annual",
    "congés": "annual",
    # sick
    "maladie": "sick",
    "sickness": "sick",
    # maternity / paternity
    "maternite": "maternity",
    "maternité": "maternity",
    "paternite": "paternity",
    "paternité": "paternity",
    # unpaid
    "sans solde": "unpaid",
    "sans_solde": "unpaid",
    # other
    "autre": "other",
}


def _coerce_leave_type(v: Union[str, LeaveType]) -> LeaveType:
    """Accepte un str (FR/EN) ou LeaveType, retourne un LeaveType valide."""
    if isinstance(v, LeaveType):
        return v
    if isinstance(v, str):
        s = v.strip()
        if not s:
            raise BadRequest("Type de congé requis.")
        s_low = s.lower()
        s_norm = _ALIAS_TYPE.get(s_low, s_low)  # mappe alias FR -> EN
        try:
            return LeaveType(s_norm)
        except Exception:
            pass
    raise BadRequest(f"Type de congé invalide: {v!r}")


def _coerce_status(v: Union[str, LeaveStatus]) -> LeaveStatus:
    """Accepte un str ou LeaveStatus, retourne un LeaveStatus valide."""
    if isinstance(v, LeaveStatus):
        return v
    if isinstance(v, str):
        s = v.strip().lower()
        try:
            return LeaveStatus(s)
        except Exception:
            pass
    raise BadRequest(f"Statut de congé invalide: {v!r}")


def request_leave(
    user_id: int,
    lv_type: Union[str, LeaveType],
    start_date: date,
    end_date: date,
    reason: Optional[str] = None,
) -> Leave:
    """Crée une demande de congé (statut PENDING) après validation des dates/type."""
    if start_date > end_date:
        raise BadRequest("La date de début doit être antérieure ou égale à la date de fin.")

    lv = Leave(
        user_id=user_id,
        type=_coerce_leave_type(lv_type),
        start_date=start_date,
        end_date=end_date,
        reason=reason,
        status=LeaveStatus.PENDING,
        updated_at=datetime.utcnow(),
    )
    db.session.add(lv)
    db.session.commit()
    return lv


def update_status(
    leave_id: int,
    status: Union[str, LeaveStatus],
    actor_user_id: Optional[int] = None,
) -> Leave:
    """Met à jour le statut; renseigne les champs d'audit si présents."""
    lv = db.session.get(Leave, leave_id)
    if not lv:
        raise NotFound("Demande de congé introuvable.")

    new_status = _coerce_status(status)

    # Règles simples de non-régression (à ajuster selon vos besoins)
    if lv.status == LeaveStatus.APPROVED and new_status != LeaveStatus.APPROVED:
        raise BadRequest("La demande approuvée ne peut plus être modifiée.")
    if lv.status == LeaveStatus.REJECTED and new_status != LeaveStatus.REJECTED:
        raise BadRequest("La demande rejetée ne peut plus être modifiée.")

    lv.status = new_status
    lv.updated_at = datetime.utcnow()

    # Champs d'audit si présents dans le modèle / la base
    if hasattr(lv, "validated_by_id"):
        lv.validated_by_id = actor_user_id
    if hasattr(lv, "validated_at"):
        lv.validated_at = datetime.utcnow()

    db.session.commit()
    return lv
