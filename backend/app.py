"""
StructGuard AI — Flask Application Factory
==========================================
Teaching note: An "app factory" is a function that creates the Flask app.
This pattern lets you create multiple app instances (e.g. one for testing,
one for production) with different configs — best practice for Flask.
"""

import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from datetime import timedelta
from dotenv import load_dotenv

# Load .env file values into environment
load_dotenv()

# --- Extension instances (created here, bound to app later) ---
db = SQLAlchemy()
jwt = JWTManager()
limiter = Limiter(key_func=get_remote_address, default_limits=["200 per day", "50 per hour"])


def create_app():
    """
    Creates and configures the Flask application.
    Call this from run.py to start the server.
    """
    app = Flask(__name__)

    # ------------------------------------------------------------------ #
    # CONFIGURATION
    # Teaching note: Config values are loaded from environment variables.
    # This means you can change behaviour (e.g. switch database) without
    # touching the code — just change the .env file.
    # ------------------------------------------------------------------ #
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-change-in-prod")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///structguard.db")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False  # Saves memory

    # JWT (JSON Web Token) settings — tokens expire for security
    app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", "jwt-secret-change-in-prod")
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(
        hours=int(os.getenv("JWT_ACCESS_TOKEN_EXPIRES_HOURS", 8))
    )
    app.config["JWT_REFRESH_TOKEN_EXPIRES"] = timedelta(
        days=int(os.getenv("JWT_REFRESH_TOKEN_EXPIRES_DAYS", 30))
    )

    # File upload limits
    max_mb = int(os.getenv("MAX_UPLOAD_SIZE_MB", 20))
    app.config["MAX_CONTENT_LENGTH"] = max_mb * 1024 * 1024
    app.config["UPLOAD_FOLDER"] = os.path.join(os.path.dirname(__file__), "uploads")
    app.config["ALLOWED_EXTENSIONS"] = set(
        os.getenv("ALLOWED_EXTENSIONS", "jpg,jpeg,png,webp").split(",")
    )

    # ------------------------------------------------------------------ #
    # BIND EXTENSIONS TO APP
    # ------------------------------------------------------------------ #
    db.init_app(app)
    jwt.init_app(app)
    limiter.init_app(app)

    # CORS: Allow the frontend (different port/domain) to call our API.
    # Teaching note: Browsers block cross-origin requests by default (security).
    # CORS headers tell the browser our API allows requests from the frontend.
    CORS(app, resources={
        r"/api/*": {
            "origins": [
                os.getenv("FRONTEND_URL", "http://localhost:5500"),
                "http://127.0.0.1:5500",
                "http://localhost:5500",
                "http://127.0.0.1:5000",
                "http://localhost:5000",
                "http://localhost:3000",
                "http://127.0.0.1:3000",
                "http://localhost:5501",
                "http://127.0.0.1:5501",
                "null",
            ],
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"],
            "supports_credentials": False,
        }
    })

    # ------------------------------------------------------------------ #
    # REGISTER BLUEPRINTS (Route groups)
    # Teaching note: Blueprints split routes into files by feature.
    # Each blueprint handles one area: auth, projects, analysis, etc.
    # ------------------------------------------------------------------ #
    from backend.routes.auth import auth_bp
    from backend.routes.projects import projects_bp
    from backend.routes.analysis import analysis_bp
    from backend.routes.reports import reports_bp
    from backend.routes.admin import admin_bp

    app.register_blueprint(auth_bp,     url_prefix="/api/auth")
    app.register_blueprint(projects_bp, url_prefix="/api/projects")
    app.register_blueprint(analysis_bp, url_prefix="/api/analysis")
    app.register_blueprint(reports_bp,  url_prefix="/api/reports")
    app.register_blueprint(admin_bp,    url_prefix="/api/admin")

    # ------------------------------------------------------------------ #
    # JWT ERROR HANDLERS
    # Return clean JSON errors instead of HTML pages when auth fails
    # ------------------------------------------------------------------ #
    @jwt.unauthorized_loader
    def missing_token_callback(error):
        return {"error": "Authentication required", "code": "MISSING_TOKEN"}, 401

    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_data):
        return {"error": "Session expired. Please log in again.", "code": "TOKEN_EXPIRED"}, 401

    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        return {"error": "Invalid authentication token", "code": "INVALID_TOKEN"}, 401

    # ------------------------------------------------------------------ #
    # CREATE DATABASE TABLES
    # Teaching note: db.create_all() reads your model classes and creates
    # matching tables in the database. Safe to run multiple times —
    # it skips tables that already exist.
    # ------------------------------------------------------------------ #
    with app.app_context():
        from backend.models import user, project, submission  # noqa — imports needed for create_all (Report is inside submission.py)
        db.create_all()
        _seed_demo_data(app)

    return app


def _seed_demo_data(app):
    """
    Creates demo accounts if the database is empty.
    Teaching note: Seeding is useful for development so you don't have to
    manually create accounts every time you reset the database.
    """
    from backend.models.user import User

    if User.query.count() > 0:
        return  # Already seeded — skip

    demo_users = [
        {"name": "Emeka Okafor",       "email": "supervisor@demo.com",  "role": "supervisor",    "password": "Demo1234!"},
        {"name": "Mrs. Adaeze Nwosu",  "email": "developer@demo.com",   "role": "developer",     "password": "Demo1234!"},
        {"name": "Inspector Kofi A.",  "email": "inspector@demo.com",   "role": "inspector",     "password": "Demo1234!"},
        {"name": "Director Fatima I.", "email": "admin@demo.com",       "role": "agency_admin",  "password": "Demo1234!"},
    ]

    for u in demo_users:
        user = User(name=u["name"], email=u["email"], role=u["role"])
        user.set_password(u["password"])
        db.session.add(user)

    db.session.commit()
    print("✅ Demo accounts created — see .env.example for credentials")