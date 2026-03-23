import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    MONGO_URI: str = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    DB_NAME: str = os.getenv("DB_NAME", "portfolio_db")
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "changeme")
    ADMIN_EMAIL: str = os.getenv("ADMIN_EMAIL", "admin@example.com")
    ADMIN_PASSWORD: str = os.getenv("ADMIN_PASSWORD", "admin123")
    UPLOAD_FOLDER: str = os.getenv("UPLOAD_FOLDER", "uploads")
    MAX_CONTENT_LENGTH: int = int(os.getenv("MAX_CONTENT_LENGTH", 16 * 1024 * 1024))
    DB_TIMEOUT: int = int(os.getenv("DB_TIMEOUT", 5000))  # Default 5 seconds
