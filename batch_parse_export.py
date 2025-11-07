# batch_parse_export.py


import os
import sys
import json
import re
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed


os.environ.setdefault("VISION_AGENT_API_KEY", "pat_Er3HNIEC0NcI9hrHgRCJDMPvte1pdiao")

MAX_WORKERS = 3

OUTPUT_JSON = Path("invoice_results.json")

ALLOWED_EXTS = {".pdf", ".tiff", ".tif", ".png", ".jpg", ".jpeg"}

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
    """Apply common OCR fixes to GSTIN-like tokens (O->0, I/L->1, S->5, Z->2)."""
    if not tok:
        return tok
    s = str(tok).upper().replace(" ", "").replace("-", "").strip()
    
    s = s.replace("O", "0").replace("I", "1").replace("L", "1").replace("S", "5").replace("Z", "2")
    return s

def find_amount_improved(md_text, chunks=None):
    text = md_text or ""
    # regex tokens
    num_re = re.compile(r'[₹]?\s*[0-9]+(?:[,\s][0-9]{3})*(?:\.[0-9]{1,2})?')
    all_tokens = [(m.start(), m.group(0)) for m in num_re.finditer(text)]
    candidates = []
    for pos, tok in all_tokens:
        val = to_float_safe(tok)
        if val is not None and val > 0.5:
            candidates.append((pos, tok, val))
 
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
    # fallback: largest numeric candidate
    if candidates:
        candidates.sort(key=lambda x: x[2], reverse=True)
        return format_num_string(candidates[0][1])
    return None

