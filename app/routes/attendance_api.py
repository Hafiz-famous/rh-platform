# app/routes/attendance_api.py
from __future__ import annotations
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime, date
from app.extensions import db
from app.models.attendance import Attendance  # adapte l'import si besoin

attendance_api = Blueprint("attendance_api", __name__, url_prefix="/attendance/api")


def _cols():
    """Liste des colonnes du modèle Attendance."""
    return set(Attendance.__table__.columns.keys())


def _pick(*candidates):
    """Retourne le 1er nom de colonne existant dans le modèle."""
    cols = _cols()
    for name in candidates:
        if name in cols:
            return name
    return None


@login_required
@attendance_api.post("/mark")
def mark():
    """
    Enregistre un pointage en s'adaptant au schéma existant :
    - Mode 'par jour' s'il y a des colonnes check_in / check_out (ou variantes)
    - Sinon, mode 'événements' (une ligne par évènement)
    """

    data = request.get_json(force=True, silent=True) or {}
    action = data.get("action")
    if action not in ("checkin", "checkout"):
        return jsonify(ok=False, message="action invalide"), 400

    lat = data.get("lat")
    lng = data.get("lng")
    acc = data.get("accuracy")
    now = datetime.utcnow()

    # Détection dynamique des colonnes
    F_CHECKIN = _pick("check_in", "checkin", "check_in_at", "in_time", "clock_in", "started_at", "start_at")
    F_CHECKOUT = _pick("check_out", "checkout", "check_out_at", "out_time", "clock_out", "ended_at", "end_at")
    F_DATE = _pick("date", "work_date", "day")
    F_TS = _pick("timestamp", "time_at", "ts", "created_at")
    F_EVENT = _pick("type", "event", "action")  # au cas où ton modèle a 'type'/'event'
    F_LAT = _pick("latitude", "lat")
    F_LNG = _pick("longitude", "lng")
    F_ACC = _pick("accuracy", "acc")

    # Mode "par jour" si on trouve les colonnes de check-in/out
    if F_CHECKIN and F_CHECKOUT:
        # Trouve/Crée l'enregistrement du jour
        today = date.today()
        row = None
        if F_DATE:
            row = db.session.query(Attendance).filter(
                getattr(Attendance, "user_id") == current_user.id,
                getattr(Attendance, F_DATE) == today,
            ).first()
        else:
            # Pas de colonne 'date' : on prend la dernière ligne 'ouverte' (sans checkout)
            row = db.session.query(Attendance).filter(
                getattr(Attendance, "user_id") == current_user.id,
                getattr(Attendance, F_CHECKOUT).is_(None),
            ).order_by(getattr(Attendance, F_CHECKIN).desc()).first()

        if row is None:
            # Crée une ligne (et renseigne la date si elle existe)
            kwargs = {"user_id": current_user.id}
            if F_DATE:
                kwargs[F_DATE] = today
            row = Attendance(**kwargs)
            db.session.add(row)

        if action == "checkin":
            setattr(row, F_CHECKIN, now)
            # Si pas de date sur le modèle, on laisse comme ça (c'est OK)
        else:  # checkout
            setattr(row, F_CHECKOUT, now)

        # Localisation si colonnes présentes
        if F_LAT: setattr(row, F_LAT, lat)
        if F_LNG: setattr(row, F_LNG, lng)
        if F_ACC: setattr(row, F_ACC, acc)

        db.session.commit()
        return jsonify(ok=True, mode="per_day", at=now.isoformat() + "Z")

    # Sinon : mode "événements" (une ligne par évènement)
    kwargs = {"user_id": current_user.id}

    # Timestamp : on renseigne la meilleure colonne dispo
    if F_TS:
        kwargs[F_TS] = now

    # Evènement : 'type'/'event' si dispo ; sinon on ignore (pas bloquant)
    if F_EVENT:
        kwargs[F_EVENT] = action

    if F_LAT: kwargs[F_LAT] = lat
    if F_LNG: kwargs[F_LNG] = lng
    if F_ACC: kwargs[F_ACC] = acc

    # Fallback : si le modèle n'a aucune de ces colonnes, crée quand même et
    # compte sur created_at (server_default) pour l'horodatage.
    att = Attendance(**kwargs)
    db.session.add(att)
    db.session.commit()
    return jsonify(ok=True, mode="event", at=(now.isoformat() + "Z"))
