from __future__ import annotations

from datetime import datetime, date
from typing import Optional

from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Integer, Date, DateTime, Text, ForeignKey, CheckConstraint
from sqlalchemy import Enum as SAEnum  # éviter la confusion avec enum.Enum

from app.extensions import db
from .enums import LeaveType, LeaveStatus


class Leave(db.Model):
    __tablename__ = "leaves"
    __table_args__ = (
        # Empêche end_date < start_date
        CheckConstraint("end_date >= start_date", name="ck_leave_dates"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), index=True, nullable=False
    )

    # Enums SQLAlchemy basés sur tes Enums Python
    type: Mapped[LeaveType] = mapped_column(
        SAEnum(LeaveType, name="leave_type_enum"), nullable=False
    )
    status: Mapped[LeaveStatus] = mapped_column(
        SAEnum(LeaveStatus, name="leave_status_enum"),
        nullable=False,
        default=LeaveStatus.PENDING,
    )

    start_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    end_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    user: Mapped["User"] = relationship("User", back_populates="leaves")
