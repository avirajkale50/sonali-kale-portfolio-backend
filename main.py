import os

from flask import Flask, send_from_directory, jsonify
from flask_cors import CORS

from config import Config


def create_app() -> Flask:
    app = Flask(__name__)

    # ── Config ────────────────────────────────────────────────────────────────
    app.config["UPLOAD_FOLDER"] = os.path.join(
        os.path.dirname(__file__), Config.UPLOAD_FOLDER
    )
    app.config["MAX_CONTENT_LENGTH"] = Config.MAX_CONTENT_LENGTH

    # ── CORS ──────────────────────────────────────────────────────────────────
    CORS(
        app,
        resources={r"/api/*": {"origins": ["http://localhost:5173", "http://127.0.0.1:5173"]}},
        supports_credentials=True,
    )

    # ── Blueprints ────────────────────────────────────────────────────────────
    from routes.auth import auth_bp
    from routes.profile import profile_bp
    from routes.education import education_bp
    from routes.publications import publications_bp
    from routes.projects import projects_bp
    from routes.materials import materials_bp
    from routes.certificates import certificates_bp
    from routes.gallery import gallery_bp
    from routes.experience import experience_bp

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(profile_bp, url_prefix="/api/profile")
    app.register_blueprint(education_bp, url_prefix="/api/education")
    app.register_blueprint(publications_bp, url_prefix="/api/publications")
    app.register_blueprint(projects_bp, url_prefix="/api/projects")
    app.register_blueprint(materials_bp, url_prefix="/api/materials")
    app.register_blueprint(certificates_bp, url_prefix="/api/certificates")
    app.register_blueprint(gallery_bp, url_prefix="/api/gallery")
    app.register_blueprint(experience_bp, url_prefix="/api/experience")

    # ── Serve uploaded files ──────────────────────────────────────────────────
    @app.route("/uploads/<path:filename>")
    def uploaded_file(filename):
        from db import get_fs
        from flask import Response
        import gridfs

        try:
            fs = get_fs()
            # Try to find in GridFS first
            file = fs.find_one({"filename": filename})
            if file:
                return Response(file.read(), mimetype=file.content_type or "image/jpeg")
        except Exception as e:
            print(f"GridFS Error: {e}")

        # Fallback to local filesystem
        return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

    # ── Health check ──────────────────────────────────────────────────────────
    @app.route("/api/health")
    def health():
        return jsonify({"status": "ok"}), 200

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=8000, debug=True)
