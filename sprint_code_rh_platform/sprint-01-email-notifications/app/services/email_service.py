# app/services/email_service.py
from __future__ import annotations

from flask import current_app, render_template
from flask_mailman import EmailMessage

def _send_html(to: list[str], subject: str, template: str, **ctx):
    """Low-level helper: render a Jinja template and send as HTML email."""
    html = render_template(template, **ctx)
    msg = EmailMessage(subject, html, to=to)
    msg.content_subtype = "html"
    msg.send()
    # Optional: log
    current_app.logger.info("Email sent to %s subject=%s template=%s", to, subject, template)

def send_leave_submitted_email(
    manager_email: str,
    employee_name: str,
    start_date,
    end_date,
    leave_id: int | str,
) -> None:
    subject = f"[RH] Nouvelle demande de congé #{leave_id}"
    _send_html(
        [manager_email],
        subject,
        "email/leave_submitted.html",
        employee_name=employee_name,
        start_date=start_date,
        end_date=end_date,
        leave_id=leave_id,
    )

def send_leave_status_email(
    user_email: str,
    user_name: str,
    status: str,
    start_date,
    end_date,
    leave_id: int | str,
) -> None:
    subject = f"[RH] Statut de votre congé #{leave_id}: {status.title()}"
    _send_html(
        [user_email],
        subject,
        "email/leave_status.html",
        user_name=user_name,
        status=status,
        start_date=start_date,
        end_date=end_date,
        leave_id=leave_id,
    )
