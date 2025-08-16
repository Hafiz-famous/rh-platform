from __future__ import annotations

from datetime import datetime, date
from typing import Optional

from sqlalchemy import (
    Integer, Date, DateTime, Float, String, ForeignKey, CheckConstraint
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db


class Attendance(db.Model):
    __tablename__ = "attendances"
    __table_args__ = (
        # Un enregistrement par salarié et par jour
        db.UniqueConstraint("user_id", "work_date", name="uq_attendance_user_day"),
        # Index utile pour les recherches / agrégations
        db.Index("ix_att_user_date", "user_id", "work_date"),
        # Valeurs autorisées pour la source (optionnel)
        CheckConstraint("source IN ('qr','manual') OR source IS NULL", name="ck_att_source_valid"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    work_date: Mapped[date] = mapped_column(Date, index=True, nullable=False)

    check_in: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    check_out: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    late_minutes: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    total_hours: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    source: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # 'qr' | 'manual'
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="attendances")
