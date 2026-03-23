import os
import uuid

from bson import ObjectId
from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename

from auth import require_auth
from db import get_db, get_fs

profile_bp = Blueprint("profile", __name__)

ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}


def _allowed_image(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS


def _serialize(doc: dict) -> dict:
    doc["_id"] = str(doc["_id"])
    return doc


@profile_bp.route("", methods=["GET"])
def get_profile():
    """Return the single profile document (public)."""
    try:
        db = get_db()
        doc = db.profile.find_one({})
        if not doc:
            return jsonify(None), 200
        return jsonify(_serialize(doc)), 200
    except Exception as e:
        return jsonify({"error": "Database unavailable", "details": str(e)}), 503


@profile_bp.route("", methods=["PUT"])
@require_auth
def update_profile():
    """Upsert the profile document (protected)."""
    try:
        db = get_db()
        data = request.get_json(force=True)
        # Never let the client set _id
        data.pop("_id", None)

        db.profile.update_one({}, {"$set": data}, upsert=True)
        doc = db.profile.find_one({})
        return jsonify(_serialize(doc)), 200
    except Exception as e:
        return jsonify({"error": "Database error", "details": str(e)}), 500


@profile_bp.route("/photo", methods=["POST"])
@require_auth
def upload_photo():
    """Upload a profile photo (protected). Returns { photo_url }."""
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    if not file.filename:
        return jsonify({"error": "Empty filename"}), 400
    if not _allowed_image(file.filename):
        return jsonify({"error": "File type not allowed"}), 400

    ext = file.filename.rsplit(".", 1)[1].lower()
    filename = f"photo_{uuid.uuid4().hex}.{ext}"
    
    # Save to GridFS
    fs = get_fs()
    fs.put(file, filename=filename, content_type=file.content_type)

    photo_url = f"/uploads/{filename}"

    # Also update the photo field in the profile document
    try:
        db = get_db()
        db.profile.update_one({}, {"$set": {"photo": photo_url}}, upsert=True)
    except Exception as e:
        return jsonify({"error": "Database error", "details": str(e)}), 500

    return jsonify({"photo_url": photo_url}), 200
