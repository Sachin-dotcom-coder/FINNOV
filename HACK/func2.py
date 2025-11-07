from pymongo import MongoClient

# Connect to MongoDB
client = MongoClient("mongodb://localhost:27017/")  # replace with your actual URI
db = client["your_database_name"]

invoices_collection = db["invoices"]
users_collection = db["users"]

# Create a dictionary of HSN→Tax_Rate for quick lookup
users_data = {doc["HSN_SAC_Code"]: doc["Tax_Rate"] for doc in users_collection.find({})}

flagged_invoices = []

# Loop through invoices and validate
for invoice in invoices_collection.find({}):
    hsn_code = str(invoice.get("hsn"))  # or invoice["hsn_sac_code"] depending on your schema
    cgst_rate = float(invoice.get("cgst", 0))
    invoice_number = invoice.get("invoice_number", "UNKNOWN")

    # Check if HSN exists in users
    if hsn_code in users_data:
        expected_cgst = float(users_data[hsn_code]) / 2
        if abs(expected_cgst - cgst_rate) > 0.01:
            flagged_invoices.append(invoice_number)
            print(f"⚠️ CGST mismatch for Invoice {invoice_number}: Expected {expected_cgst}%, Found {cgst_rate}%")
    else:
        flagged_invoices.append(invoice_number)
        print(f"❌ Missing HSN match for Invoice {invoice_number}: HSN {hsn_code}")

print("\nSummary:")
print(f"Total flagged invoices: {len(flagged_invoices)}")
print(flagged_invoices)
