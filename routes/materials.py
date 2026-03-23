import os
import uuid
from datetime import datetime, timezone

from bson import ObjectId
from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename

from auth import require_auth
from db import get_db, get_fs

materials_bp = Blueprint("materials", __name__)

ALLOWED_EXTENSIONS = {
    "pdf", "doc", "docx", "ppt", "pptx", "xls", "xlsx",
    "zip", "tar", "gz", "txt", "csv",
    "png", "jpg", "jpeg", "gif", "webp",
    "mp4", "mp3", "wav",
}


def _allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def _serialize(doc: dict) -> dict:
    doc["_id"] = str(doc["_id"])
    return doc


def _save_upload(file) -> tuple[str, str]:
    """Save uploaded file to GridFS. Returns (file_url, file_type)."""
    ext = file.filename.rsplit(".", 1)[1].lower() if "." in file.filename else "bin"
    filename = f"{uuid.uuid4().hex}.{ext}"
    
    fs = get_fs()
    fs.put(file, filename=filename, content_type=file.content_type)
    
    return f"/uploads/{filename}", ext


def _delete_upload(file_url: str) -> None:
    """Remove a previously uploaded file from GridFS or disk."""
    if not file_url:
        return
    # file_url is like /uploads/<filename>
    filename = file_url.lstrip("/").replace("uploads/", "", 1)
    
    # Try GridFS delete
    try:
        fs = get_fs()
        file = fs.find_one({"filename": filename})
        if file:
            fs.delete(file._id)
            return
    except Exception as e:
        print(f"GridFS Delete Error: {e}")

    # Fallback to local filesystem
    upload_folder = current_app.config["UPLOAD_FOLDER"]
    full_path = os.path.join(upload_folder, filename)
    if os.path.isfile(full_path):
        os.remove(full_path)


# ── Public routes ──────────────────────────────────────────────────────────────

@materials_bp.route("", methods=["GET"])
def get_all():
    """Return all materials, optionally filtered by ?category= (public)."""
    try:
        db = get_db()
        query = {}
        category = request.args.get("category")
        if category:
            query["category"] = category
        docs = list(db.materials.find(query).sort("order", 1))
        return jsonify([_serialize(d) for d in docs]), 200
    except Exception as e:
        return jsonify({"error": "Database unavailable", "details": str(e)}), 503


@materials_bp.route("/categories", methods=["GET"])
def get_categories():
    """Return distinct category strings (public)."""
    try:
        db = get_db()
        categories = db.materials.distinct("category")
        return jsonify(sorted(categories)), 200
    except Exception as e:
        return jsonify({"error": "Database error", "details": str(e)}), 500


# ── Protected routes ───────────────────────────────────────────────────────────

@materials_bp.route("", methods=["POST"])
@require_auth
def create():
    """Create a new material record (protected)."""
    try:
        db = get_db()
        data = request.get_json(force=True)
        data.pop("_id", None)
        data["upload_date"] = datetime.now(timezone.utc).isoformat()
        result = db.materials.insert_one(data)
        doc = db.materials.find_one({"_id": result.inserted_id})
        return jsonify(_serialize(doc)), 201
    except Exception as e:
        return jsonify({"error": "Database error", "details": str(e)}), 500


@materials_bp.route("/upload", methods=["POST"])
@require_auth
def upload_file():
    """Upload a new file; returns { file_url } (protected)."""
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400
    file = request.files["file"]
    if not file.filename:
        return jsonify({"error": "Empty filename"}), 400
    if not _allowed_file(file.filename):
        return jsonify({"error": "File type not allowed"}), 400

    file_url, _ = _save_upload(file)
    return jsonify({"file_url": file_url}), 200


@materials_bp.route("/<id>", methods=["PUT"])
@require_auth
def update(id: str):
    """Update material metadata by _id (protected)."""
    try:
        oid = ObjectId(id)
    except Exception:
        return jsonify({"error": "Invalid id"}), 400

    try:
        db = get_db()
        data = request.get_json(force=True)
        data.pop("_id", None)
        result = db.materials.update_one({"_id": oid}, {"$set": data})
        if result.matched_count == 0:
            return jsonify({"error": "Not found"}), 404

        doc = db.materials.find_one({"_id": oid})
        return jsonify(_serialize(doc)), 200
    except Exception as e:
        return jsonify({"error": "Database error", "details": str(e)}), 500


@materials_bp.route("/<id>/file", methods=["POST"])
@require_auth
def update_file(id: str):
    """Replace the file on an existing material (protected).
    Deletes the old file from disk, uploads the new one, and
    updates file_url + file_type on the document.
    """
    try:
        oid = ObjectId(id)
    except Exception:
        return jsonify({"error": "Invalid id"}), 400

    try:
        db = get_db()
        doc = db.materials.find_one({"_id": oid})
        if not doc:
            return jsonify({"error": "Not found"}), 404

        if "file" not in request.files:
            return jsonify({"error": "No file provided"}), 400
        file = request.files["file"]
        if not file.filename:
            return jsonify({"error": "Empty filename"}), 400
        if not _allowed_file(file.filename):
            return jsonify({"error": "File type not allowed"}), 400

        # Remove old file
        _delete_upload(doc.get("file_url", ""))

        # Save new file
        file_url, file_type = _save_upload(file)

        db.materials.update_one(
            {"_id": oid},
            {"$set": {"file_url": file_url, "file_type": file_type}},
        )
        updated = db.materials.find_one({"_id": oid})
        return jsonify(_serialize(updated)), 200
    except Exception as e:
        return jsonify({"error": "Database error", "details": str(e)}), 500


@materials_bp.route("/<id>", methods=["DELETE"])
@require_auth
def delete(id: str):
    """Delete a material and its associated file from disk (protected)."""
    try:
        oid = ObjectId(id)
    except Exception:
        return jsonify({"error": "Invalid id"}), 400

    try:
        db = get_db()
        doc = db.materials.find_one({"_id": oid})
        if not doc:
            return jsonify({"error": "Not found"}), 404

        # Remove file from disk
        _delete_upload(doc.get("file_url", ""))

        db.materials.delete_one({"_id": oid})
        return jsonify({"message": "Deleted successfully"}), 200
    except Exception as e:
        return jsonify({"error": "Database error", "details": str(e)}), 500
