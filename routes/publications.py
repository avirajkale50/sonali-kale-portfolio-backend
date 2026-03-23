from bson import ObjectId
from flask import Blueprint, request, jsonify

from auth import require_auth
from db import get_db

publications_bp = Blueprint("publications", __name__)


def _serialize(doc: dict) -> dict:
    doc["_id"] = str(doc["_id"])
    return doc


@publications_bp.route("", methods=["GET"])
def get_all():
    """Return all publications sorted by order (public)."""
    try:
        db = get_db()
        docs = list(db.publications.find({}).sort("order", 1))
        return jsonify([_serialize(d) for d in docs]), 200
    except Exception as e:
        return jsonify({"error": "Database unavailable", "details": str(e)}), 503


@publications_bp.route("", methods=["POST"])
@require_auth
def create():
    """Create a new publication (protected)."""
    try:
        db = get_db()
        data = request.get_json(force=True)
        data.pop("_id", None)
        result = db.publications.insert_one(data)
        doc = db.publications.find_one({"_id": result.inserted_id})
        return jsonify(_serialize(doc)), 201
    except Exception as e:
        return jsonify({"error": "Database error", "details": str(e)}), 500


@publications_bp.route("/<id>", methods=["PUT"])
@require_auth
def update(id: str):
    """Update a publication by _id (protected)."""
    try:
        oid = ObjectId(id)
    except Exception:
        return jsonify({"error": "Invalid id"}), 400

    try:
        db = get_db()
        data = request.get_json(force=True)
        data.pop("_id", None)
        result = db.publications.update_one({"_id": oid}, {"$set": data})
        if result.matched_count == 0:
            return jsonify({"error": "Not found"}), 404

        doc = db.publications.find_one({"_id": oid})
        return jsonify(_serialize(doc)), 200
    except Exception as e:
        return jsonify({"error": "Database error", "details": str(e)}), 500


@publications_bp.route("/<id>", methods=["DELETE"])
@require_auth
def delete(id: str):
    """Delete a publication by _id (protected)."""
    try:
        oid = ObjectId(id)
    except Exception:
        return jsonify({"error": "Invalid id"}), 400

    try:
        db = get_db()
        result = db.publications.delete_one({"_id": oid})
        if result.deleted_count == 0:
            return jsonify({"error": "Not found"}), 404
        return jsonify({"message": "Deleted successfully"}), 200
    except Exception as e:
        return jsonify({"error": "Database error", "details": str(e)}), 500
