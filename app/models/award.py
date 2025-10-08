from __future__ import annotations

import calendar
from dataclasses import asdict, dataclass
from datetime import date
from typing import Any, Dict, Optional

from sqlalchemy import CheckConstraint, Index, text
from ..extensions import db


class Award(db.Model):
    """
    'Employé·e du mois' (EoM) stocké par période calendrier (YYYY-MM).
    Un seul gagnant par mois. Le champ 'details' peut contenir des infos
    supplémentaires (ex: métriques calculées, commentaire, etc.).
    """
    __tablename__ = "awards"

    id: int = db.Column(db.Integer, primary_key=True)

    # ---- Clés & relations
    user_id: int = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False,
        index=True,
    )
    # backref simple (si tu préfères lazy="dynamic", ajoute-le ici)
    user = db.relationship("User", backref="awards")

    # IMPORTANT : la colonne s'appelle 'month' et stocke 'YYYY-MM'
    month: str = db.Column(
        "month",
        db.String(7),
        nullable=False,
        unique=True,    # 1 gagnant par mois
        index=True,
        doc="Période au format 'YYYY-MM' (ex: 2025-10)",
    )

    # Score cumulé (optionnel, sert pour départager)
    score: float = db.Column(db.Float, nullable=False, default=0.0)

    # JSON non null — compat SQLite / Postgres :
    # - server_default: '{}' côté SGBD
    # - default: dict côté Python
    details: Dict[str, Any] = db.Column(
        db.JSON,
        nullable=False,
        server_default=text("'{}'"),
        default=dict,
        doc="Détails calculés (métriques, raisons, etc.)",
    )

    created_at = db.Column(
        db.DateTime,
        server_default=db.func.now(),
        nullable=False,
    )

    # ---- Contraintes & Index complémentaires
    __table_args__ = (
        # Valide le format basique 'YYYY-MM' (SQLite/Postgres)
        # NB: SQLite ne gère pas REGEXP par défaut; on reste simple :
        CheckConstraint(
            "length(month)=7 AND substr(month,5,1)='-'",
            name="ck_award_month_fmt",
        ),
        # Index composé utile si tu ajoutes d'autres périodes plus tard
        Index("ix_awards_user_month", "user_id", "month"),
    )

    # ---- Représentation
    def __repr__(self) -> str:
        return f"<Award id={self.id} month={self.month} user_id={self.user_id} score={self.score}>"

    # ---- Propriétés d'aide
    @property
    def year(self) -> Optional[int]:
        try:
            return int(self.month[:4])
        except Exception:
            return None

    @property
    def month_num(self) -> Optional[int]:
        try:
            return int(self.month[5:7])
        except Exception:
            return None

    @property
    def period_label(self) -> str:
        y, m = self.year, self.month_num
        if y and m and 1 <= m <= 12:
            return f"{calendar.month_name[m]} {y}"
        return self.month or "—"

    # ---- Helpers de création / recherche
    @staticmethod
    def ym_from_date(d: date) -> str:
        """Retourne 'YYYY-MM' pour une date donnée."""
        return f"{d.year:04d}-{d.month:02d}"

    @classmethod
    def from_ym(cls, ym: str) -> Optional["Award"]:
        """Retrouve l'Award par 'YYYY-MM'."""
        return cls.query.filter_by(month=ym).first()

    @classmethod
    def current_period(cls) -> str:
        """'YYYY-MM' du mois courant (UTC)."""
        return cls.ym_from_date(date.today())

    @classmethod
    def upsert(
        cls,
        *,
        ym: str,
        user_id: int,
        score: float = 0.0,
        details: Optional[Dict[str, Any]] = None,
    ) -> "Award":
        """
        Crée ou met à jour le gagnant pour la période 'ym' (YYYY-MM).
        """
        aw = cls.query.filter_by(month=ym).first()
        if not aw:
            aw = cls(month=ym, user_id=user_id, score=score, details=details or {})
            db.session.add(aw)
        else:
            aw.user_id = user_id
            aw.score = score
            if details:
                # merge simple
                merged = dict(aw.details or {})
                merged.update(details)
                aw.details = merged
        return aw

    # ---- Sérialisation simple (utile pour API / JSON)
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "month": self.month,
            "score": float(self.score or 0),
            "details": self.details or {},
            "period_label": self.period_label,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
