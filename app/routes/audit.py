from flask import Blueprint, render_template
from flask_login import login_required
from ..services.authz import roles_required
from ..models.enums import Role

bp = Blueprint("audit", __name__, url_prefix="/admin/audit")

@bp.get("/")
@login_required
@roles_required(Role.ADMIN)
def index():
    return render_template("admin/audit/index.html")
