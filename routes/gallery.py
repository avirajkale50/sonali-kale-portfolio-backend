from bson import ObjectId
from flask import Blueprint, request, jsonify, current_app
import os
import uuid
from auth import require_auth
from db import get_db, get_fs

gallery_bp = Blueprint("gallery", __name__)

ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}

def _allowed_image(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS

def _serialize(doc: dict) -> dict:
    doc["_id"] = str(doc["_id"])
    return doc

@gallery_bp.route("", methods=["GET"])
def get_all():
    """Return all gallery items sorted by date (public)."""
    try:
        db = get_db()
        docs = list(db.gallery.find({}).sort("date", -1))
        return jsonify([_serialize(d) for d in docs]), 200
    except Exception as e:
        return jsonify({"error": "Database unavailable", "details": str(e)}), 503

@gallery_bp.route("", methods=["POST"])
@require_auth
def create():
    """Create a new gallery item (protected)."""
    try:
        db = get_db()
        data = request.get_json(force=True)
        data.pop("_id", None)
        result = db.gallery.insert_one(data)
        doc = db.gallery.find_one({"_id": result.inserted_id})
        return jsonify(_serialize(doc)), 201
    except Exception as e:
        return jsonify({"error": "Database error", "details": str(e)}), 500

@gallery_bp.route("/<id>", methods=["PUT"])
@require_auth
def update(id: str):
    """Update a gallery item by _id (protected)."""
    try:
        oid = ObjectId(id)
    except Exception:
        return jsonify({"error": "Invalid id"}), 400

    try:
        db = get_db()
        data = request.get_json(force=True)
        data.pop("_id", None)
        result = db.gallery.update_one({"_id": oid}, {"$set": data})
        if result.matched_count == 0:
            return jsonify({"error": "Not found"}), 404

        doc = db.gallery.find_one({"_id": oid})
        return jsonify(_serialize(doc)), 200
    except Exception as e:
        return jsonify({"error": "Database error", "details": str(e)}), 500

@gallery_bp.route("/<id>", methods=["DELETE"])
@require_auth
def delete(id: str):
    """Delete a gallery item by _id (protected)."""
    try:
        oid = ObjectId(id)
    except Exception:
        return jsonify({"error": "Invalid id"}), 400

    try:
        db = get_db()
        result = db.gallery.delete_one({"_id": oid})
        if result.deleted_count == 0:
            return jsonify({"error": "Not found"}), 404
        return jsonify({"message": "Deleted successfully"}), 200
    except Exception as e:
        return jsonify({"error": "Database error", "details": str(e)}), 500

@gallery_bp.route("/upload", methods=["POST"])
@require_auth
def upload_image():
    """Upload a gallery photo. Returns { url }."""
    print(f"DEBUG: Headers: {dict(request.headers)}")
    print(f"DEBUG: Files: {list(request.files.keys())}")
    if "file" not in request.files:
        return jsonify({
            "error": "No file provided",
            "debug_files": list(request.files.keys()),
            "debug_headers": dict(request.headers)
        }), 400

    file = request.files["file"]
    if not file.filename:
        return jsonify({"error": "Empty filename"}), 400
    if not _allowed_image(file.filename):
        return jsonify({"error": "File type not allowed"}), 400

    ext = file.filename.rsplit(".", 1)[1].lower()
    filename = f"gallery_{uuid.uuid4().hex}.{ext}"
    
    # Save to GridFS instead of filesystem
    fs = get_fs()
    fs.put(file, filename=filename, content_type=file.content_type)

    return jsonify({"url": f"/uploads/{filename}"}), 200
