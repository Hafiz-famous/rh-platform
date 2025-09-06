# app/factory.py
from flask_apscheduler import APScheduler # pyright: ignore[reportMissingImports]

scheduler = APScheduler()

def create_app():
    app = Flask(__name__) # pyright: ignore[reportUndefinedVariable]
    # ...
    scheduler.init_app(app)
    scheduler.start()
    return app

# jobs/overtime_jobs.py
from datetime import date, timedelta
from ..extensions import db # pyright: ignore[reportMissingImports]
from ..models.user import User # pyright: ignore[reportMissingImports]
from ..services.overtime_auto import compute_overtime_for_user_day # pyright: ignore[reportMissingImports]

def nightly_recompute():
    y = date.today() - timedelta(days=1)
    for uid, in db.session.query(User.id).all():
        compute_overtime_for_user_day(uid, y)

# register job (ex: 00:30 tous les jours)
scheduler.add_job(id='ot_nightly', func=nightly_recompute, trigger='cron', hour=0, minute=30)
