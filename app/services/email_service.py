from flask_mailman import EmailMessage
from flask import render_template
from app.extensions import mail
import functools, time, logging

log = logging.getLogger(__name__)

def retry(times=3, delay=1.5):
    def deco(fn):
        @functools.wraps(fn)
        def wrap(*a, **kw):
            last = None
            for _ in range(times):
                try:
                    return fn(*a, **kw)
                except Exception as e:
                    last = e
                    time.sleep(delay)
            log.exception("Email send failed after retries: %s", last)
        return wrap
    return deco

@retry()
def send_leave_submitted_email(manager_email, employee_name, start_date, end_date, leave_id):
    subject = f"[RH] Nouvelle demande de congé #{leave_id}"
    html = render_template("emails/leave_submitted.html",
                           employee_name=employee_name, start_date=start_date, end_date=end_date, leave_id=leave_id)
    EmailMessage(subject, html, to=[manager_email]).send()

@retry()
def send_leave_status_email(user_email, user_name, status, start_date, end_date, leave_id):
    subject = f"[RH] Votre demande #{leave_id} est {status}"
    html = render_template("emails/leave_status.html",
                           user_name=user_name, status=status, start_date=start_date, end_date=end_date, leave_id=leave_id)
    EmailMessage(subject, html, to=[user_email]).send()
