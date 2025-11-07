import os
import sys
import json
import re
import time
import csv
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from dotenv import load_dotenv

# ============== CONFIG ======================
load_dotenv()

# MongoDB connection
uri = os.getenv("MONGO_URI")
if not uri:
    print("❌ Error: MONGO_URI not found in .env file")
    sys.exit(1)

try:
    client = MongoClient(uri, server_api=ServerApi('1'))
    client.admin.command('ping')
    print("✅ Connected to MongoDB successfully!")
except Exception as e:
    print(f"❌ Failed to connect to MongoDB: {e}")
    sys.exit(1)

db = client["online_db"]
collection = db["invoices"]

# Vision API key (Landing AI)
vision_api_key = os.getenv("VISION_AGENT_API_KEY")
if not vision_api_key:
    print("❌ Error: VISION_AGENT_API_KEY not found in .env file")
    sys.exit(1)
os.environ["VISION_AGENT_API_KEY"] = vision_api_key

MAX_WORKERS = 3
OUTPUT_JSON = Path("invoice_results.json")
OUTPUT_CSV = Path("invoice_results.csv")
FAILED_JSON = Path("failed_invoices.json")
ALLOWED_EXTS = {".pdf", ".tiff", ".tif", ".png", ".jpg", ".jpeg"}

# ===========================================

def format_num_string(s):
    if s is None:
        return None
    return str(s).replace("₹", "").replace(",", "").strip()

def to_float_safe(s):
    if not s:
        return None
    s2 = str(s).replace("₹", "").replace(",", "").replace(" ", "")
    try:
        return float(s2)
    except:
        return None

def search_first(pattern, text, flags=0):
    if not text:
        return None
    m = re.search(pattern, text, flags)
    if not m:
        return None
    if m.groups():
        for g in m.groups():
            if g:
                return g.strip()
    return m.group(0).strip()

def normalize_gstin_token(tok: str) -> str:
    if not tok:
        return tok
    s = str(tok).upper().replace(" ", "").replace("-", "").strip()
    s = s.replace("O", "0").replace("I", "1").replace("L", "1").replace("S", "5").replace("Z", "2")
    return s

def find_amount_improved(md_text, chunks=None):
    text = md_text or ""
    num_re = re.compile(r'[₹]?\s*[0-9]+(?:[,\s][0-9]{3})*(?:\.[0-9]{1,2})?')
    all_tokens = [(m.start(), m.group(0)) for m in num_re.finditer(text)]
    candidates = []
    for pos, tok in all_tokens:
        val = to_float_safe(tok)
        if val is not None and val > 0.5:
            candidates.append((pos, tok, val))
    if not candidates:
        return None
    decimal_cands = [(p, t, v) for (p, t, v) in candidates if re.search(r'\.\d{1,2}$', t)]
    if decimal_cands:
        total_positions = [m.start() for m in re.finditer(r'\btotal\b', text, flags=re.IGNORECASE)]
        if total_positions:
            best = None
            best_score = -1
            for p, t, v in decimal_cands:
                dist = min([abs(p - tp) for tp in total_positions])
                score = (1000 / (1 + dist)) + v
                if score > best_score:
                    best_score = score
                    best = (t, v)
            if best:
                return format_num_string(best[0])
        decimal_cands.sort(key=lambda x: x[2], reverse=True)
        return format_num_string(decimal_cands[0][1])
    candidates.sort(key=lambda x: x[2], reverse=True)
    return format_num_string(candidates[0][1])

# ✅ NEW FUNCTION — Extract HSN or SAC codes
def extract_hsn_sac(md_text):
    """
    Extract HSN or SAC codes from the document using regex.
    """
    if not md_text:
        return None

    hsn_pattern = re.compile(
        r'\b(?:HSN|SAC|HSN/SAC)\s*(?:Code)?[:\-]?\s*([0-9]{4,8})\b',
        flags=re.IGNORECASE
    )

    codes = hsn_pattern.findall(md_text)
    codes = list(set(codes))  # remove duplicates
    return codes if codes else None

# ===========================================

