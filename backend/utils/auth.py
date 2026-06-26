"""
Auth utilities — JWT helpers and role-based access decorators.
Teaching note: @require_role is a decorator — it wraps your route function.
When a request comes in, it first checks the JWT is valid, then checks
the user's role. If the role doesn't match, it returns 403 before your
route code even runs. This is backend enforcement — the frontend cannot
bypass it.
"""
from functools import wraps
from flask import jsonify
from flask_jwt_extended import get_jwt_identity
from backend.app import db


def get_current_user():
    """Get the User object for the currently authenticated JWT holder."""
    from backend.models.user import User
    user_id = get_jwt_identity()
    return db.session.get(User, int(user_id))


def require_role(*roles):
    """
    Decorator: only allow users whose role is in the given list.
    Usage:
        @require_role("inspector", "agency_admin")
        def my_route(): ...
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            user = get_current_user()
            if not user:
                return jsonify({"error": "User not found"}), 404
            if not user.is_active:
                return jsonify({"error": "Account is deactivated"}), 403
            if user.role not in roles:
                return jsonify({
                    "error": f"Access denied. Required role: {' or '.join(roles)}"
                }), 403
            return fn(*args, **kwargs)
        return wrapper
    return decorator
