"""Analysis routes — photo upload and AI risk analysis."""
import os, json
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required
from werkzeug.utils import secure_filename
from backend.app import db
from backend.models.project import Project
from backend.models.submission import Submission
from backend.utils.auth import get_current_user

analysis_bp = Blueprint("analysis", __name__)

ALLOWED = {"jpg", "jpeg", "png", "webp"}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED


@analysis_bp.route("/submit", methods=["POST"])
@jwt_required()
def submit_photo():
    user = get_current_user()
    if not user.can_submit():
        return jsonify({"error": "Only supervisors and developers can submit photos"}), 403

    if "photo" not in request.files:
        return jsonify({"error": "No photo file provided"}), 400

    file       = request.files["photo"]
    project_id = request.form.get("project_id")
    notes      = request.form.get("notes", "")

    if not project_id:
        return jsonify({"error": "project_id is required"}), 400

    project = Project.query.get_or_404(int(project_id))
    if project.owner_id != user.id:
        return jsonify({"error": "You can only submit photos for your own projects"}), 403

    if not allowed_file(file.filename):
        return jsonify({"error": "Only JPG, PNG, and WebP images are accepted"}), 400

    upload_dir = os.path.join(current_app.root_path, "..", "backend", "uploads", "images")
    os.makedirs(upload_dir, exist_ok=True)
    filename  = secure_filename(file.filename)
    import time
    safe_name = f"{int(time.time())}_{filename}"
    filepath  = os.path.join(upload_dir, safe_name)
    file.save(filepath)

    submission = Submission(
        project_id=project.id,
        submitted_by_id=user.id,
        image_path=safe_name,
        original_name=filename,
        notes=notes,
        analysis_status="processing",
    )
    db.session.add(submission)
    db.session.commit()

    # Run AI analysis
    try:
        from backend.services.ai_analysis import analyse_image
        result = analyse_image(filepath)

        submission.risk_level      = result["risk_level"]
        submission.risk_score      = result["risk_score"]
        submission.ai_summary      = result["summary"]
        submission.violations      = json.dumps(result.get("violations", []))
        submission.recommendations = json.dumps(result.get("recommendations", []))
        submission.analysis_status = "complete"

        # Update project risk level to worst seen
        risk_order = {"safe": 0, "monitor": 1, "high_risk": 2, "critical": 3}
        if risk_order.get(result["risk_level"], 0) > risk_order.get(project.risk_level, 0):
            project.risk_level = result["risk_level"]
            project.risk_score = result["risk_score"]
            if result["risk_level"] in ("high_risk", "critical"):
                project.status = "flagged"

        db.session.commit()
    except Exception as e:
        submission.analysis_status = "failed"
        submission.ai_summary      = f"Analysis failed: {str(e)}"
        db.session.commit()

    return jsonify({"submission": submission.to_dict()}), 201


@analysis_bp.route("/submissions/<int:project_id>", methods=["GET"])
@jwt_required()
def get_submissions(project_id):
    user    = get_current_user()
    project = Project.query.get_or_404(project_id)

    if user.role in ("supervisor", "developer") and project.owner_id != user.id:
        return jsonify({"error": "Access denied"}), 403

    subs = project.submissions.order_by(db.text("submitted_at desc")).all()
    return jsonify({"submissions": [s.to_dict() for s in subs]}), 200


@analysis_bp.route("/submission/<int:submission_id>", methods=["GET"])
@jwt_required()
def get_submission(submission_id):
    sub = Submission.query.get_or_404(submission_id)
    return jsonify({"submission": sub.to_dict()}), 200
