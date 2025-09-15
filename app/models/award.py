# app/models/award.py
from __future__ import annotations
from ..extensions import db

class Award(db.Model):
    __tablename__ = "awards"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    # IMPORTANT : correspond à la table actuelle (texte 'YYYY-MM')
    month = db.Column(db.String(7), nullable=False)  # ex: '2025-09'

    score = db.Column(db.Float, nullable=False, default=0.0)
    created_at = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)

    __table_args__ = (
        db.UniqueConstraint("user_id", "month", name="uq_award_user_month"),
    )

    user = db.relationship("User", backref="awards")
