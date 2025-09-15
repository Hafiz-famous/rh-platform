# app/utils/authz.py
from functools import wraps
from flask import abort
from flask_login import current_user

def roles_required(*roles):
    roles = {r.upper() for r in roles}
    def deco(f):
        @wraps(f)
        def _wrap(*a, **k):
            if not current_user.is_authenticated:
                from flask_login import login_manager
                return login_manager.unauthorized()
            user_role = getattr(current_user, "role", None)
            name = getattr(user_role, "name", None) or str(user_role).upper()
            if name not in roles:
                abort(403)
            return f(*a, **k)
        return _wrap
    return deco
