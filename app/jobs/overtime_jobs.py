# app/jobs/overtime_jobs.py
from __future__ import annotations
from datetime import date, timedelta

from flask import current_app, has_app_context

from ..models.user import User

# Service optionnel : on l'utilise s'il existe
try:
    from ..services.overtime_auto import compute_overtime_for_range  # (user_id, d1, d2)
except Exception:  # pragma: no cover
    compute_overtime_for_range = None


def _run_for_day(target_day: date) -> None:
    """Recalcule les HS automatiques pour tous les utilisateurs sur un jour donné."""
    if not compute_overtime_for_range:
        current_app.logger.warning("overtime_auto indisponible : aucun recalcul lancé")
        return

    ids = [uid for (uid,) in User.query.with_entities(User.id).all()]
    done = 0
    for uid in ids:
        try:
            compute_overtime_for_range(uid, target_day, target_day)
            done += 1
        except Exception as e:
            current_app.logger.exception("OT recompute failed uid=%s day=%s: %s",
                                        uid, target_day, e)
    current_app.logger.info("OT recompute finished: %s user(s), day=%s",
                            done, target_day.isoformat())


# === Ce nom est celui que ton create_app() essaie d'importer ===
def nightly_recompute() -> None:
    """Job quotidien (veille). Compatible avec un appel sans app_context."""
    d = date.today() - timedelta(days=1)
    if has_app_context():
        _run_for_day(d)
        return

    # Si le scheduler n'ouvre pas de contexte, on en crée un
    try:
        from app import create_app  # lazy import pour éviter les cycles
        app = create_app()
    except Exception as e:
        # on log sur stderr au pire
        import sys
        print(f"[jobs] nightly_recompute: no app context and create_app() failed: {e}",
              file=sys.stderr)
        return

    with app.app_context():
        _run_for_day(d)


def register_jobs(scheduler, app) -> None:
    """Alternative plus moderne : enregistre les jobs via le scheduler."""
    # quotidien 23:55
    scheduler.add_job(
        id="overtime_daily",
        func=nightly_recompute,          # réutilise la même fonction
        trigger="cron",
        hour=23, minute=55,
        misfire_grace_time=3600,
        replace_existing=True,
    )

    # heartbeat optionnel
    def _heartbeat():
        current_app.logger.debug("Scheduler heartbeat OK")
    scheduler.add_job(
        id="heartbeat",
        func=_heartbeat,
        trigger="interval",
        minutes=30,
        replace_existing=True,
    )
