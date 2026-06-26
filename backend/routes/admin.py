"""
StructGuard AI — Admin / Agency Routes
=========================================
Teaching note: These routes are for regulatory agency users (inspectors and admins).
They are protected by @require_role so non-agency users get a 403 Forbidden response
if they try to call these endpoints — even if they know the URL.

Routes:
  GET  /api/admin/dashboard          → System-wide analytics
  GET  /api/admin/users              → All registered users (agency_admin only)
  POST /api/admin/users/<id>/deactivate → Disable a user account
  POST /api/admin/users/<id>/activate   → Re-enable a user account
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from backend.app import db
from backend.models.project import Project
from backend.models.submission import Submission
from backend.models.user import User
from backend.utils.auth import require_role, get_current_user

admin_bp = Blueprint("admin", __name__)


@admin_bp.route("/dashboard", methods=["GET"])
@jwt_required()
@require_role("inspector", "agency_admin")
def agency_dashboard():
    """
    System-wide analytics summary for the regulatory dashboard.
    Returns overview counts, the high-risk priority queue, and state breakdown.
    """
    from sqlalchemy import func

    total_projects    = Project.query.count()
    flagged           = Project.query.filter_by(status="flagged").count()
    stop_work         = Project.query.filter_by(status="stop_work").count()
    critical          = Project.query.filter_by(risk_level="critical").count()
    high_risk         = Project.query.filter_by(risk_level="high_risk").count()
    total_submissions = Submission.query.count()
    total_users       = User.query.count()

    # AI-prioritised inspection queue: highest risk score first
    priority_projects = (
        Project.query
        .filter(Project.risk_level.in_(["critical", "high_risk"]))
        .order_by(Project.risk_score.desc())
        .limit(10)
        .all()
    )

    # Projects grouped by state for the geographic breakdown widget
    state_data = (
        db.session.query(Project.state, func.count(Project.id).label("count"))
        .group_by(Project.state)
        .all()
    )

    return jsonify({
        "overview": {
            "total_projects":    total_projects,
            "flagged":           flagged,
            "stop_work":         stop_work,
            "critical":          critical,
            "high_risk":         high_risk,
            "safe":              Project.query.filter_by(risk_level="safe").count(),
            "monitor":           Project.query.filter_by(risk_level="monitor").count(),
            "total_submissions": total_submissions,
            "total_users":       total_users,
        },
        "priority_queue": [p.to_dict() for p in priority_projects],
        "by_state":        [{"state": s, "count": c} for s, c in state_data],
    }), 200


@admin_bp.route("/users", methods=["GET"])
@jwt_required()
@require_role("agency_admin")
def list_users():
    """
    List all registered users — agency_admin only.
    Teaching note: Inspectors can see the dashboard but NOT manage users.
    Only the agency_admin (LASBCA Director level) can see and manage accounts.
    """
    users = User.query.order_by(User.created_at.desc()).all()
    return jsonify({"users": [u.to_dict() for u in users], "total": len(users)}), 200


@admin_bp.route("/users/<int:user_id>/deactivate", methods=["POST"])
@jwt_required()
@require_role("agency_admin")
def deactivate_user(user_id):
    """
    Deactivate a user account.
    Teaching note: We use a 'soft delete' (is_active=False) rather than
    deleting the record — this preserves audit history.
    """
    user    = User.query.get_or_404(user_id)
    current = get_current_user()

    if user.id == current.id:
        return jsonify({"error": "You cannot deactivate your own account"}), 400

    user.is_active = False
    db.session.commit()
    return jsonify({"message": f"User {user.email} has been deactivated"}), 200


@admin_bp.route("/users/<int:user_id>/activate", methods=["POST"])
@jwt_required()
@require_role("agency_admin")
def activate_user(user_id):
    """Reactivate a deactivated user account."""
    user = User.query.get_or_404(user_id)
    user.is_active = True
    db.session.commit()
    return jsonify({"message": f"User {user.email} has been reactivated"}), 200
