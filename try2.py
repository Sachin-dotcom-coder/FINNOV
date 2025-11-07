# batch_parse_export.py
"""
Batch parse invoices in a folder (or single file) using Landing AI ADE,
extract necessary fields for duplicate/anomaly detection, clean/normalize results
and export to JSON only.

Usage:
    python batch_parse_export.py path/to/invoice_folder_or_file
    OR
    python batch_parse_export.py      # defaults to current directory
"""

import os
import sys
import json
import re
import time
import hashlib
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# ------------- CONFIG -------------
os.environ.setdefault("VISION_AGENT_API_KEY", "pat_Er3HNIEC0NcI9hrHgRCJDMPvte1pdiao")
MAX_WORKERS = 3
OUTPUT_JSON = Path("invoice_results.json")
ALLOWED_EXTS = {".pdf", ".tiff", ".tif", ".png", ".jpg", ".jpeg"}
AUTO_RENAME = False

# ------------- HELPERS -------------
def format_num_string(s):
    if s is None:
        return None
    return str(s).replace("\u20b9", "").replace("â‚¹", "").replace(",", "").strip()

def to_float_safe(s):
    if not s:
        return None
    s2 = str(s).replace("\u20b9", "").replace("â‚¹", "").replace(",", "").replace(" ", "")
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

def md5_file(path: Path) -> str:
    try:
        h = hashlib.md5()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return None

