# app/models/payroll_cost.py
from __future__ import annotations
from datetime import datetime
from decimal import Decimal
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Integer, Numeric, String, ForeignKey, DateTime, UniqueConstraint, Index
from app.extensions import db

class PayrollCost(db.Model):
    __tablename__ = "payroll_costs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id"), index=True, nullable=False)

    year:  Mapped[int] = mapped_column(Integer, nullable=False)     # ex: 2025
    month: Mapped[int] = mapped_column(Integer, nullable=False)     # 1..12

    base_salary:    Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0, nullable=False)
    overtime_cost:  Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0, nullable=False)
    leave_cost:     Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0, nullable=False)
    benefits_cost:  Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0, nullable=False)
    currency:       Mapped[str]     = mapped_column(String(8), default="XOF", nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    department = relationship("Department", back_populates="payroll_costs")

    __table_args__ = (
        UniqueConstraint("department_id", "year", "month", name="uq_payroll_costs_dep_month"),
        Index("ix_payroll_costs_year_month", "year", "month"),
    )

    @property
    def total_cost(self):
        return (self.base_salary or 0) + (self.overtime_cost or 0) + (self.leave_cost or 0) + (self.benefits_cost or 0)
