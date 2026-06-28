"""
StructGuard AI — Authentication Routes
=========================================
All login/registration logic lives here.

Routes:
  POST /api/auth/register          → create new account with email/password
  POST /api/auth/login             → email/password login, returns JWT
  GET  /api/auth/google            → redirect to Google OAuth consent screen
  GET  /api/auth/google/callback   → Google returns here after user approves
  POST /api/auth/refresh           → swap expiring token for a fresh one
  GET  /api/auth/me                → return current logged-in user profile
  PUT  /api/auth/change-password   → update password

Teaching note on Google OAuth flow:
  1. User clicks "Continue with Google" on frontend
  2. Frontend opens /api/auth/google  (this backend route)
  3. Backend redirects to Google's login page
  4. User logs in on Google and approves
  5. Google redirects back to /api/auth/google/callback with a short-lived code
  6. Backend exchanges that code for the user's profile (name, email)
  7. Backend creates or finds the user in our database
  8. Backend issues our own JWT and redirects frontend to index.html#oauth=...
  9. Frontend reads the token from the URL, stores it, goes to dashboard
"""

import os
import json
import base64
import requests as http_requests

from flask import Blueprint, request, jsonify, redirect
from flask_jwt_extended import (
    create_access_token, create_refresh_token,
    jwt_required, get_jwt_identity,
)
from backend.app import db, limiter
from backend.models.user import User
from backend.utils.auth import get_current_user

auth_bp = Blueprint("auth", __name__)

# Google OAuth endpoints — do not change these
GOOGLE_AUTH_URL     = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL    = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"


# ── Internal helpers ──────────────────────────────────────────────────

def _make_tokens(user):
    """Create a JWT access token and refresh token for this user."""
    identity = str(user.id)
    return (
        create_access_token(identity=identity),
        create_refresh_token(identity=identity),
    )


def _frontend_url():
    """
    Returns the frontend base URL from .env
    Teaching note: We strip trailing slashes so redirects like
    {url}/index.html never become http://localhost:5500//index.html
    """
    url = os.environ.get("FRONTEND_URL", "http://127.0.0.1:5500")
    return url.rstrip("/")


# ── Email / Password ──────────────────────────────────────────────────

@auth_bp.route("/register", methods=["POST"])
@limiter.limit("10 per hour")
def register():
    """Create a new user account with email and password."""
    data = request.get_json() or {}

    required = ["name", "email", "role", "password"]
    missing  = [f for f in required if not data.get(f)]
    if missing:
        return jsonify({"error": f"Required fields missing: {', '.join(missing)}"}), 400

    if User.query.filter_by(email=data["email"].lower().strip()).first():
        return jsonify({"error": "An account with this email already exists"}), 409

    valid_roles = {"supervisor", "developer", "inspector", "agency_admin"}
    if data["role"] not in valid_roles:
        return jsonify({"error": "Invalid role selected"}), 400

    user = User(
        name         = data["name"].strip(),
        email        = data["email"].lower().strip(),
        role         = data["role"],
        phone        = data.get("phone", "").strip() or None,
        state        = data.get("state", "Lagos"),
        organisation = data.get("organisation", "").strip() or None,
    )
    user.set_password(data["password"])
    db.session.add(user)
    db.session.commit()

    access, refresh = _make_tokens(user)
    return jsonify({
        "access_token":  access,
        "refresh_token": refresh,
        "user":          user.to_dict(),
    }), 201


@auth_bp.route("/login", methods=["POST"])
@limiter.limit("20 per hour")
def login():
    """Authenticate with email and password, return JWT tokens."""
    data     = request.get_json() or {}
    email    = data.get("email", "").lower().strip()
    password = data.get("password", "")

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return jsonify({"error": "Invalid email or password"}), 401

    if not user.is_active:
        return jsonify({"error": "Your account has been deactivated. Contact your administrator."}), 403

    user.record_login()
    db.session.commit()

    access, refresh = _make_tokens(user)
    return jsonify({
        "access_token":  access,
        "refresh_token": refresh,
        "user":          user.to_dict(),
    }), 200


# ── Google OAuth ──────────────────────────────────────────────────────

@auth_bp.route("/google", methods=["GET"])
def google_login():
    """
    Step 1 — Redirect the user to Google's OAuth consent screen.
    If GOOGLE_CLIENT_ID is not set in .env, redirect back with an error
    instead of crashing.
    """
    client_id    = os.environ.get("GOOGLE_CLIENT_ID", "").strip()
    redirect_uri = os.environ.get(
        "GOOGLE_REDIRECT_URI",
        "http://localhost:5000/api/auth/google/callback"
    )
    frontend     = _frontend_url()

    if not client_id:
        return redirect(f"{frontend}/?error=google_not_configured")

    params = {
        "client_id":     client_id,
        "redirect_uri":  redirect_uri,
        "response_type": "code",
        "scope":         "openid email profile",
        "access_type":   "offline",
        "prompt":        "select_account",
    }
    query = "&".join(f"{k}={v}" for k, v in params.items())
    return redirect(f"{GOOGLE_AUTH_URL}?{query}")