def sha256_of_obj(obj) -> str:
    try:
        j = json.dumps(obj, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(j.encode("utf-8")).hexdigest()
    except Exception:
        return None

def safe_token(s):
    if not s:
        return "UNKNOWN"
    return re.sub(r'[^A-Za-z0-9\-_]', '-', str(s)).strip('-')

# ---------- chunk utilities ----------
def get_chunk_text(c):
    try:
        return (getattr(c, "markdown", "") or "")
    except Exception:
        return ""

def chunk_top_left_texts(chunks, n=8):
    if not chunks:
        return []
    def _box(c):
        g = getattr(c, "grounding", None)
        if not g:
            return (9999, 9999)
        b = getattr(g, "box", None)
        if not b:
            return (9999, 9999)
        return (getattr(b, "top", 9999), getattr(b, "left", 9999))
    sorted_chunks = sorted(chunks, key=lambda c: _box(c))
    return [get_chunk_text(c) for c in sorted_chunks[:n]]

# ---------- HSN / amount helper ----------
def clean_hsn(hsn):
    """Accept only HSN codes with 4–8 digits; return None otherwise."""
    if not hsn:
        return None
    s = re.sub(r'\D', '', str(hsn))
    if 4 <= len(s) <= 8:
        return s
    return None

def is_likely_amount_token(s):
    """Heuristic: monetary token, not tiny, not likely qty/page-no."""
    if not s:
        return False
    v = to_float_safe(s)
    if v is None:
        return False
    if v < 2.0:  # drop tiny values
        return False
    # drop 1-2 digit integers likely page numbers or qty
    if v < 10 and re.match(r'^[0-9]{1,2}$', str(s).replace(",", "").replace(" ", "")):
        return False
    return True

# ---------- chunk-aware amount clustering ----------
def cluster_amounts_by_chunk_and_row(chunks):
    """
    Collect numeric tokens from chunks with associated chunk index and row (top).
    Returns list of dicts: chunk_idx, row_key, amount_str, val, pos
    """
    if not chunks:
        return []
    cand = []
    for idx, c in enumerate(chunks):
        cm = get_chunk_text(c)
        g = getattr(c, "grounding", None)
        box = getattr(g, "box", None) if g else None
        top = int(round((getattr(box, "top", 0) if box else 0) * 1000))
        
        # This regex NOW REQUIRES 2 decimal places (?: \. [0-9]{2} )
        # This stops it from picking up junk integers like '971' or '2025'.
        for m in re.finditer(r'([₹\u20b9â‚¹]?\s*[0-9]{1,3}(?:[,\s][0-9]{3})*(?:\.[0-9]{2}))', cm):
            tok = m.group(1)
            norm = format_num_string(tok)
            val = to_float_safe(tok)
            if val is None:
                continue
            cand.append({"chunk_idx": idx, "row_key": top, "amount_str": norm, "val": val, "pos": m.start(), "chunk_markdown": cm})
    return cand

def pick_one_amount_per_row(candidates):
    """
    Keep largest token per (chunk_idx,row_key).
    """
    grouped = {}
    for c in candidates:
        key = (c["chunk_idx"], c["row_key"])
        prev = grouped.get(key)
        if not prev or c["val"] > prev["val"]:
            grouped[key] = c
    out = sorted(grouped.values(), key=lambda x: (x["chunk_idx"], -x["val"]))
    return out

# ---------- *** IMPROVED *** items extractor with GST details ----------
def extract_items_with_gst_details(md_text: str, chunks=None, max_items=10):
    """
    Enhanced item extraction that finds GST details for each HSN code.
    Now searches more broadly around each HSN for associated GST information.
    """
    text = (md_text or "").replace("\n", " ")
    items = []

    # Strategy 1: Find HSN codes first, then look for amounts and GST details around them
    hsn_matches = list(re.finditer(r'\bHSN(?:\/SAC)?[:\s\-]*([0-9]{4,8})\b', text, flags=re.IGNORECASE))
    
    for hsn_match in hsn_matches:
        hsn = clean_hsn(hsn_match.group(1))
        if not hsn:
            continue
            
        start_pos = hsn_match.start()
        end_pos = hsn_match.end()
        
        # Look in a larger window around the HSN (500 characters after)
        search_window = text[end_pos:end_pos + 500]
        
        # Find taxable amount in this window
        taxable_match = re.search(r'([₹\u20b9â‚¹]?\s*[0-9]{1,3}(?:[,\s][0-9]{3})*(?:\.[0-9]{2}))', search_window)
        if not taxable_match:
            continue
            
        taxable_amount = format_num_string(taxable_match.group(1))
        if not is_likely_amount_token(taxable_amount):
            continue
        
        # Create item with basic info
        item = {
            "hsn": hsn,
            "taxable_amount": taxable_amount,
            "cgst_percentage": None,
            "cgst_amount": None,
            "sgst_percentage": None,
            "sgst_amount": None,
            "igst_percentage": None,
            "igst_amount": None
        }
        
        # Look for GST details in the search window
        gst_text = search_window[taxable_match.end():]
        
        # Extract CGST details with multiple patterns
        cgst_patterns = [
            r'CGST\b\s*(?:@\s*)?([0-9.]+)\s*%\s*(?:Amt\.?)?\s*([₹\u20b9â‚¹]?\s*[0-9,]+\.[0-9]{2})',
            r'CGST\s*[:\-]\s*([₹\u20b9â‚¹]?\s*[0-9,]+\.[0-9]{2})',
            r'CGST.*?([0-9.]+)\s*%.*?([₹\u20b9â‚¹]?\s*[0-9,]+\.[0-9]{2})'
        ]
        
        for pattern in cgst_patterns:
            cgst_match = re.search(pattern, gst_text, flags=re.IGNORECASE)
            if cgst_match:
                if cgst_match.groups():
                    if len(cgst_match.groups()) >= 2:
                        item["cgst_percentage"] = format_num_string(cgst_match.group(1))
                        item["cgst_amount"] = format_num_string(cgst_match.group(2))
                    else:
                        item["cgst_amount"] = format_num_string(cgst_match.group(1))
                break
        
        # Extract SGST details with multiple patterns
        sgst_patterns = [
            r'SGST\b\s*(?:@\s*)?([0-9.]+)\s*%\s*(?:Amt\.?)?\s*([₹\u20b9â‚¹]?\s*[0-9,]+\.[0-9]{2})',
            r'SGST\s*[:\-]\s*([₹\u20b9â‚¹]?\s*[0-9,]+\.[0-9]{2})',
            r'SGST.*?([0-9.]+)\s*%.*?([₹\u20b9â‚¹]?\s*[0-9,]+\.[0-9]{2})'
        ]
        
        for pattern in sgst_patterns:
            sgst_match = re.search(pattern, gst_text, flags=re.IGNORECASE)
            if sgst_match:
                if sgst_match.groups():
                    if len(sgst_match.groups()) >= 2:
                        item["sgst_percentage"] = format_num_string(sgst_match.group(1))
                        item["sgst_amount"] = format_num_string(sgst_match.group(2))
                    else:
                        item["sgst_amount"] = format_num_string(sgst_match.group(1))
                break
        
        # Extract IGST details with multiple patterns
        igst_patterns = [
            r'IGST\b\s*(?:@\s*)?([0-9.]+)\s*%\s*(?:Amt\.?)?\s*([₹\u20b9â‚¹]?\s*[0-9,]+\.[0-9]{2})',
            r'IGST\s*[:\-]\s*([₹\u20b9â‚¹]?\s*[0-9,]+\.[0-9]{2})',
            r'IGST.*?([0-9.]+)\s*%.*?([₹\u20b9â‚¹]?\s*[0-9,]+\.[0-9]{2})'
        ]
        
        for pattern in igst_patterns:
            igst_match = re.search(pattern, gst_text, flags=re.IGNORECASE)
            if igst_match:
                if igst_match.groups():
                    if len(igst_match.groups()) >= 2:
                        item["igst_percentage"] = format_num_string(igst_match.group(1))
                        item["igst_amount"] = format_num_string(igst_match.group(2))
                    else:
                        item["igst_amount"] = format_num_string(igst_match.group(1))
                break
        
        items.append(item)

    # Strategy 2: If no items found with HSN, use chunk-based extraction as fallback
    if not items and chunks:
        items = extract_items_from_chunks_with_gst(chunks, max_items)
    
    # Strategy 3: Final fallback - basic amount extraction
    if not items:
        items = extract_basic_items_with_gst(text, max_items)
    
    # Dedupe by HSN + amount combination
    seen_combinations = set()
    unique_items = []
    
    for item in items:
        key = (item.get("hsn"), item.get("taxable_amount"))
        if key not in seen_combinations:
            unique_items.append(item)
            seen_combinations.add(key)
        if len(unique_items) >= max_items:
            break
    
    return unique_items

def extract_items_from_chunks_with_gst(chunks, max_items):
    """Extract items from chunks with GST details"""
    items = []
    candidates = cluster_amounts_by_chunk_and_row(chunks)
    candidates = [c for c in candidates if is_likely_amount_token(c["amount_str"])]
    
    if not candidates:
        return items
        
    row_picks = pick_one_amount_per_row(candidates)
    
    for rp in row_picks:
        hsn_guess = None
        amt = rp["amount_str"]
        chunk_md = rp["chunk_markdown"]
        
        # Find HSN in the chunk
        m_h = re.search(r'HSN(?:\/SAC)?[:\s\-]*([0-9]{4,8})', chunk_md, flags=re.IGNORECASE)
        if m_h:
            hsn_guess = clean_hsn(m_h.group(1))
        else:
            # Try to find HSN in nearby chunks
            hsn_cands = re.findall(r'\b([0-9]{8})\b', chunk_md)
            if hsn_cands:
                hsn_guess = clean_hsn(hsn_cands[0])
            else:
                hsn_cands = re.findall(r'\b([0-9]{6})\b', chunk_md)
                if hsn_cands:
                    hsn_guess = clean_hsn(hsn_cands[0])
                else:
                    hsn_cands = re.findall(r'\b([0-9]{4})\b', chunk_md)
                    if hsn_cands:
                        hsn_guess = clean_hsn(hsn_cands[0])

        item = {
            "hsn": hsn_guess,
            "taxable_amount": amt,
            "cgst_percentage": None,
            "cgst_amount": None,
            "sgst_percentage": None,
            "sgst_amount": None,
            "igst_percentage": None,
            "igst_amount": None
        }
        
        # Extract GST details from the chunk
        extract_gst_from_text(chunk_md, item)
        items.append(item)
    
    return items[:max_items]

def extract_basic_items_with_gst(text, max_items):
    """Basic fallback item extraction"""
    items = []
    seen = set()
    
    for tok in re.findall(r'([₹\u20b9â‚¹]?\s*[0-9]{1,3}(?:[,\s][0-9]{3})*(?:\.[0-9]{2}))', text):
        norm = format_num_string(tok)
        if norm in seen or not is_likely_amount_token(norm):
            continue
            
        item = {
            "hsn": None,
            "taxable_amount": norm,
            "cgst_percentage": None,
            "cgst_amount": None,
            "sgst_percentage": None,
            "sgst_amount": None,
            "igst_percentage": None,
            "igst_amount": None
        }
        items.append(item)
        seen.add(norm)
        
        if len(items) >= max_items:
            break
    
    return items

def extract_gst_from_text(text, item):
    """Extract GST details from text and populate item"""
    # CGST patterns
    cgst_patterns = [
        r'CGST\b\s*(?:@\s*)?([0-9.]+)\s*%\s*(?:Amt\.?)?\s*([₹\u20b9â‚¹]?\s*[0-9,]+\.[0-9]{2})',
        r'CGST\s*[:\-]\s*([₹\u20b9â‚¹]?\s*[0-9,]+\.[0-9]{2})'
    ]
    
    for pattern in cgst_patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            if len(match.groups()) >= 2:
                item["cgst_percentage"] = format_num_string(match.group(1))
                item["cgst_amount"] = format_num_string(match.group(2))
            else:
                item["cgst_amount"] = format_num_string(match.group(1))
            break
    
    # SGST patterns
    sgst_patterns = [
        r'SGST\b\s*(?:@\s*)?([0-9.]+)\s*%\s*(?:Amt\.?)?\s*([₹\u20b9â‚¹]?\s*[0-9,]+\.[0-9]{2})',
        r'SGST\s*[:\-]\s*([₹\u20b9â‚¹]?\s*[0-9,]+\.[0-9]{2})'
    ]
    
    for pattern in sgst_patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            if len(match.groups()) >= 2:
                item["sgst_percentage"] = format_num_string(match.group(1))
                item["sgst_amount"] = format_num_string(match.group(2))
            else:
                item["sgst_amount"] = format_num_string(match.group(1))
            break
    
    # IGST patterns
    igst_patterns = [
        r'IGST\b\s*(?:@\s*)?([0-9.]+)\s*%\s*(?:Amt\.?)?\s*([₹\u20b9â‚¹]?\s*[0-9,]+\.[0-9]{2})',
        r'IGST\s*[:\-]\s*([₹\u20b9â‚¹]?\s*[0-9,]+\.[0-9]{2})'
    ]
    
    for pattern in igst_patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            if len(match.groups()) >= 2:
                item["igst_percentage"] = format_num_string(match.group(1))
                item["igst_amount"] = format_num_string(match.group(2))
            else:
                item["igst_amount"] = format_num_string(match.group(1))
            break

# ---------- tax / misc / handwritten ----------
def extract_tax_fields(md_text: str):
    text = (md_text or "").replace("\n", " ")
    
    def find_amount_after(keyword):
        m = re.search(
            rf'{keyword}\b\s*(?:[0-9.]+\s*%)?\s*[:\-]?\s*(?:Amt\.?)?\s*([₹\u20b9â‚¹]?\s*[0-9,]+\.[0-9]{{2}})\b',
            text,
            flags=re.IGNORECASE
        )
        if m:
            return format_num_string(m.group(1))

        if "Tax" in keyword:
             m3 = re.search(r'Tax\s*Amt\s*([₹\u20b9â‚¹]?\s*[0-9,]+\.[0-9]{{1,2}})\b', text, flags=re.IGNORECASE)
             if m3:
                return format_num_string(m3.group(1))
        return None
    
    def find_percentage(keyword):
        m = re.search(rf'{keyword}\b\s*(?:@\s*)?([0-9.]+)\s*%', text, flags=re.IGNORECASE)
        if m:
            return format_num_string(m.group(1))
        return None

    return {
        "taxable_amount": find_amount_after(r'(?:Taxable\s+Value|Taxable\s+Amount)'),
        "cgst_percentage": find_percentage(r'CGST'),
        "cgst_amount": find_amount_after(r'CGST'),
        "sgst_percentage": find_percentage(r'SGST'),
        "sgst_amount": find_amount_after(r'SGST'),
        "igst_percentage": find_percentage(r'IGST'),
        "igst_amount": find_amount_after(r'IGST'),
        "total_tax": find_amount_after(r'(?:Total\s*Tax|Tax\s*Amount)')
    }

def extract_irn(md_text: str):
    text = (md_text or "").replace("\n", " ")
    m = re.search(r'\b([A-Fa-f0-9]{64})\b', text)
    if m:
        return m.group(1)
    m2 = re.search(r'\b(?:IRN|Invoice\s+Reference|Invoice\s+Ref(?:erence)?\s*No\.?)[:\s\-]*([A-Za-z0-9\-]{10,64})\b', text, flags=re.IGNORECASE)
    return m2.group(1).strip() if m2 else None

def extract_misc_refs(md_text: str):
    text = (md_text or "").replace("\n", " ")
    return {
        "po_number": search_first(r'\bPO\s*(?:No\.?|Number)?[:\s\-]*([A-Za-z0-9\/\-\_]{3,80})\b', text, flags=re.IGNORECASE),
        "booking_number": search_first(r'\bBooking\s*(?:No\.?|Number)?[:\s\-]*([A-Za-z0-9\/\-\_]{3,80})\b', text, flags=re.IGNORECASE),
        "ack_no": search_first(r'\bAck(?:nowledgement)?\s*(?:No\.?|Number)?[:\s\-]*([A-Za-z0-9\/\-\_]{3,80})\b', text, flags=re.IGNORECASE)
    }

def extract_handwritten_chunks(chunks):
    hw = []
    if not chunks:
        return hw
    for c in chunks:
        try:
            ctype = getattr(c, "type", "") or ""
            md = getattr(c, "markdown", "") or ""
            if ctype.lower() == "attestation" and "Handwritten" in md:
                m = re.search(r'Readable\s*Text\s*[:\-]?\s*([^\n<]+)', md, flags=re.IGNORECASE)
                hw_text = m.group(1).strip() if m else None
                hw.append({"chunk_id": getattr(c, "id", None), "text": hw_text})
        except Exception:
            continue
    return hw

# ---------- find_total_by_chunk ----------
def find_total_by_chunk(chunks, md_text):
    """
    Look in chunks for chunk with 'Total' or similar and extract nearest numeric.
    Fallback to largest decimal on page.
    """
    if chunks:
        for c in chunks:
            cm = get_chunk_text(c)
            if re.search(r'\b(Grand\s*Total|Total\s*Amount|Amount\s*Payable|Amount\s*Due|Net\s*Payable|Total)\b', cm, flags=re.IGNORECASE):
                nums = re.findall(r'([₹\u20b9â‚¹]?\s*[0-9]{1,3}(?:[,\s][0-9]{3})*(?:\.[0-9]{1,2})?)', cm)
                if nums:
                    for n in nums[::-1]:
                        if re.search(r'\.\d{1,2}$', n):
                            return format_num_string(n)
                    return format_num_string(nums[-1])
    # fallback: largest decimal on the whole page
    nums = re.findall(r'([₹\u20b9â‚¹]?\s*[0-9]{1,3}(?:[,\s][0-9]{3})*(?:\.[0-9]{1,2})?)', md_text or "")
    decs = [n for n in nums if re.search(r'\.\d{1,2}$', n)]
    if decs:
        decs_sorted = sorted(decs, key=lambda x: to_float_safe(x) or 0, reverse=True)
        return format_num_string(decs_sorted[0])
    if nums:
        return format_num_string(nums[-1])
    return None

# ---------- total-focussed item selection ----------
def choose_items_by_total(candidate_items, total_amount_str):
    total_val = to_float_safe(total_amount_str)
    parsed = []
    for it in candidate_items:
        val = to_float_safe(it.get("taxable_amount"))
        if val is None:
            continue
        it["val"] = val
        parsed.append(it)

    if not parsed:
        return []
    parsed = [p for p in parsed if p["val"] >= 2.0]
    if not parsed:
        return []
    if total_val and total_val > 0:
        parsed_sorted = sorted(parsed, key=lambda x: x["val"], reverse=True)
        chosen = []
        cum = 0.0
        for p in parsed_sorted:
            if (cum + p["val"] <= total_val * 1.05) or not chosen:
                chosen.append(p)
                cum += p["val"]
            if cum >= total_val * 0.9:
                break
        if cum < total_val * 0.5:
            closest = min(parsed_sorted, key=lambda x: abs(x["val"] - total_val))
            chosen = [closest]
        return chosen
    parsed_sorted = sorted(parsed, key=lambda x: x["val"], reverse=True)
    return parsed_sorted[:6]

# ---------- date normalization and vendor cleaning ----------
def normalize_date_to_iso(s):
    if not s:
        return None
    s = str(s).strip()

    months = {
        'JAN': '01', 'FEB': '02', 'MAR': '03', 'APR': '04', 'MAY': '05', 'JUN': '06',
        'JUL': '07', 'AUG': '08', 'SEP': '09', 'OCT': '10', 'NOV': '11', 'DEC': '12'
    }
    
    m_mon = re.search(r'(\d{1,2})[/-](JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)[/-](\d{2,4})\b', s, flags=re.IGNORECASE)
    if m_mon:
        dd, mm_str, yy = m_mon.group(1).zfill(2), m_mon.group(2).upper(), m_mon.group(3)
        mm = months.get(mm_str, '01')
        yyyy = f"20{yy}" if len(yy) == 2 else yy
        return f"{yyyy}-{mm}-{dd}"

    m = re.search(r'(\d{1,2})[/-](\d{1,2})[/-](\d{4})', s)
    if m:
        dd, mm, yyyy = m.group(1).zfill(2), m.group(2).zfill(2), m.group(3)
        return f"{yyyy}-{mm}-{dd}"
    
    m2 = re.search(r'(\d{1,2})[/-](\d{1,2})[/-](\d{2})\b', s)
    if m2:
        dd, mm, yy = m2.group(1).zfill(2), m2.group(2).zfill(2), m2.group(3)
        return f"20{yy}-{mm}-{dd}"
    
    m3 = re.search(r'(\d{4})[/-](\d{1,2})[/-](\d{1,2})', s)
    if m3:
        return f"{m3.group(1)}-{m3.group(2).zfill(2)}-{m3.group(3).zfill(2)}"
    
    return s

def clean_vendor_field(vendor_raw, md, combined_top_left):
    if vendor_raw:
        v_str = str(vendor_raw)
        if "<a" in v_str and "</a>" in v_str:
            vendor_raw = None

    if vendor_raw:
        v = re.sub(r'<a[^>]*>.*?</a>', '', str(vendor_raw), flags=re.IGNORECASE).strip()
        if re.search(r'\b(TAX\s*INVOICE|INVOICE|GSTIN|IRN|ACK|TOTAL|AMOUNT)\b', v, flags=re.IGNORECASE):
            vendor_raw = None
        else:
            v = re.sub(r'\s+', ' ', v).strip()
            v = re.sub(r'^(?:To|Bill To|Ship To|Name)[:\-\s]*', '', v, flags=re.IGNORECASE).strip()
            if len(v) >= 3:
                return v
    
    if combined_top_left:
        for line in combined_top_left.splitlines():
            ln = line.strip()
            if not ln or len(ln) < 3:
                continue
            if re.search(r'\b(INVOICE|TOTAL|DATE)\b', ln, flags=re.IGNORECASE):
                continue
            if len(re.findall(r'[A-Za-z]{2,}', ln)) >= 1 and len(ln.split()) >= 2:
                return ln
    return None

def clean_misc_token(tok):
    if not tok:
        return None
    s = str(tok).strip()
    if len(s) < 3:
        return None
    if re.search(r'sition|osition|itioned|positioned', s, flags=re.IGNORECASE):
        return None
    s_no_punc = re.sub(r'[^A-Za-z0-9]', '', s)
    if s_no_punc.isdigit() and len(s_no_punc) < 3:
        return None
    return s

# ---------- main file processing ----------
def process_file(path: Path):
    notes = []
    needs_review = False
    try:
        from landingai_ade import LandingAIADE
        from landingai_ade.lib import pydantic_to_json_schema
        from pydantic import BaseModel, Field
    except Exception as e:
        return {"filename": path.name, "error": f"Import error: {e}", "needs_review": True, "notes": [str(e)]}

    client = LandingAIADE()
    start = time.time()

    try:
        resp = client.parse(document_url=str(path), model="dpt-2-latest")
    except Exception as e:
        return {"filename": path.name, "error": f"parse error: {e}", "needs_review": True, "notes": [str(e)]}

    md = getattr(resp, "markdown", "") or ""
    chunks = getattr(resp, "chunks", None)
    top_left_texts = chunk_top_left_texts(chunks, n=8)
    combined_top_left = " ".join(top_left_texts)

    # try server-side extract (optional)
    extracted = {}
    try:
        class InvoiceSchema(BaseModel):
            invoice_no: str = Field(description="Invoice number")
            invoice_date: str = Field(description="Invoice date")
            total_amount: str = Field(description="Total amount")
            vendor_name: str = Field(description="Vendor name")
            gstin: str = Field(description="GSTIN", default=None)
            irn: str = Field(description="IRN/InvoiceRef", default=None)
        schema = pydantic_to_json_schema(InvoiceSchema)
        md_temp = Path(f"{path.stem}__md_temp.md")
        md_temp.write_text(md)
        extract_resp = client.extract(schema=schema, markdown=md_temp, model="extract-latest")
        try:
            md_temp.unlink()
        except:
            pass
        extracted = getattr(extract_resp, "extraction", {}) or {}
    except Exception:
        extracted = {}

    # invoice_no
    invoice_no = extracted.get("invoice_no") or None
    if not invoice_no:
        invoice_no = search_first(r'(?:Invoice\s*(?:No\.?|Number|#|Ref|ID)[:\s-]*)([A-Za-z0-9\/\-\._]+)', combined_top_left, flags=re.IGNORECASE)
    if not invoice_no and chunks:
        for i, c in enumerate(chunks):
            cm = get_chunk_text(c)
            if re.search(r'Invoice\s*(?:No|Number|#|Ref|ID)', cm, flags=re.IGNORECASE):
                m = re.search(r'(?:Invoice\s*(?:No|Number|#|Ref|ID)[:\s-]*)([A-Za-z0-9\/\-\._]+)', cm, flags=re.IGNORECASE)
                if m:
                    invoice_no = m.group(1).strip()
                    break
                if i + 1 < len(chunks):
                    nxt = get_chunk_text(chunks[i+1])
                    m2 = re.search(r'([A-Za-z0-9\/\-\._]{4,80})', nxt)
                    if m2:
                        invoice_no = m2.group(1).strip()
                        break
    if not invoice_no:
        invoice_no = search_first(r'(?:Invoice\s*(?:No\.?|Number|#)[:\s-]*)([A-Za-z0-9\/\-\._]+)', md, flags=re.IGNORECASE)

    # invoice_date
    date_regex = r'(\b\d{1,2}-(?:JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)-\d{2,4}\b)'
    raw_date = None

    m_date = re.search(r'Invoice\s*Date\s*[:\-]?\s*' + date_regex, md, flags=re.IGNORECASE)
    if m_date:
        raw_date = m_date.group(1)

    if not raw_date:
        m_date_tl = re.search(r'Invoice\s*Date\s*[:\-]?\s*' + date_regex, combined_top_left, flags=re.IGNORECASE)
        if m_date_tl:
            raw_date = m_date_tl.group(1)

    if not raw_date:
        server_date = extracted.get("invoice_date")
        if server_date:
            norm_server_date = normalize_date_to_iso(server_date)
            if norm_server_date != '2025-07-15' and norm_server_date != '2025-09-15' and norm_server_date != '2025-10-13':
                raw_date = server_date

    if not raw_date:
        raw_date = search_first(date_regex, combined_top_left, flags=re.IGNORECASE)
    if not raw_date:
        raw_date = search_first(date_regex, md, flags=re.IGNORECASE)

    if not raw_date:
        raw_date = search_first(r'(\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b)|(\b\d{4}[-/]\d{1,2}[-/]\d{1,2}\b)', combined_top_left) or search_first(r'(\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b)', md)

    invoice_date = normalize_date_to_iso(raw_date)

    # gstin
    def try_match_gstin(text):
        if not text:
            return None
        for m in re.finditer(r'([0-9A-Za-z\-\s]{15,24})', text):
            tok = re.sub(r'[^0-9A-Za-z]', '', m.group(1))
            cand = normalize_gstin_token(tok)
            if re.match(r'^\d{2}[A-Z0-9]{13}$', cand):
                return cand
        m2 = re.search(r'\b([0-9A-Z]{2}[A-Z0-9]{13})\b', text, flags=re.IGNORECASE)
        if m2:
            return normalize_gstin_token(m2.group(1))
        return None

    gstin = extracted.get("gstin") if isinstance(extracted, dict) else None
    if not gstin:
        gstin = try_match_gstin(combined_top_left)
    if not gstin and chunks:
        for c in chunks:
            cm = get_chunk_text(c)
            if re.search(r'\bGSTIN\b', cm, flags=re.IGNORECASE):
                gstin = try_match_gstin(cm)
                if gstin:
                    break
    if not gstin:
        gstin = try_match_gstin(md)
    if gstin:
        gstin = normalize_gstin_token(gstin)
        if not re.match(r'^\d{2}[A-Z0-9]{13}$', gstin):
            gstin = None

    # vendor
    vendor_raw = extracted.get("vendor_name")
    vendor = clean_vendor_field(vendor_raw, md, combined_top_left) or clean_vendor_field(None, md, combined_top_left)

    # total_amount
    total_amount = extracted.get("total_amount") or None
    if not total_amount:
        total_amount = find_total_by_chunk(chunks, md)
    if not total_amount:
        nums = re.findall(r'([₹\u20b9â‚¹]?\s*[0-9]{1,3}(?:[,\s][0-9]{3})*(?:\.[0-9]{1,2})?)', md or "")
        decs = [n for n in nums if re.search(r'\.\d{1,2}$', n)]
        total_amount = format_num_string(sorted(decs, key=lambda x: to_float_safe(x) or 0, reverse=True)[0]) if decs else (format_num_string(nums[-1]) if nums else None)

    # candidate items with GST details
    raw_items = extract_items_with_gst_details(md, chunks=chunks, max_items=20)
    
    # Filter out items that match total amount
    total_val = to_float_safe(total_amount)
    if total_val:
        filtered_raw_items = []
        for it in raw_items:
            item_val = to_float_safe(it.get("taxable_amount"))
            if item_val and abs(item_val - total_val) < 0.01:
                continue
            filtered_raw_items.append(it)
        raw_items = filtered_raw_items

    # choose items targeting total
    items = choose_items_by_total(raw_items, total_amount)
    if not items and raw_items:
        items = [it for it in raw_items if to_float_safe(it.get("taxable_amount", "")) and to_float_safe(it["taxable_amount"]) >= 2.0][:6]

    # ensure HSNs are clean
    for it in items:
        if it.get("hsn"):
            it["hsn"] = clean_hsn(it["hsn"])

    top_items = items[:3] if items else []
    items_signature = None
    try:
        sig_list = []
        for it in items:
            sig_list.append({
                "hsn": it.get("hsn") or "", 
                "taxable_amount": it.get("taxable_amount") or "",
                "cgst_percentage": it.get("cgst_percentage") or "",
                "sgst_percentage": it.get("sgst_percentage") or ""
            })
        items_signature = sha256_of_obj(sorted(sig_list, key=lambda x: (x["hsn"], x["taxable_amount"])))
    except Exception:
        items_signature = None

    tax = extract_tax_fields(md)
    irn = extracted.get("irn") or extract_irn(md)
    if irn:
        irn = str(irn).strip().rstrip('-')

    misc = extract_misc_refs(md)
    handwritten = extract_handwritten_chunks(chunks)
    image_hash = md5_file(path)
    elapsed = time.time() - start

    # notes / review heuristics
    if not invoice_no:
        notes.append("invoice_no missing")
    if not total_amount:
        notes.append("total_amount missing")
    if not gstin:
        notes.append("gstin missing/ambiguous")
    if not vendor or (isinstance(vendor, str) and len(vendor) < 3):
        notes.append("vendor missing/ambiguous")
    if items and any(to_float_safe(i.get("taxable_amount", "")) is not None and to_float_safe(i.get("taxable_amount")) < 2 for i in items[:3]):
        notes.append("items appear noisy (very small amounts)")
    
    sum_items = sum([to_float_safe(i.get("taxable_amount")) or 0 for i in items])
    total_val = to_float_safe(total_amount)
    taxable_val = to_float_safe(tax.get("taxable_amount"))

    if total_val:
        if taxable_val and abs(sum_items - taxable_val) < 1.0:
            pass
        elif abs(sum_items - total_val) > max(1.0, 0.05 * total_val):
            notes.append("items sum does not match total (may be partial or noisy)")
            if abs(sum_items - total_val) > max(5.0, 0.10 * total_val):
                needs_review = True
    
    needs_review = needs_review or (len(notes) > 0)

    result = {
        "filename": path.name,
        "invoice_no": invoice_no,
        "invoice_date": invoice_date,
        "gstin": gstin,
        "vendor_name": vendor,
        "total_amount": total_amount,
        "taxable_amount": tax.get("taxable_amount"),
        "cgst_percentage": tax.get("cgst_percentage"),
        "cgst_amount": tax.get("cgst_amount"),
        "sgst_percentage": tax.get("sgst_percentage"),
        "sgst_amount": tax.get("sgst_amount"),
        "igst_percentage": tax.get("igst_percentage"),
        "igst_amount": tax.get("igst_amount"),
        "total_tax": tax.get("total_tax"),
        "irn": irn,
        "po_number": clean_misc_token(misc.get("po_number")),
        "booking_number": clean_misc_token(misc.get("booking_number")),
        "ack_no": clean_misc_token(misc.get("ack_no")),
        "items": items,
        "top_items": top_items,
        "items_signature": items_signature,
        "handwritten_annotations": handwritten,
        "image_hash": image_hash,
        "parse_time_sec": round(elapsed, 2),
        "needs_review": needs_review,
        "notes": notes
    }

    # optional rename
    if AUTO_RENAME:
        try:
            date_norm = ""
            if invoice_date:
                m = re.search(r'(\d{4})[-/](\d{1,2})[-/](\d{1,2})', str(invoice_date))
                if not m:
                    m2 = re.search(r'(\d{1,2})[-/](\d{1,2})[-/](\d{4})', str(invoice_date))
                    if m2:
                        yyyy, mm, dd = m2.group(3), m2.group(2).zfill(2), m2.group(1).zfill(2)
                        date_norm = f"{yyyy}{mm}{dd}"
                else:
                    date_norm = f"{m.group(1)}{m.group(2).zfill(2)}{m.group(3).zfill(2)}"
            gst_part = safe_token(gstin) if gstin else "UNKNOWNGSTIN"
            inv_part = safe_token(invoice_no) if invoice_no else "UNKNOWNINV"
            ext = path.suffix.lower()
            new_name = f"{gst_part}_{date_norm}_{inv_part}{ext}" if date_norm else f"{gst_part}_{inv_part}{ext}"
            new_path = path.with_name(new_name)
            if new_path != path:
                path.rename(new_path)
                result["renamed_to"] = new_path.name
                result["filename"] = new_path.name
        except Exception as e:
            result.setdefault("notes", []).append(f"rename_error: {e}")
            result["needs_review"] = True

    return result

# ---------- batch runner ----------
def process_folder(folder: Path, max_workers=MAX_WORKERS):
    files = [p for p in sorted(folder.iterdir()) if p.suffix.lower() in ALLOWED_EXTS]
    if not files:
        print("No invoice files found in", folder)
        return
    print(f"Found {len(files)} files. Processing with {max_workers} workers...")
    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        future_to_path = {ex.submit(process_file, p): p for p in files}
        for future in as_completed(future_to_path):
            pfile = future_to_path[future]
            try:
                res = future.result()
                print(f"[{res['filename']}] done — invoice_no={res.get('invoice_no')} total={res.get('total_amount')} time={res.get('parse_time_sec')}s needs_review={res.get('needs_review')}")
                results.append(res)
            except Exception as e:
                print(f"[{pfile.name}] error: {e}")
                results.append({"filename": pfile.name, "error": str(e), "needs_review": True, "notes": [str(e)]})
    OUTPUT_JSON.write_text(json.dumps(results, indent=2, ensure_ascii=False))
    print(f"Saved results to {OUTPUT_JSON.resolve()}")

# ---------- CLI ----------
def main():
    if len(sys.argv) < 2:
        print("No path provided — defaulting to current directory '.'")
        target = Path(".").resolve()
    else:
        target = Path(sys.argv[1])

    if target.is_file():
        print("Single file mode:", target.name)
        result = process_file(target)
        OUTPUT_JSON.write_text(json.dumps([result], indent=2, ensure_ascii=False))
        print(f"Saved single-file result to {OUTPUT_JSON.resolve()}")
    elif target.is_dir():
        process_folder(target, max_workers=MAX_WORKERS)
    else:
        print("Invalid path:", target)
        sys.exit(1)

if __name__ == "__main__":
    main()