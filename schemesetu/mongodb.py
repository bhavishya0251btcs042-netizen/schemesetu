"""
schemesetu/mongodb.py — MongoDB connector and collection manager.
Connects to MongoDB using MONGODB_URI from .env.
Provides helper methods for sync/storing data in MongoDB collections.
"""
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

_mongo_client = None


def get_mongo_client():
    """Returns a PyMongo MongoClient if MONGODB_URI is configured, else None."""
    global _mongo_client
    uri = getattr(settings, "MONGODB_URI", "").strip()
    if not uri:
        return None

    if _mongo_client is None:
        try:
            from pymongo import MongoClient
            _mongo_client = MongoClient(uri, serverSelectionTimeoutMS=5000)
            # Test connection
            _mongo_client.admin.command("ping")
            logger.info("Successfully connected to MongoDB.")
        except Exception as e:
            logger.warning(f"Failed to connect to MongoDB: {e}")
            return None

    return _mongo_client


def get_mongo_db():
    """Returns the MongoDB database instance if connected, else None."""
    client = get_mongo_client()
    if client is not None:
        db_name = getattr(settings, "MONGODB_DB_NAME", "schemesetu")
        return client[db_name]
    return None


def sync_user_to_mongodb(user):
    """Mirror user details to MongoDB 'users' collection."""
    db = get_mongo_db()
    if db is not None:
        try:
            db.users.update_one(
                {"username": user.username},
                {"$set": {
                    "username": user.username,
                    "email": user.email,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "is_active": user.is_active,
                    "date_joined": user.date_joined,
                }},
                upsert=True
            )
            return True
        except Exception as e:
            logger.error(f"MongoDB user sync error: {e}")
    return False


def sync_otp_to_mongodb(email, otp_code, purpose="signup"):
    """Store OTP audit record in MongoDB 'otp_records' collection."""
    db = get_mongo_db()
    if db is not None:
        try:
            from django.utils import timezone
            db.otp_records.insert_one({
                "email": email,
                "otp_code": otp_code,
                "purpose": purpose,
                "created_at": timezone.now(),
            })
            return True
        except Exception as e:
            logger.error(f"MongoDB OTP sync error: {e}")
    return False
