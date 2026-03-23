from flask import Blueprint, request, jsonify

from auth import create_token, require_auth
from config import Config

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["POST"])
def login():
    """
    Accept application/x-www-form-urlencoded with fields:
      username  — the admin email
      password  — the admin password
    Returns { access_token, token_type } on success.
    """
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "").strip()

    if not username or not password:
        return jsonify({"error": "username and password are required"}), 400

    if username != Config.ADMIN_EMAIL or password != Config.ADMIN_PASSWORD:
        return jsonify({"error": "Invalid credentials"}), 401

    token = create_token(username)
    return jsonify({"access_token": token, "token_type": "bearer"}), 200


@auth_bp.route("/verify", methods=["GET"])
@require_auth
def verify():
    """Returns 200 OK if the Bearer token is valid."""
    return jsonify({"status": "ok"}), 200
