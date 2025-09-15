from __future__ import annotations

from datetime import datetime
from typing import Optional

from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin

from sqlalchemy import (
    Integer, String, Boolean, Float, DateTime, ForeignKey, CheckConstraint, Index
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

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

    role: Mapped[Role] = mapped_column(
        SAEnum(Role, name="role_enum"), nullable=False, default=Role.EMPLOYEE, index=True
    )

    hourly_rate: Mapped[float] = mapped_column(Float, nullable=False, default=8.0)

    # ⚠️ Garde ce nom si tu l'utilises déjà partout. Flask-Login lira bien un bool ici.
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    # --- Relations ---
    department: Mapped[Optional["Department"]] = relationship(
        "Department", back_populates="users"
    )
    attendances: Mapped[list["Attendance"]] = relationship(
        "Attendance", back_populates="user", cascade="all, delete-orphan"
    )
    leaves: Mapped[list["Leave"]] = relationship(
        "Leave", back_populates="user", cascade="all, delete-orphan"
    )
    overtimes: Mapped[list["Overtime"]] = relationship(
        "Overtime", back_populates="user", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint("hourly_rate >= 0", name="ck_users_hourly_rate_nonneg"),
        # index composite utile si tu filtres souvent par dept + rôle
        Index("ix_users_department_role", "department_id", "role"),
    )

    # ---------- Helpers sécurité / rôles ----------
    def set_password(self, raw: str) -> None:
        self.password_hash = generate_password_hash(raw)

    def check_password(self, raw: str) -> bool:
        return check_password_hash(self.password_hash, raw)

    @property
    def full_name(self) -> str:
        fn = (self.first_name or "").strip()
        ln = (self.last_name or "").strip()
        return (f"{fn} {ln}".strip()) or self.email

    def has_role(self, *roles: Role) -> bool:
        """True si l'utilisateur possède un des rôles spécifiés."""
        return self.role in roles

    # Rôles de base
    def is_admin(self) -> bool:
        return self.role == Role.ADMIN

    def is_manager(self) -> bool:
        return self.role == Role.MANAGER or self.is_admin()

    def is_hr(self) -> bool:
        return self.role == Role.HR

    def is_employee(self) -> bool:
        return self.role == Role.EMPLOYEE

    # ➕ Droits fins (pour tes vues / blueprints)
    def can_access_admin(self) -> bool:
        """Droit d'afficher le menu /admin (admin, manager ou HR)."""
        return self.is_admin() or self.is_manager() or self.is_hr()

    def can_manage_users(self) -> bool:
        """Créer/modifier des comptes utilisateurs → admin ou RH UNIQUEMENT."""
        return self.is_admin() or self.is_hr()

    def can_manage_attendance(self) -> bool:
        """Gérer les pointages → manager, RH ou admin."""
        return self.is_admin() or self.is_hr() or self.is_manager()

    def can_manage_payroll(self) -> bool:
        """Gérer paie/coûts → RH ou admin."""
        return self.is_admin() or self.is_hr()

    @property
    def display_role(self) -> str:
        # joli libellé pour l'UI
        try:
            return self.role.name.title()
        except AttributeError:
            return str(self.role)

    @validates("email")
    def _normalize_email(self, key: str, value: str) -> str:
        """Normalise l'email (trim + lowercase) pour garantir l'unicité logique."""
        return (value or "").strip().lower()

    def __repr__(self) -> str:  # pragma: no cover
        return f"<User id={self.id} email={self.email} role={self.role}>"
