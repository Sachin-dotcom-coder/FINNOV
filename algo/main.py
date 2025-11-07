from pymongo import MongoClient
from bson import json_util

# --- Connect to your MongoDB Atlas cluster ---
client = MongoClient("mongodb+srv://Tanishka_1:214365@online.qhnk9zd.mongodb.net/?appName=Online")

# --- Database and collection (from your Compass screenshot) ---
db = client["online_db"]
collection = db["invoices"]

# --- Fetch all invoices ---
invoices = list(collection.find())

# --- Detect duplicates (by invoice_no + gstin) ---
seen = {}
duplicates = []

for entry in invoices:
    key = (entry.get("invoice_no"), entry.get("gstin"))
    if key in seen:
        duplicates.append(entry)
        duplicates.append(seen[key])  # include the first one too
    else:
        seen[key] = entry

# --- Print results cleanly ---
if duplicates:
    print("⚠️ Duplicate invoices found (same invoice_no + gstin):\n")
    handled = set()

    for entry in duplicates:
        key = (entry.get("invoice_no"), entry.get("gstin"))
        if key not in handled:
            # collect all duplicates for that key
            dups = [doc for doc in duplicates if (doc.get("invoice_no"), doc.get("gstin")) == key]
            print(f"📄 Invoice No: {key[0]}, GSTIN: {key[1]} — {len(dups)} duplicates found\n")

            for i, doc in enumerate(dups, start=1):
                print(f"--- Duplicate #{i} ---")
                print(json_util.dumps(doc, indent=4, ensure_ascii=False))
                print()
            handled.add(key)
else:
    print("✅ No duplicate invoices found.")

