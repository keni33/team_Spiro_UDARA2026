"""
StructGuard AI — User Model
============================
Teaching note: A "model" in Flask/SQLAlchemy is a Python class that maps
directly to a database table. Each class attribute = one column in the table.

ROLES in StructGuard AI (managed by backend, not frontend):
  supervisor   → Site foreman — submits photos, sees their project results
  developer    → Building owner — sees all their projects + compliance status
  inspector    → Regulatory inspector — sees flagged/high-risk projects
  agency_admin → LASBCA Director — full analytics, user management
"""

from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from backend.app import db


class User(db.Model):
    """
    Represents every person who can log in to StructGuard AI.
    The 'role' column is the single source of truth for what they can access.
    """
    __tablename__ = "users"

    # ── Primary key ───────────────────────────────────────────────
    id            = db.Column(db.Integer, primary_key=True)

    # ── Basic profile ─────────────────────────────────────────────
    name          = db.Column(db.String(120), nullable=False)
    email         = db.Column(db.String(255), nullable=False, unique=True, index=True)

    # Password — NEVER stored in plain text, only the hash.
    # nullable=True because Google OAuth users have no password.
    password_hash = db.Column(db.String(255), nullable=True)

    # ── Role ──────────────────────────────────────────────────────
    # This is the single source of truth. Backend checks this on every
    # protected route. Frontend just reads and displays it.
    role          = db.Column(
        db.Enum("supervisor", "developer", "inspector", "agency_admin",
                name="user_roles"),
        nullable=False,
        default="supervisor"
    )

    # ── Optional profile fields ───────────────────────────────────
    phone         = db.Column(db.String(20))
    organisation  = db.Column(db.String(200))   # Company / agency name
    licence_no    = db.Column(db.String(100))   # Professional licence number
    state         = db.Column(db.String(100), default="Lagos")

    # ── OAuth ─────────────────────────────────────────────────────
    # Google's unique ID for this user. Null for email/password accounts.
    google_id     = db.Column(db.String(255), unique=True, nullable=True)

    # ── Account status ────────────────────────────────────────────
    is_active     = db.Column(db.Boolean, default=True,  nullable=False)
    is_verified   = db.Column(db.Boolean, default=False, nullable=False)

    # ── Timestamps ── always UTC ──────────────────────────────────
    created_at    = db.Column(db.DateTime,
                              default=lambda: datetime.now(timezone.utc))
    last_login    = db.Column(db.DateTime, nullable=True)

    # ── Relationships ─────────────────────────────────────────────
    # Teaching note: These tell SQLAlchemy how tables are connected.
    # foreign_keys= is required because User relates to Project twice
    # (once as owner, once as supervisor).
    projects      = db.relationship(
        "Project",
        back_populates="owner",
        lazy="dynamic",
        foreign_keys="Project.owner_id"
    )
    supervised    = db.relationship(
        "Project",
        back_populates="supervisor",
        lazy="dynamic",
        foreign_keys="Project.supervisor_id"
    )

    # ── Password methods ──────────────────────────────────────────
    def set_password(self, plain_text: str):
        """Hash and store the password. Never store plain text."""
        self.password_hash = generate_password_hash(plain_text)

    def check_password(self, plain_text: str) -> bool:
        """Return True if the given password matches the stored hash."""
        if not self.password_hash:
            return False    # Google-only accounts have no password
        return check_password_hash(self.password_hash, plain_text)

    def record_login(self):
        """
        Update last_login timestamp on every successful sign-in.
        Teaching note: We always store UTC time, never local time.
        """
        self.last_login = datetime.now(timezone.utc)

    # ── Role permission helpers ───────────────────────────────────
    # Teaching note: Logic lives HERE in the backend, not on the frontend.
    # Even if someone edits the frontend JS, these backend checks still run.
    def can_submit_photos(self) -> bool:
        return self.role in ("supervisor", "developer")

    def can_view_all_projects(self) -> bool:
        return self.role in ("inspector", "agency_admin")

    def can_issue_enforcement(self) -> bool:
        return self.role == "agency_admin"

    def can_view_analytics(self) -> bool:
        return self.role in ("inspector", "agency_admin")

    # ── Serialisation ─────────────────────────────────────────────
    # Teaching note: to_dict() converts this object to a plain Python
    # dictionary so Flask can turn it into JSON for the frontend.
    # We NEVER include password_hash or google_id in this output.
    def to_dict(self):
        return {
            "id":           self.id,
            "name":         self.name,
            "email":        self.email,
            "role":         self.role,
            "phone":        self.phone,
            "organisation": self.organisation,
            "licence_no":   self.licence_no,
            "state":        self.state,
            "is_active":    self.is_active,
            "is_verified":  self.is_verified,
            "has_password": bool(self.password_hash),
            "has_google":   bool(self.google_id),
            "created_at":   self.created_at.isoformat() if self.created_at else None,
            "last_login":   self.last_login.isoformat() if self.last_login else None,
        }

    def __repr__(self):
        return f"<User {self.email} [{self.role}]>"