@auth_bp.route("/google/callback", methods=["GET"])
def google_callback():
    """
    Step 2 — Google redirects back here after the user approves.
    Everything is wrapped in try/except so ANY error redirects the user
    back to the login page with a friendly message instead of a crash page.
    """
    frontend = _frontend_url()

    try:
        # If Google sent an error (e.g. user clicked Cancel)
        error = request.args.get("error")
        code  = request.args.get("code")
        if error or not code:
            return redirect(f"{frontend}/?error=google_denied")

        client_id     = os.environ.get("GOOGLE_CLIENT_ID", "").strip()
        client_secret = os.environ.get("GOOGLE_CLIENT_SECRET", "").strip()
        redirect_uri  = os.environ.get(
            "GOOGLE_REDIRECT_URI",
            "http://localhost:5000/api/auth/google/callback"
        )

        # ── Exchange the one-time code for a Google access token ──
        token_res  = http_requests.post(GOOGLE_TOKEN_URL, data={
            "code":          code,
            "client_id":     client_id,
            "client_secret": client_secret,
            "redirect_uri":  redirect_uri,
            "grant_type":    "authorization_code",
        }, timeout=10)
        token_data   = token_res.json()
        google_token = token_data.get("access_token")

        if not google_token:
            raise ValueError(f"Google did not return an access token: {token_data}")

        # ── Fetch the user's profile from Google ──
        profile_res = http_requests.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {google_token}"},
            timeout=10,
        )
        profile = profile_res.json()
        email   = profile.get("email", "").lower().strip()
        name    = profile.get("name", "").strip() or email.split("@")[0]
        g_id    = str(profile.get("sub", ""))

        if not email:
            raise ValueError("Google did not return an email address")

        # ── Find or create our user in the database ──
        user = User.query.filter_by(email=email).first()

        if not user:
            # Brand new user signing in with Google for the first time
            user = User(
                name      = name,
                email     = email,
                role      = "supervisor",   # default — they can change in profile
                is_active = True,
            )
            # Set google_id safely — column exists in current model
            if hasattr(user, "google_id"):
                user.google_id = g_id
            db.session.add(user)
        else:
            # Existing user — link Google ID if not already set
            if hasattr(user, "google_id") and not user.google_id:
                user.google_id = g_id

        if not user.is_active:
            return redirect(f"{frontend}/?error=account_deactivated")

        # record_login updates last_login timestamp
        if hasattr(user, "record_login"):
            user.record_login()

        db.session.commit()

        # ── Issue our own JWT and send it to the frontend ──
        access, refresh = _make_tokens(user)

        # Encode as base64 and put in URL fragment (#oauth=...)
        # The # fragment is never sent to any server — it stays in the browser.
        payload = base64.urlsafe_b64encode(
            json.dumps({
                "access_token":  access,
                "refresh_token": refresh,
                "user":          user.to_dict(),
            }).encode()
        ).decode()

        return redirect(f"{frontend}/#oauth={payload}")

    except Exception as exc:
        # Log the real error to the terminal for debugging
        import traceback
        print(f"\n[Google OAuth Error] {exc}")
        traceback.print_exc()
        print()
        # But show the user a clean login page, not a crash page
        return redirect(f"{frontend}/?error=google_failed")


# ── Token management ──────────────────────────────────────────────────

@auth_bp.route("/refresh", methods=["POST"])
@jwt_required(refresh=True)
def refresh():
    """Exchange a refresh token for a new access token."""
    user_id = get_jwt_identity()
    user    = User.query.get(user_id)
    if not user or not user.is_active:
        return jsonify({"error": "User not found or deactivated"}), 404
    return jsonify({"access_token": create_access_token(identity=user_id)}), 200


@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def me():
    """Return the current user's profile. Called on every page load to verify token."""
    user = get_current_user()
    if not user:
        return jsonify({"error": "User not found"}), 404
    return jsonify({"user": user.to_dict()}), 200


@auth_bp.route("/change-password", methods=["PUT"])
@jwt_required()
def change_password():
    """Update the user's password. Google-only accounts cannot use this."""
    user    = get_current_user()
    data    = request.get_json() or {}
    current = data.get("current_password", "")
    new_pw  = data.get("new_password", "")

    # Google-only accounts have no password to change
    has_google_only = (
        hasattr(user, "google_id") and
        user.google_id and
        not user.password_hash
    )
    if has_google_only:
        return jsonify({
            "error": "Your account uses Google Sign-In. Manage your password via Google."
        }), 400

    if not user.check_password(current):
        return jsonify({"error": "Current password is incorrect"}), 400
    if len(new_pw) < 8:
        return jsonify({"error": "New password must be at least 8 characters"}), 400

    user.set_password(new_pw)
    db.session.commit()
    return jsonify({"message": "Password updated successfully"}), 200
