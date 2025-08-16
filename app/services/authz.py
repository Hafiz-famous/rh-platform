
from functools import wraps
from flask import abort
from flask_login import current_user

def roles_required(*roles):
    allowed = {getattr(r, "value", r) for r in roles}
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)
            current = getattr(current_user.role, "value", current_user.role)
            if current not in allowed:
                abort(403)
            return fn(*args, **kwargs)
        return wrapper
    return decorator
