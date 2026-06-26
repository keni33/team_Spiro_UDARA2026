"""
StructGuard AI — Authentication Routes
=========================================
Teaching note: This file handles ALL login/registration logic.

Routes:
  POST /api/auth/register       → create new account
  POST /api/auth/login          → email/password login
  GET  /api/auth/google         → redirect to Google OAuth
  GET  /api/auth/google/callback → Google redirects back here
  POST /api/auth/refresh        → get new access token
  GET  /api/auth/me             → get current user info
  PUT  /api/auth/change-password

GOOGLE OAUTH FLOW (teaching):
  1. User clicks "Sign in with Google" on frontend
  2. Frontend opens: GET /api/auth/google
  3. Backend redirects to Google's login page
  4. User logs in on Google
  5. Google redirects to /api/auth/google/callback with a code
  6. Backend exchanges code for user info (name, email, picture)
  7. Backend creates/finds the user in DB, issues our JWT
  8. Backend redirects to frontend with JWT in URL fragment
  9. Frontend reads JWT from URL, stores it, navigates to dashboard
"""

import os, requests as http_requests
from flask import Blueprint, request, jsonify, redirect
from flask_jwt_extended import (
    create_access_token, create_refresh_token,
    jwt_required, get_jwt_identity
)
from backend.app import db, limiter
from backend.models.user import User
from backend.utils.auth import get_current_user

auth_bp = Blueprint("auth", __name__)

# ── Helpers ──────────────────────────────────────────────────────────

GOOGLE_AUTH_URL     = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL    = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"

def _make_tokens(user):
    """Issue JWT access + refresh tokens for a user."""
    identity = str(user.id)
    return (
        create_access_token(identity=identity),
        create_refresh_token(identity=identity),
    )

def _user_dict(user):
    return {
        "access_token":  None,   # filled by caller
        "refresh_token": None,
        "user": user.to_dict(),
    }

# ── Email / Password Auth ─────────────────────────────────────────────

@auth_bp.route("/register", methods=["POST"])
@limiter.limit("10 per hour")
def register():
    data = request.get_json() or {}
    required = ["name", "email", "role", "password"]
    missing  = [f for f in required if not data.get(f)]
    if missing:
        return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400

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
    data     = request.get_json() or {}
    email    = data.get("email", "").lower().strip()
    password = data.get("password", "")

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return jsonify({"error": "Invalid email or password"}), 401
    if not user.is_active:
        return jsonify({"error": "Your account has been deactivated. Contact your agency admin."}), 403

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
    Step 1: Redirect user to Google's OAuth consent screen.
    Teaching note: We send Google our client_id and a redirect_uri
    (where Google should send the user back after login).
    """
    client_id    = os.environ.get("GOOGLE_CLIENT_ID", "")
    redirect_uri = os.environ.get("GOOGLE_REDIRECT_URI",
                                  "http://localhost:5000/api/auth/google/callback")
    frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:5500")

    if not client_id:
        # No Google credentials configured — redirect to frontend with error
        return redirect(f"{frontend_url}/index.html?error=google_not_configured")

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
    Step 2: Google redirects here with a one-time 'code'.
    We exchange it for an access token, fetch the user's profile,
    then create/find our user and issue our own JWT.
    Teaching note: We never store Google's token — we just use it
    once to get the user's email, then issue our own JWT.
    """
    frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:5500")
    error        = request.args.get("error")
    code         = request.args.get("code")

    if error or not code:
        return redirect(f"{frontend_url}/index.html?error=google_denied")

    client_id     = os.environ.get("GOOGLE_CLIENT_ID", "")
    client_secret = os.environ.get("GOOGLE_CLIENT_SECRET", "")
    redirect_uri  = os.environ.get("GOOGLE_REDIRECT_URI",
                                   "http://localhost:5000/api/auth/google/callback")

    # Exchange code for access token
    try:
        token_res = http_requests.post(GOOGLE_TOKEN_URL, data={
            "code":          code,
            "client_id":     client_id,
            "client_secret": client_secret,
            "redirect_uri":  redirect_uri,
            "grant_type":    "authorization_code",
        }, timeout=10)
        token_data = token_res.json()
        google_token = token_data.get("access_token")
        if not google_token:
            raise ValueError("No access token in response")

        # Fetch user profile from Google
        profile_res  = http_requests.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {google_token}"},
            timeout=10
        )
        profile = profile_res.json()
        email   = profile.get("email", "").lower().strip()
        name    = profile.get("name", email.split("@")[0])
        g_id    = profile.get("sub", "")   # Google's unique user ID

        if not email:
            raise ValueError("No email returned from Google")

    except Exception as e:
        return redirect(f"{frontend_url}/index.html?error=google_failed")

    # Find existing user or create a new one
    user = User.query.filter_by(email=email).first()
    if not user:
        # New user via Google — default role is 'supervisor'
        # They can update role in profile settings
        user = User(
            name       = name,
            email      = email,
            role       = "supervisor",
            google_id  = g_id,
            is_active  = True,
        )
        # No password needed for Google users
        db.session.add(user)
    else:
        # Existing user — link their Google ID if not already linked
        if not user.google_id:
            user.google_id = g_id

    if not user.is_active:
        return redirect(f"{frontend_url}/index.html?error=account_deactivated")

    user.record_login()
    db.session.commit()

    access, refresh = _make_tokens(user)

    # Redirect to frontend with tokens in URL fragment (never in query string)
    # Teaching note: Fragment (#) is never sent to servers — more private than ?param=
    import json, base64
    payload = base64.urlsafe_b64encode(json.dumps({
        "access_token":  access,
        "refresh_token": refresh,
        "user":          user.to_dict(),
    }).encode()).decode()

    return redirect(f"{frontend_url}/index.html#oauth={payload}")


# ── Token Management ──────────────────────────────────────────────────

@auth_bp.route("/refresh", methods=["POST"])
@jwt_required(refresh=True)
def refresh():
    """Exchange an expiring access token for a fresh one."""
    user_id = get_jwt_identity()
    user    = User.query.get(user_id)
    if not user or not user.is_active:
        return jsonify({"error": "User not found or deactivated"}), 404
    return jsonify({"access_token": create_access_token(identity=user_id)}), 200


@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def me():
    """Return the currently logged-in user's profile."""
    user = get_current_user()
    if not user:
        return jsonify({"error": "User not found"}), 404
    return jsonify({"user": user.to_dict()}), 200


@auth_bp.route("/change-password", methods=["PUT"])
@jwt_required()
def change_password():
    user    = get_current_user()
    data    = request.get_json() or {}
    current = data.get("current_password", "")
    new_pw  = data.get("new_password", "")

    if user.google_id and not user.password_hash:
        return jsonify({"error": "Google accounts cannot set a password here. Use Google to manage your password."}), 400
    if not user.check_password(current):
        return jsonify({"error": "Current password is incorrect"}), 400
    if len(new_pw) < 8:
        return jsonify({"error": "New password must be at least 8 characters"}), 400

    user.set_password(new_pw)
    db.session.commit()
    return jsonify({"message": "Password updated successfully"}), 200