def process_file(path: Path):
    """
    Process one invoice (PDF/image) and upload data to MongoDB.
    """
    try:
        from pydantic import BaseModel, Field
        from landingai_ade.lib import pydantic_to_json_schema
        from landingai_ade import LandingAIADE
    except Exception as e:
        return {"filename": path.name, "error": f"Import error: {e}"}

    client_ai = LandingAIADE()
    start = time.time()

    try:
        resp = client_ai.parse(document_url=str(path), model="dpt-2-latest")
    except Exception as e:
        return {"filename": path.name, "error": f"parse error: {e}"}

    md = getattr(resp, "markdown", "") or ""
    chunks = getattr(resp, "chunks", None)
    extracted = {}

    try:
        class InvoiceSchema(BaseModel):
            invoice_no: str = Field(description="Invoice number")
            invoice_date: str = Field(description="Invoice date")
            total_amount: str = Field(description="Total amount")
            vendor_name: str = Field(description="Vendor name")
            gstin: str = Field(description="GSTIN", default=None)
            hsn_sac: str = Field(description="HSN or SAC code", default=None)

        schema = pydantic_to_json_schema(InvoiceSchema)
        md_temp = Path(f"{path.stem}__md_temp.md")
        md_temp.write_text(md)
        extract_resp = client_ai.extract(schema=schema, markdown=md_temp, model="extract-latest")

        try:
            md_temp.unlink()
        except:
            pass

        extracted = getattr(extract_resp, "extraction", {}) or {}
    except Exception:
        extracted = {}

    invoice_no = extracted.get("invoice_no") or search_first(
        r'(?:Invoice\s*(?:No\.?|Number)[:\s-]*)([A-Za-z0-9\/\-\._]+)', md
    )
    invoice_date = extracted.get("invoice_date") or search_first(
        r'(\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b)|(\b\d{4}[-/]\d{1,2}[-/]\d{1,2}\b)', md
    )

    gstin = extracted.get("gstin")
    if not gstin:
        m = re.search(r'\b([0-9A-Z]{15})\b', md, flags=re.IGNORECASE)
        if m:
            candidate = normalize_gstin_token(m.group(1))
            if re.match(r'^\d{2}[A-Z0-9]{13}$', candidate):
                gstin = candidate

    vendor = extracted.get("vendor_name") or search_first(
        r'Name\s*[:\-]?\s*([A-Z][A-Za-z0-9\.\,&\(\)\-\/\s]{3,200}?)\s*(?:Address|GSTIN|Bill To|Ship To|State Code|$)',
        md, flags=re.IGNORECASE
    )

    total_amount = extracted.get("total_amount") or find_amount_improved(md, chunks)
    hsn_sac = extracted.get("hsn_sac") or extract_hsn_sac(md)

    elapsed = time.time() - start

    result = {
        "filename": path.name,
        "invoice_no": invoice_no,
        "invoice_date": invoice_date,
        "gstin": gstin,
        "vendor_name": vendor,
        "total_amount": total_amount,
        "hsn_sac": hsn_sac,
        "parse_time_sec": round(elapsed, 2)
    }

    # Always insert (no duplicate filtering)
    try:
        insert_result = collection.insert_one(result)
        result["_id"] = str(insert_result.inserted_id)
        print(f"✅ Inserted {path.name} → MongoDB ID {insert_result.inserted_id}")
    except Exception as e:
        result["error"] = f"MongoDB insert failed: {e}"
        print(f"❌ MongoDB insert failed for {path.name}: {e}")

    return result

# ===========================================

def process_folder(folder: Path, max_workers=MAX_WORKERS):
    files = [p for p in sorted(folder.iterdir()) if p.suffix.lower() in ALLOWED_EXTS]
    if not files:
        print("No invoice files found in", folder)
        return

    print(f"Found {len(files)} invoice files. Processing with {max_workers} workers...")

    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        future_to_path = {ex.submit(process_file, p): p for p in files}
        for future in as_completed(future_to_path):
            try:
                res = future.result()
                results.append(res)
            except Exception as e:
                results.append({"error": str(e)})

    # Save output files
    OUTPUT_JSON.write_text(json.dumps(results, indent=2))

    keys = ["filename", "invoice_no", "invoice_date", "gstin", "vendor_name", "total_amount", "hsn_sac", "parse_time_sec"]
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys, extrasaction='ignore')
        writer.writeheader()
        for r in results:
            writer.writerow(r)

    failed = [r for r in results if "error" in r]
    if failed:
        FAILED_JSON.write_text(json.dumps(failed, indent=2))
        print(f"⚠️ Saved {len(failed)} failed invoices to {FAILED_JSON.resolve()}")

    print(f"✅ Saved JSON to {OUTPUT_JSON.resolve()}")
    print(f"✅ Saved CSV to {OUTPUT_CSV.resolve()}")

# ===========================================

def main():
    if len(sys.argv) < 2:
        print("Usage: python batch_parse_export_to_mongo.py path/to/invoice_folder")
        sys.exit(1)
    folder = Path(sys.argv[1])
    if not folder.exists() or not folder.is_dir():
        print("❌ Provided path is not a folder:", folder)
        sys.exit(1)
    process_folder(folder)

if __name__ == "__main__":
    main()
