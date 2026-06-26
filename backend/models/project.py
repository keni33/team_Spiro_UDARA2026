"""
StructGuard AI — Project Model
================================
Teaching note: A Project represents one registered construction site.
Every photo submission and compliance check links back to a project.
The SGID (StructGuard ID) is the unique public reference for the site.
"""

import uuid
from datetime import datetime, timezone
from backend.app import db


class Project(db.Model):
    __tablename__ = "projects"

    id              = db.Column(db.Integer, primary_key=True)

    # Public-facing unique ID, e.g. "SG-2026-00042"
    sgid            = db.Column(db.String(30), unique=True, nullable=False, index=True)

    # Basic site info
    name            = db.Column(db.String(200), nullable=False)
    description     = db.Column(db.Text)
    address         = db.Column(db.String(500), nullable=False)
    state           = db.Column(db.String(100), default="Lagos")
    lga             = db.Column(db.String(100))  # Local Government Area

    # GPS coordinates — stored as strings for portability
    latitude        = db.Column(db.String(30))
    longitude       = db.Column(db.String(30))

    # Building details
    building_type   = db.Column(
        db.Enum("residential", "commercial", "industrial", "mixed", name="building_types"),
        nullable=False, default="residential"
    )
    floors          = db.Column(db.Integer, default=1)
    permit_ref      = db.Column(db.String(100))  # LASBCA permit number

    # Dates
    start_date      = db.Column(db.Date)
    expected_end    = db.Column(db.Date)
    actual_end      = db.Column(db.Date)

    # Compliance status — driven by backend logic, not user input
    status          = db.Column(
        db.Enum(
            "registered",       # Just created
            "active",           # Under construction, submissions ongoing
            "inspection_due",   # Milestone overdue
            "flagged",          # HIGH or CRITICAL risk score detected
            "stop_work",        # Enforcement action issued
            "completed",        # Construction finished
            name="project_status"
        ),
        nullable=False, default="registered"
    )

    # Risk level — updated after every AI analysis
    risk_level      = db.Column(
        db.Enum("safe", "monitor", "high_risk", "critical", name="risk_levels"),
        default="safe"
    )
    risk_score      = db.Column(db.Float, default=0.0)  # 0–100

    # Ownership
    owner_id        = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    supervisor_id   = db.Column(db.Integer, db.ForeignKey("users.id"))

    # Timestamps
    created_at      = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at      = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                                 onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    owner           = db.relationship("User", back_populates="projects",   foreign_keys=[owner_id])
    supervisor      = db.relationship("User", back_populates="supervised", foreign_keys=[supervisor_id])
    submissions     = db.relationship("Submission", back_populates="project", lazy="dynamic",
                                       cascade="all, delete-orphan")

    # ------------------------------------------------------------------ #
    # SGID GENERATION
    # Called before first save to give the project a human-readable ID
    # ------------------------------------------------------------------ #
    @staticmethod
    def generate_sgid():
        year = datetime.now(timezone.utc).year
        suffix = uuid.uuid4().hex[:5].upper()
        return f"SG-{year}-{suffix}"

    def to_dict(self, include_submissions=False):
        data = {
            "id":            self.id,
            "sgid":          self.sgid,
            "name":          self.name,
            "description":   self.description,
            "address":       self.address,
            "state":         self.state,
            "lga":           self.lga,
            "latitude":      self.latitude,
            "longitude":     self.longitude,
            "building_type": self.building_type,
            "floors":        self.floors,
            "permit_ref":    self.permit_ref,
            "start_date":    self.start_date.isoformat() if self.start_date else None,
            "expected_end":  self.expected_end.isoformat() if self.expected_end else None,
            "status":        self.status,
            "risk_level":    self.risk_level,
            "risk_score":    self.risk_score,
            "owner_id":      self.owner_id,
            "supervisor_id": self.supervisor_id,
            "created_at":    self.created_at.isoformat() if self.created_at else None,
            "updated_at":    self.updated_at.isoformat() if self.updated_at else None,
            "submission_count": self.submissions.count(),
        }
        if self.owner:
            data["owner_name"] = self.owner.name
        if include_submissions:
            data["submissions"] = [s.to_dict() for s in self.submissions.order_by(
                db.text("created_at DESC")).limit(10)]
        return data

    def __repr__(self):
        return f"<Project {self.sgid} — {self.name}>"
