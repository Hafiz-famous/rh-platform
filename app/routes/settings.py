from flask import Blueprint, render_template
from flask_login import login_required
from ..services.authz import roles_required
from ..models.enums import Role

bp = Blueprint("settings", __name__, url_prefix="/admin/settings")

@bp.get("/")
@login_required
@roles_required(Role.ADMIN)
def index():
    return render_template("admin/settings/index.html")
