from __future__ import annotations

from datetime import datetime
from typing import List

from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Integer, String, DateTime
from app.extensions import db


class Department(db.Model):
    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # relation typée (assure-toi que User.department back_populates pointe ici)
    users: Mapped[List["User"]] = relationship(
        "User",
        back_populates="department",
        cascade="all, delete-orphan"
    )