def process_file(path: Path):
    """
    Process a single file using Landing AI ADE parse + extract (with fallback).
    Returns a dict (result) for JSON output.
    """
    # local imports
    try:
        from pydantic import BaseModel, Field
        from landingai_ade.lib import pydantic_to_json_schema
        from landingai_ade import LandingAIADE
    except Exception as e:
        return {"filename": path.name, "error": f"Import error: {e}"}

    client = LandingAIADE()

    start = time.time()
    try:
        resp = client.parse(document_url=str(path), model="dpt-2-latest")
    except Exception as e:
        return {"filename": path.name, "error": f"parse error: {e}"}

    md = getattr(resp, "markdown", "") or ""
    chunks = getattr(resp, "chunks", None)

    # Try extract(); if server fails, ignore and fallback to heuristics
    extracted = {}
    try:
        class InvoiceSchema(BaseModel):
            invoice_no: str = Field(description="Invoice number")
            invoice_date: str = Field(description="Invoice date")
            total_amount: str = Field(description="Total amount")
            vendor_name: str = Field(description="Vendor name")
            gstin: str = Field(description="GSTIN", default=None)
        schema = pydantic_to_json_schema(InvoiceSchema)
        # write md to temp file for extract
        md_temp = Path(f"{path.stem}__md_temp.md")
        md_temp.write_text(md)
        extract_resp = client.extract(schema=schema, markdown=md_temp, model="extract-latest")
        # cleanup temp markdown
        try:
            md_temp.unlink()
        except:
            pass
        extracted = getattr(extract_resp, "extraction", {}) or {}
    except Exception:
        # ignore extract errors (server 500 etc)
        extracted = {}

    invoice_no = extracted.get("invoice_no") or search_first(
        r'(?:Invoice\s*(?:No\.?|Number)[:\s-]*)([A-Za-z0-9\/\-\._]+)', md
    )
    invoice_date = extracted.get("invoice_date") or search_first(
        r'(\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b)|(\b\d{4}[-/]\d{1,2}[-/]\d{1,2}\b)', md
    )

    gstin = extracted.get("gstin") if isinstance(extracted, dict) else None

    if not gstin:
        m = re.search(r'\b([0-9A-Z]{15})\b', md, flags=re.IGNORECASE)
        if m:
            candidate = normalize_gstin_token(m.group(1))
            if re.match(r'^\d{2}[A-Z0-9]{13}$', candidate):
                gstin = candidate

    if not gstin and chunks:
        for c in chunks:
            chunk_md = getattr(c, "markdown", "") or ""
            if re.search(r'\bGSTIN\b|\bGSTIN\s*/\b|\bGSTIN\s*:|\bGSTIN\s+Unique', chunk_md, flags=re.IGNORECASE):
                mm = re.search(r'([0-9A-Z]{14,16})', chunk_md.replace(" ", ""))
                if mm:
                    candidate = normalize_gstin_token(mm.group(1))
                    if re.match(r'^\d{2}[A-Z0-9]{13}$', candidate):
                        gstin = candidate
                        break
 
        if not gstin:
            chunk_texts = [getattr(c, "markdown", "") or "" for c in chunks]
            for i, ct in enumerate(chunk_texts):
                if re.search(r'\bGSTIN\b', ct, flags=re.IGNORECASE):
                    for nb in (i - 1, i, i + 1):
                        if 0 <= nb < len(chunk_texts):
                            m2 = re.search(r'([0-9A-Z]{14,16})', chunk_texts[nb].replace(" ", ""))
                            if m2:
                                candidate = normalize_gstin_token(m2.group(1))
                                if re.match(r'^\d{2}[A-Z0-9]{13}$', candidate):
                                    gstin = candidate
                                    break
                if gstin:
                    break

    if not gstin:
        for m in re.finditer(r'\bGSTIN[:\s\-]*([^\s,;]{10,20})', md, flags=re.IGNORECASE):
            cand = normalize_gstin_token(m.group(1))
            if len(cand) >= 15:
                cand = cand[:15]
            if re.match(r'^\d{2}[A-Z0-9]{13}$', cand):
                gstin = cand
                break

    vendor = extracted.get("vendor_name")
    if not vendor:

        if gstin:
            pat = rf'{re.escape(gstin)}\s*[:\-]?\s*Name\s*[:\-]?\s*(.+?)\s*(?:Address|Bill|Ship|State Code|GSTIN|$)'
            vendor = search_first(pat, md, flags=re.IGNORECASE | re.DOTALL)

        if not vendor:
            vendor = search_first(
                r'Name\s*[:\-]?\s*([A-Z][A-Za-z0-9\.\,&\(\)\-\/\s]{3,200}?)\s*(?:Address|GSTIN|Bill To|Ship To|State Code|$)',
                md, flags=re.IGNORECASE
            )

        if not vendor:
            vendor = search_first(r'\b([A-Z][A-Z0-9\.\s,&\-]{6,120})\b', md)

    # ---------------- Amount ----------------
    total_amount = extracted.get("total_amount")
    if not total_amount:
        total_amount = find_amount_improved(md, chunks)

    elapsed = time.time() - start

    result = {
        "filename": path.name,
        "invoice_no": invoice_no,
        "invoice_date": invoice_date,
        "gstin": gstin,
        "vendor_name": vendor,
        "total_amount": total_amount,
        "parse_time_sec": round(elapsed, 2)
    }
    return result

# ---------------- Batch runner ----------------
def process_folder(folder: Path, max_workers=MAX_WORKERS):
    files = [p for p in sorted(folder.iterdir()) if p.suffix.lower() in ALLOWED_EXTS]
    if not files:
        print("No invoice files found in", folder)
        return

    print(f"Found {len(files)} files. Processing with {max_workers} workers...")

    results = []
    # Thread pool for I/O-bound API calls
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        future_to_path = {ex.submit(process_file, p): p for p in files}
        for future in as_completed(future_to_path):
            p = future_to_path[future]
            try:
                res = future.result()
                print(f"[{p.name}] done — invoice_no={res.get('invoice_no')} total={res.get('total_amount')} time={res.get('parse_time_sec')}s")
                results.append(res)
            except Exception as e:
                print(f"[{p.name}] error: {e}")
                results.append({"filename": p.name, "error": str(e)})

    # write final JSON (overwrite with this batch results)
    OUTPUT_JSON.write_text(json.dumps(results, indent=2))
    print(f"Saved results to {OUTPUT_JSON.resolve()}")

# ---------------- CLI ----------------
def main():
    if len(sys.argv) < 2:
        print("Usage: python batch_parse_export.py path/to/invoice_folder")
        sys.exit(1)
    folder = Path(sys.argv[1])
    if not folder.exists() or not folder.is_dir():
        print("Provided path is not a folder:", folder)
        sys.exit(1)
    process_folder(folder, max_workers=MAX_WORKERS)

if __name__ == "__main__":
    main()
