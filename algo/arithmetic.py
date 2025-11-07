from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

# --- Connect to MongoDB ---
uri = "mongodb+srv://Tanishka_1:214365@online.qhnk9zd.mongodb.net/online_db?retryWrites=true&w=majority"
client = MongoClient(uri, server_api=ServerApi('1'))
collection = client["online_db"]["invoices"]

# --- Fetch all invoices ---
invoices = list(collection.find({}))

# --- Validation Parameters ---
tolerance = 1.0  # allow ₹1 difference to account for rounding

# --- Check each invoice ---
for inv in invoices:
    invoice_no = inv.get("invoice_no")
    filename = inv.get("filename")
    gstin = inv.get("gstin")
    taxable = inv.get("taxable_amount")
    total = inv.get("total_amount")
    cgst = inv.get("cgst") or 0
    sgst = inv.get("sgst") or 0
    igst = inv.get("igst") or 0

    # Skip if values are missing
    try:
        taxable = float(str(taxable).replace(",", ""))
        total = float(str(total).replace(",", ""))
        cgst = float(cgst)
        sgst = float(sgst)
        igst = float(igst)
    except (ValueError, TypeError):
        print(f"⚠️ Skipping {filename} — incomplete or invalid numeric fields.")
        continue

    # Calculate expected total
    expected_total = taxable + taxable * ((cgst + sgst + igst) / 100)

    # Check discrepancy
    diff = abs(expected_total - total)

    if diff > tolerance:
        print("🚨 Arithmetic Discrepancy Found:")
        print(f"   • File: {filename}")
        print(f"   • Invoice No: {invoice_no}")
        print(f"   • GSTIN: {gstin}")
        print(f"   • Taxable Amount: {taxable}")
        print(f"   • Total Amount: {total}")
        print(f"   • CGST: {cgst}%  SGST: {sgst}%  IGST: {igst}%")
        print(f"   • Expected Total: {expected_total:.2f}")
        print(f"   • Difference: {diff:.2f}\n")

        # Optionally update DB with flag
        collection.update_one(
            {"_id": inv["_id"]},
            {"$set": {"arithmetic_flag": "Arithmetic_Discrepancy"}}
        )
    else:
        # Optionally mark as accurate
        collection.update_one(
            {"_id": inv["_id"]},
            {"$set": {"arithmetic_flag": "Accurate"}}
        )
