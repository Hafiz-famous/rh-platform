
from datetime import datetime, date
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy import Integer, Date, DateTime, Float, Text, ForeignKey, Enum
from ..extensions import db
from .enums import RequestStatus

class Overtime(db.Model):
    __tablename__ = "overtimes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    work_date: Mapped[date] = mapped_column(Date, nullable=False)
    hours: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[RequestStatus] = mapped_column(Enum(RequestStatus), default=RequestStatus.PENDING)
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="overtimes")
