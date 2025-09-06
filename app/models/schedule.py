from __future__ import annotations

from datetime import date as _date, time as _time
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Integer, Time, Date, String, ForeignKey, UniqueConstraint
from ..extensions import db

class WorkSchedule(db.Model):
    __tablename__ = "work_schedules"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)

    # 0 = lundi, 6 = dimanche
    weekday: Mapped[int] = mapped_column(Integer, nullable=False)

    start_time: Mapped[_time] = mapped_column(Time, nullable=False)
    end_time:   Mapped[_time] = mapped_column(Time, nullable=False)
    break_minutes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # (optionnel) si tu veux naviguer depuis l'user
    # user = relationship("User", back_populates="work_schedules")

    __table_args__ = (
        UniqueConstraint("user_id", "weekday", name="uq_schedule_user_day"),
    )

class Holiday(db.Model):
    __tablename__ = "holidays"

    date: Mapped[_date] = mapped_column(Date, primary_key=True)
    label: Mapped[str] = mapped_column(String(120), nullable=False)
