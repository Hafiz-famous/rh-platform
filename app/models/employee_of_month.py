from datetime import date, datetime
from sqlalchemy import Column, Integer, Date, Text, ForeignKey, UniqueConstraint, DateTime
from sqlalchemy.orm import relationship
from app import db

class EmployeeOfMonth(db.Model):
    __tablename__ = "employee_of_month"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    # Première journée du mois (ex: 2025-08-01) pour identifier la période
    period = Column(Date, nullable=False, index=True)
    note = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", backref="employee_of_month_awards")

    __table_args__ = (
        UniqueConstraint("period", name="uq_employee_of_month_period"),
    )
