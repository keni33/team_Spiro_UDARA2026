"""
StructGuard AI — Submission Model
===================================
Teaching note: A Submission is one photo upload event at a construction milestone.
One project has many submissions over time (foundation, columns, roofing etc.).
Each submission gets an AI risk analysis result stored as JSON.
"""

import json
from datetime import datetime, timezone
from backend.app import db


class Submission(db.Model):
    __tablename__ = "submissions"

    id              = db.Column(db.Integer, primary_key=True)

    # Which project this belongs to
    project_id      = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=False)

    # Who submitted it
    submitted_by    = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    # Construction stage at time of submission
    milestone       = db.Column(
        db.Enum("foundation", "column_casting", "lintel", "roofing",
                "finishing", "completion", "existing_building", name="milestones"),
        nullable=False
    )

    # File paths of uploaded images (comma-separated, max 5)
    image_paths     = db.Column(db.Text)  # stored as JSON list string

    # GPS at time of photo capture
    latitude        = db.Column(db.String(30))
    longitude       = db.Column(db.String(30))

    # AI analysis results — stored as JSON so we can add fields later
    # Structure: {"risk_level": "high_risk", "risk_score": 78, "flags": [...], "summary": "..."}
    analysis_json   = db.Column(db.Text)
    analysis_status = db.Column(
        db.Enum("pending", "processing", "complete", "failed", name="analysis_status"),
        default="pending"
    )

    # Risk outcome (denormalised from analysis_json for fast querying)
    risk_level      = db.Column(
        db.Enum("safe", "monitor", "high_risk", "critical", name="sub_risk_levels"),
        default="safe"
    )
    risk_score      = db.Column(db.Float, default=0.0)

    # Notes and timestamps
    notes           = db.Column(db.Text)  # Supervisor's own notes
    created_at      = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    project         = db.relationship("Project", back_populates="submissions")
    submitter       = db.relationship("User", foreign_keys=[submitted_by])
    report          = db.relationship("Report", back_populates="submission",
                                       uselist=False, cascade="all, delete-orphan")

    def get_images(self):
        """Return list of image file paths."""
        if not self.image_paths:
            return []
        try:
            return json.loads(self.image_paths)
        except (json.JSONDecodeError, TypeError):
            return []

    def set_images(self, paths: list):
        self.image_paths = json.dumps(paths)

    def get_analysis(self):
        """Return parsed analysis dict or empty dict."""
        if not self.analysis_json:
            return {}
        try:
            return json.loads(self.analysis_json)
        except (json.JSONDecodeError, TypeError):
            return {}

    def set_analysis(self, data: dict):
        self.analysis_json = json.dumps(data)
        # Denormalise for fast queries
        self.risk_level = data.get("risk_level", "safe")
        self.risk_score = data.get("risk_score", 0.0)

    def to_dict(self):
        return {
            "id":              self.id,
            "project_id":      self.project_id,
            "submitted_by":    self.submitted_by,
            "submitter_name":  self.submitter.name if self.submitter else None,
            "milestone":       self.milestone,
            "images":          self.get_images(),
            "analysis":        self.get_analysis(),
            "analysis_status": self.analysis_status,
            "risk_level":      self.risk_level,
            "risk_score":      self.risk_score,
            "notes":           self.notes,
            "created_at":      self.created_at.isoformat() if self.created_at else None,
            "has_report":      self.report is not None,
        }


class Report(db.Model):
    """
    A generated PDF inspection report for one submission.
    Stored as a file path; metadata kept here for listing/downloading.
    """
    __tablename__ = "reports"

    id            = db.Column(db.Integer, primary_key=True)
    submission_id = db.Column(db.Integer, db.ForeignKey("submissions.id"), nullable=False)
    project_id    = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=False)
    file_path     = db.Column(db.String(500), nullable=False)
    file_name     = db.Column(db.String(200), nullable=False)
    generated_at  = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    generated_by  = db.Column(db.Integer, db.ForeignKey("users.id"))

    submission    = db.relationship("Submission", back_populates="report")

    def to_dict(self):
        return {
            "id":           self.id,
            "submission_id": self.submission_id,
            "project_id":   self.project_id,
            "file_name":    self.file_name,
            "generated_at": self.generated_at.isoformat() if self.generated_at else None,
            "download_url": f"/api/reports/{self.id}/download",
        }
