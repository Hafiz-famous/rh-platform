from flask import Blueprint, render_template
from app.services.dashboard_service import DashboardService

pages_bp = Blueprint("pages", __name__)

@pages_bp.route("/dashboard")
def dashboard_page():
    data = DashboardService.global_overview()
    eom = data.get("employee_of_month")
    return render_template(
        "dashboard.html",
        eom_name=(eom["name"] if eom else None),
        # facultatif si tu veux les afficher sous le nom
        eom_dept=(eom.get("department") if eom else None) if eom else None,
        eom_period=(eom.get("period_label") if eom else None) if eom else None,
    )
