# app/models/award.py
from __future__ import annotations
from sqlalchemy import text
from ..extensions import db

class Award(db.Model):
    __tablename__ = "awards"

    id = db.Column(db.Integer, primary_key=True)

    # FK vers users
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    user = db.relationship("User", backref="awards")

    # IMPORTANT : la colonne en base s'appelle bien 'month'
    month = db.Column("month", db.String(7), nullable=False, unique=True)  # ex: '2025-10'

    score = db.Column(db.Float, nullable=False, default=0.0)

    # Colonne JSON existante et NOT NULL en base
    details = db.Column(db.JSON, nullable=False, server_default=text("'{}'"), default=dict)

    created_at = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)

    def __repr__(self) -> str:
        return f"<Award id={self.id} month={self.month} user_id={self.user_id} score={self.score}>"
