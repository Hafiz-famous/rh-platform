
from flask import Blueprint, render_template
from flask_login import login_required
from ..models.enums import Role
from ..services.authz import roles_required
from ..extensions import db
from ..models.user import User

bp = Blueprint("admin", __name__, url_prefix="/admin")

@bp.get("/")
@login_required
@roles_required(Role.ADMIN)
def admin_home():
    users = User.query.order_by(User.created_at.desc()).limit(20).all()
    return render_template("admin/index.html", users=users)
