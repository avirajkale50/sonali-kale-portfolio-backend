import certifi
import gridfs
from pymongo import MongoClient
from config import Config

_client: MongoClient | None = None
_fs: gridfs.GridFS | None = None


def get_db():
    global _client
    if _client is None:
        try:
            _client = MongoClient(
                Config.MONGO_URI,
                tlsCAFile=certifi.where(),
                tlsAllowInvalidCertificates=True,
                serverSelectionTimeoutMS=Config.DB_TIMEOUT, # Avoid indefinite hanging
            )
            # Test connection immediately
            _client.admin.command('ping')
        except Exception as e:
            print(f"CRITICAL: Failed to connect to MongoDB: {e}")
            _client = None # Reset so it tries again or handled by caller
            raise e
    return _client[Config.DB_NAME]


def get_fs():
    global _fs
    if _fs is None:
        db = get_db()
        _fs = gridfs.GridFS(db)
    return _fs


