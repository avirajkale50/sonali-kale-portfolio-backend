from bson import ObjectId
from flask import Blueprint, request, jsonify

from auth import require_auth
from db import get_db

education_bp = Blueprint("education", __name__)


def _serialize(doc: dict) -> dict:
    doc["_id"] = str(doc["_id"])
    return doc


@education_bp.route("", methods=["GET"])
def get_all():
    """Return all education records sorted by order (public)."""
    try:
        db = get_db()
        docs = list(db.education.find({}).sort("order", 1))
        return jsonify([_serialize(d) for d in docs]), 200
    except Exception as e:
        return jsonify({"error": "Database unavailable", "details": str(e)}), 503


@education_bp.route("", methods=["POST"])
@require_auth
def create():
    """Create a new education record (protected)."""
    try:
        db = get_db()
        data = request.get_json(force=True)
        data.pop("_id", None)
        result = db.education.insert_one(data)
        doc = db.education.find_one({"_id": result.inserted_id})
        return jsonify(_serialize(doc)), 201
    except Exception as e:
        return jsonify({"error": "Database error", "details": str(e)}), 500


@education_bp.route("/<id>", methods=["PUT"])
@require_auth
def update(id: str):
    """Update an education record by _id (protected)."""
    try:
        oid = ObjectId(id)
    except Exception:
        return jsonify({"error": "Invalid id"}), 400

    try:
        db = get_db()
        data = request.get_json(force=True)
        data.pop("_id", None)
        result = db.education.update_one({"_id": oid}, {"$set": data})
        if result.matched_count == 0:
            return jsonify({"error": "Not found"}), 404

        doc = db.education.find_one({"_id": oid})
        return jsonify(_serialize(doc)), 200
    except Exception as e:
        return jsonify({"error": "Database error", "details": str(e)}), 500


@education_bp.route("/<id>", methods=["DELETE"])
@require_auth
def delete(id: str):
    """Delete an education record by _id (protected)."""
    try:
        oid = ObjectId(id)
    except Exception:
        return jsonify({"error": "Invalid id"}), 400

    try:
        db = get_db()
        result = db.education.delete_one({"_id": oid})
        if result.deleted_count == 0:
            return jsonify({"error": "Not found"}), 404
        return jsonify({"message": "Deleted successfully"}), 200
    except Exception as e:
        return jsonify({"error": "Database error", "details": str(e)}), 500
