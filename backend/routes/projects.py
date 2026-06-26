"""Projects routes — create, list, get, update projects."""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from backend.app import db
from backend.models.project import Project
from backend.utils.auth import get_current_user, require_role

projects_bp = Blueprint("projects", __name__)


def _next_sgid():
    from sqlalchemy import func
    count = db.session.query(func.count(Project.id)).scalar() or 0
    return f"SG-2026-{count+1:05d}"


@projects_bp.route("", methods=["GET"])
@jwt_required()
def list_projects():
    user     = get_current_user()
    page     = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)

    query = Project.query
    # Supervisors/developers only see their own projects
    if user.role in ("supervisor", "developer"):
        query = query.filter_by(owner_id=user.id)

    # Filters
    if request.args.get("risk_level"):
        query = query.filter_by(risk_level=request.args["risk_level"])
    if request.args.get("status"):
        query = query.filter_by(status=request.args["status"])
    if request.args.get("state"):
        query = query.filter_by(state=request.args["state"])

    pagination = query.order_by(Project.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    return jsonify({
        "projects": [p.to_dict() for p in pagination.items],
        "total":    pagination.total,
        "pages":    pagination.pages,
        "page":     page,
    }), 200


@projects_bp.route("", methods=["POST"])
@jwt_required()
def create_project():
    user = get_current_user()
    data = request.get_json() or {}

    if not data.get("name") or not data.get("address"):
        return jsonify({"error": "Project name and address are required"}), 400

    project = Project(
        sgid=_next_sgid(),
        name=data["name"].strip(),
        address=data["address"].strip(),
        building_type=data.get("building_type", "residential"),
        state=data.get("state", "Lagos"),
        lga=data.get("lga", "").strip(),
        floors=data.get("floors", 1),
        permit_ref=data.get("permit_ref", "").strip(),
        description=data.get("description", "").strip(),
        latitude=data.get("latitude"),
        longitude=data.get("longitude"),
        owner_id=user.id,
    )
    db.session.add(project)
    db.session.commit()
    return jsonify({"project": project.to_dict(), "message": "Project registered"}), 201


@projects_bp.route("/<int:project_id>", methods=["GET"])
@jwt_required()
def get_project(project_id):
    user    = get_current_user()
    project = Project.query.get_or_404(project_id)

    if user.role in ("supervisor", "developer") and project.owner_id != user.id:
        return jsonify({"error": "Access denied"}), 403

    subs = project.submissions.order_by(db.text("submitted_at desc")).limit(10).all()
    data = project.to_dict()
    data["recent_submissions"] = [s.to_dict() for s in subs]
    return jsonify({"project": data}), 200


@projects_bp.route("/<int:project_id>", methods=["PUT"])
@jwt_required()
def update_project(project_id):
    user    = get_current_user()
    project = Project.query.get_or_404(project_id)

    if user.role in ("supervisor", "developer") and project.owner_id != user.id:
        return jsonify({"error": "Access denied"}), 403

    data = request.get_json() or {}
    for field in ["name", "address", "building_type", "state", "lga",
                  "floors", "permit_ref", "description", "latitude", "longitude"]:
        if field in data:
            setattr(project, field, data[field])

    db.session.commit()
    return jsonify({"project": project.to_dict()}), 200


@projects_bp.route("/<int:project_id>/stop-work", methods=["POST"])
@jwt_required()
@require_role("agency_admin")
def stop_work(project_id):
    project = Project.query.get_or_404(project_id)
    project.status = "stop_work"
    db.session.commit()
    return jsonify({"message": f"Stop-work order issued for {project.name}"}), 200


@projects_bp.route("/stats", methods=["GET"])
@jwt_required()
def project_stats():
    user  = get_current_user()
    query = Project.query
    if user.role in ("supervisor", "developer"):
        query = query.filter_by(owner_id=user.id)

    total    = query.count()
    safe     = query.filter_by(risk_level="safe").count()
    monitor  = query.filter_by(risk_level="monitor").count()
    high     = query.filter_by(risk_level="high_risk").count()
    critical = query.filter_by(risk_level="critical").count()
    flagged  = query.filter_by(status="flagged").count()

    return jsonify({
        "total": total, "safe": safe, "monitor": monitor,
        "high_risk": high, "critical": critical, "flagged": flagged,
    }), 200
