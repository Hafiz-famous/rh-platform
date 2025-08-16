from __future__ import annotations

from datetime import datetime
from typing import Optional, List

from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin

from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Integer, String, Boolean, Float, DateTime, ForeignKey
from sqlalchemy import Enum as SAEnum  # évite la confusion avec enum.Enum

from app.extensions import db
from .enums import Role  # Enum Python: class Role(Enum): ADMIN=..., MANAGER=..., HR=..., EMPLOYEE=...


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    department_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("departments.id"), nullable=True, index=True
    )

    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )

    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    first_name: Mapped[str] = mapped_column(String(80), nullable=False)
    last_name: Mapped[str] = mapped_column(String(80), nullable=False)

    # Enum SQLAlchemy basé sur l'Enum Python `Role`
    role: Mapped[Role] = mapped_column(
        SAEnum(Role, name="role_enum"), nullable=False, default=Role.EMPLOYEE
    )

    hourly_rate: Mapped[float] = mapped_column(Float, default=8.0, nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    # Relations (assure-toi que les autres modèles utilisent back_populates symétriquement)
    department: Mapped[Optional["Department"]] = relationship(
        "Department", back_populates="users"
    )

    attendances: Mapped[List["Attendance"]] = relationship(
        "Attendance", back_populates="user", cascade="all, delete-orphan"
    )

    leaves: Mapped[List["Leave"]] = relationship(
        "Leave", back_populates="user", cascade="all, delete-orphan"
    )

    overtimes: Mapped[List["Overtime"]] = relationship(
        "Overtime", back_populates="user", cascade="all, delete-orphan"
    )

    # ---------- Helpers sécurité / rôles ----------
    def set_password(self, raw: str) -> None:
        self.password_hash = generate_password_hash(raw)

    def check_password(self, raw: str) -> bool:
        return check_password_hash(self.password_hash, raw)

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    # Raccourcis de rôles (utilisables dans Jinja : current_user.is_admin(), etc.)
    def has_role(self, *roles: Role) -> bool:
        """True si l'utilisateur possède un des rôles spécifiés."""
        return self.role in roles

    def is_admin(self) -> bool:
        return self.role == Role.ADMIN

    def is_manager(self) -> bool:
        # souvent on considère qu'un admin a aussi les droits manager
        return self.role in (Role.MANAGER, Role.ADMIN)

    def is_hr(self) -> bool:
        return self.role == Role.HR

    def is_employee(self) -> bool:
        return self.role == Role.EMPLOYEE

    def can_access_admin(self) -> bool:
        """Droit d'afficher le menu /admin (admin ou manager)."""
        return self.is_admin() or self.is_manager()

    @property
    def display_role(self) -> str:
        # joli libellé pour l'UI
        return self.role.name.title() if hasattr(self.role, "name") else str(self.role)

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email} role={self.role}>"
