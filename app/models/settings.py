
from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Integer, String, DateTime, JSON, UniqueConstraint
from ..extensions import db

class AppSetting(db.Model):
    __tablename__ = "app_settings"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(120), unique=True, nullable=False, index=True)
    value: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (UniqueConstraint("key", name="uq_appsetting_key"),)

    @staticmethod
    def get(key: str, default=None):
        row = AppSetting.query.filter_by(key=key).first()
        return row.value if row else default

    @staticmethod
    def set(key: str, value: dict):
        row = AppSetting.query.filter_by(key=key).first()
        if not row:
            row = AppSetting(key=key, value=value)
            db.session.add(row)
        else:
            row.value = value
            row.updated_at = datetime.utcnow()
        db.session.commit()
        return row
