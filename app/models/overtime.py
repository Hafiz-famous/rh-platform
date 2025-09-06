from datetime import datetime, date
import enum
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy import Integer, Date, DateTime, Float, Text, ForeignKey, Enum, UniqueConstraint
from ..extensions import db
from .enums import RequestStatus  # ton enum existant: PENDING / APPROVED / REJECTED (par ex.)

# --- Nouveaux enums pour le mode automatique ---
class OvertimeSource(str, enum.Enum):
    manual = "manual"
    auto = "auto"

class AutoState(str, enum.Enum):
    auto_approved = "auto_approved"
    needs_review = "needs_review"

class Overtime(db.Model):
    __tablename__ = "overtimes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    work_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    # Montant des heures sup déclarées/calculées (tu gardes ta colonne)
    hours: Mapped[float] = mapped_column(Float, nullable=False)

    # --- EXISTANT : statut du workflow "manuel" (ex. PENDING/APPROVED/REJECTED) ---
    status: Mapped[RequestStatus] = mapped_column(Enum(RequestStatus), default=RequestStatus.PENDING, nullable=False)

    # --- NOUVEAU : provenance et état auto ---
    # source = 'manual' (déclaration) ou 'auto' (calculée depuis le pointage)
    source: Mapped[OvertimeSource] = mapped_column(Enum(OvertimeSource), default=OvertimeSource.manual, nullable=False)
    # auto_state seulement si source='auto' : 'auto_approved' ou 'needs_review'
    auto_state: Mapped[AutoState | None] = mapped_column(Enum(AutoState), nullable=True)

    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="overtimes")

    # Unicité : un enregistrement auto PAR jour et PAR user (et idem pour manual)
    __table_args__ = (
        UniqueConstraint("user_id", "work_date", "source", name="uq_overtimes_user_date_source"),
    )
