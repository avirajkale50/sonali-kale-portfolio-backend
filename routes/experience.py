from bson import ObjectId
from flask import Blueprint, request, jsonify, current_app
import os
import uuid
from auth import require_auth
from db import get_db, get_fs

experience_bp = Blueprint("experience", __name__)

ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}

def _allowed_image(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS

def _serialize(doc: dict) -> dict:
    doc["_id"] = str(doc["_id"])
    return doc

@experience_bp.route("", methods=["GET"])
def get_all():
    """Return all experience records sorted by order (public)."""
    try:
        db = get_db()
        docs = list(db.experience.find({}).sort("order", 1))
        return jsonify([_serialize(d) for d in docs]), 200
    except Exception as e:
        return jsonify({"error": "Database unavailable", "details": str(e)}), 503

@experience_bp.route("", methods=["POST"])
@require_auth
def create():
    """Create a new experience record (protected)."""
    try:
        db = get_db()
        data = request.get_json(force=True)
        data.pop("_id", None)
        result = db.experience.insert_one(data)
        doc = db.experience.find_one({"_id": result.inserted_id})
        return jsonify(_serialize(doc)), 201
    except Exception as e:
        return jsonify({"error": "Database error", "details": str(e)}), 500

@experience_bp.route("/<id>", methods=["PUT"])
@require_auth
def update(id: str):
    """Update an experience record by _id (protected)."""
    try:
        oid = ObjectId(id)
    except Exception:
        return jsonify({"error": "Invalid id"}), 400

    try:
        db = get_db()
        data = request.get_json(force=True)
        data.pop("_id", None)
        result = db.experience.update_one({"_id": oid}, {"$set": data})
        if result.matched_count == 0:
            return jsonify({"error": "Not found"}), 404

        doc = db.experience.find_one({"_id": oid})
        return jsonify(_serialize(doc)), 200
    except Exception as e:
        return jsonify({"error": "Database error", "details": str(e)}), 500

@experience_bp.route("/<id>", methods=["DELETE"])
@require_auth
def delete(id: str):
    """Delete an experience record by _id (protected)."""
    try:
        oid = ObjectId(id)
    except Exception:
        return jsonify({"error": "Invalid id"}), 400

    try:
        db = get_db()
        result = db.experience.delete_one({"_id": oid})
        if result.deleted_count == 0:
            return jsonify({"error": "Not found"}), 404
        return jsonify({"message": "Deleted successfully"}), 200
    except Exception as e:
        return jsonify({"error": "Database error", "details": str(e)}), 500

@experience_bp.route("/upload", methods=["POST"])
@require_auth
def upload_image():
    """Upload an institute logo/image. Returns { url }."""
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    if not file.filename:
        return jsonify({"error": "Empty filename"}), 400
    if not _allowed_image(file.filename):
        return jsonify({"error": "File type not allowed"}), 400

    ext = file.filename.rsplit(".", 1)[1].lower()
    filename = f"exp_{uuid.uuid4().hex}.{ext}"
    
    # Save to GridFS instead of filesystem
    fs = get_fs()
    fs.put(file, filename=filename, content_type=file.content_type)

    return jsonify({"url": f"/uploads/{filename}"}), 200
