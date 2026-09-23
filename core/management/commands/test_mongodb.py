"""
Management command to test MongoDB connection and report collection stats.
"""
from django.core.management.base import BaseCommand
from schemesetu.mongodb import get_mongo_client, get_mongo_db

class Command(BaseCommand):
    help = "Test MongoDB connection and display database status."

    def handle(self, *args, **options):
        client = get_mongo_client()
        if client is None:
            self.stdout.write(self.style.WARNING(
                "MongoDB is NOT connected.\n"
                "Please configure MONGODB_URI in your .env file.\n"
                "Example: MONGODB_URI=mongodb+srv://user:pass@cluster.mongodb.net/?retryWrites=true&w=majority"
            ))
            return

        db = get_mongo_db()
        self.stdout.write(self.style.SUCCESS(f"[OK] Successfully connected to MongoDB database '{db.name}'!"))
        collections = db.list_collection_names()
        self.stdout.write(f"Existing collections: {collections if collections else '(None yet)'}")
