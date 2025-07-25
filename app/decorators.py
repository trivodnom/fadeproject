from functools import wraps
from flask import abort
from flask_login import current_user

def admin_or_organizer_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or (current_user.role not in ['admin', 'organizer']):
            abort(403) # Forbidden
        return f(*args, **kwargs)
    return decorated_function