"""Reports routes — generate and download PDF inspection reports."""
import os
from flask import Blueprint, send_file, jsonify, current_app
from flask_jwt_extended import jwt_required
from backend.app import db
from backend.models.submission import Submission, Report
from backend.utils.auth import get_current_user

reports_bp = Blueprint("reports", __name__)


@reports_bp.route("/<int:submission_id>/generate", methods=["POST"])
@jwt_required()
def generate_report(submission_id):
    user       = get_current_user()
    submission = Submission.query.get_or_404(submission_id)

    if submission.analysis_status != "complete":
        return jsonify({"error": "Analysis must be complete before generating a report"}), 400

    if submission.report:
        return jsonify({"report": submission.report.to_dict(), "message": "Report already exists"}), 200

    try:
        from backend.services.pdf_generator import generate_pdf
        report_dir  = os.path.join(current_app.root_path, "..", "backend", "uploads", "reports")
        os.makedirs(report_dir, exist_ok=True)
        output_path = os.path.join(report_dir, f"report_{submission_id}.pdf")
        generate_pdf(submission, output_path)

        report = Report(submission_id=submission_id, file_path=output_path)
        db.session.add(report)
        db.session.commit()

        return jsonify({"report": report.to_dict(), "message": "Report generated"}), 201
    except Exception as e:
        return jsonify({"error": f"PDF generation failed: {str(e)}"}), 500


@reports_bp.route("/<int:report_id>/download", methods=["GET"])
@jwt_required()
def download_report(report_id):
    report = Report.query.get_or_404(report_id)
    if not os.path.exists(report.file_path):
        return jsonify({"error": "Report file not found"}), 404
    return send_file(report.file_path, as_attachment=True,
                     download_name=f"StructGuard_Report_{report_id}.pdf")
