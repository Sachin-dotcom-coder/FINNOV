from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from dotenv import load_dotenv
import os
import re

# Load environment variables (.env should contain MONGO_URI)
load_dotenv()
uri = os.getenv("MONGO_URI")

# Connect to MongoDB
client = MongoClient(uri, server_api=ServerApi('1'))
db = client["online_db"]
collection = db["invoices"]

print("✅ Connected to MongoDB")

# ------------------- Normalize invoice numbers -------------------
def normalize_invoice_no(inv_no):
    """
    Remove slashes, dashes, spaces, and lowercase everything
    so INV-001, INV/001, inv001 all match.
    """
    if not inv_no:
        return None
    return re.sub(r'[^A-Za-z0-9]', '', inv_no).upper().strip()

# ------------------- Step 1: Create a normalized field -------------------
# We'll create (or update) a field 'normalized_invoice_no' for each record
print("🔄 Normalizing invoice numbers...")
for doc in collection.find({}, {"invoice_no": 1}):
    inv_no = doc.get("invoice_no")
    normalized = normalize_invoice_no(inv_no)
    if normalized:
        collection.update_one(
            {"_id": doc["_id"]},
            {"$set": {"normalized_invoice_no": normalized}}
        )

print("✅ Normalization complete.")

# ------------------- Step 2: Find duplicates by normalized_invoice_no -------------------
pipeline = [
    {"$group": {"_id": "$normalized_invoice_no", "count": {"$sum": 1}, "ids": {"$push": "$_id"}}},
    {"$match": {"count": {"$gt": 1}, "_id": {"$ne": None}}}
]

duplicates = list(collection.aggregate(pipeline))

if not duplicates:
    print("🎉 No duplicate invoice numbers found.")
else:
    print(f"⚠️ Found {len(duplicates)} duplicate invoice numbers:\n")
    for dup in duplicates:
        normalized = dup["_id"]
        ids = dup["ids"]
        print(f"Invoice (normalized): {normalized}")
        print("ObjectIDs:", [str(i) for i in ids])
        print("-" * 60)

print("✅ Done checking duplicates.")
