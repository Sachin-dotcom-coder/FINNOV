from __future__ import annotations

import os
import re
import io
import json
import time
import tempfile
from datetime import datetime, date
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List, Optional, Tuple

# Optional heavy deps guarded
try:
    import fitz  # PyMuPDF
except Exception:
    fitz = None  # type: ignore

try:
    import numpy as np
    import cv2
except Exception:
    np = None  # type: ignore
    cv2 = None  # type: ignore

try:
    import requests
except Exception:
    requests = None  # type: ignore

try:
    import pytesseract
    from PIL import Image
    TESS_AVAILABLE = True
except Exception:
    TESS_AVAILABLE = False

try:
    from pymongo import MongoClient
    MONGO_AVAILABLE = True
except Exception:
    MONGO_AVAILABLE = False

# Config via env (no hard-coded secrets)
AZURE_ENDPOINT = os.getenv("AZURE_ENDPOINT")
AZURE_KEY = os.getenv("AZURE_KEY")
MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB = os.getenv("MONGO_DB", "online_db")
MONGO_COLLECTION = os.getenv("MONGO_COLLECTION", "invoices")
HSN_CSV_PATH = os.getenv("HSN_CSV_PATH", os.path.join(os.getcwd(), "Collection_HSN_and_GST_Data.csv"))

STANDARD_GST_SLABS = [Decimal("0"), Decimal("5"), Decimal("12"), Decimal("18"), Decimal("28")]
SLAB_TOLERANCE = Decimal("0.5")

IRN_RE = re.compile(r"([a-f0-9]{64}\s*-\s*[a-f0-9]{32})", flags=re.I)
GST_LABEL_PATTERNS = [
    r"(?:COMPANY'S\s*GSTIN\/UIN|COMPANY'S\s*GSTIN|COMPANY\s*GSTIN|GSTIN\/UIN|GSTIN)(?:\s*[:\-\n]\s*|\s+)([0-9A-Z\-\s]{10,30})",
    r"(?:BUYER|BILL TO|CONSIGNEE|SHIP TO).{0,40}(?:GSTIN\/UIN|GSTIN)(?:\s*[:\-\n]\s*|\s+)([0-9A-Z\-\s]{10,30})",
]
GST_SIMPLE = re.compile(r"([0-9A-Z]{15})", flags=re.I)
PAN_RE = re.compile(r"\b([A-Z]{5}[0-9]{4}[A-Z])\b")
HSN_RE = re.compile(r"\b[0-9]{4,8}\b")
AMOUNT_RE = re.compile(r"([0-9]{1,3}(?:,[0-9]{3})*(?:\.\d+)?)")
COMPANY_KEYWORDS = [
    "LTD",
    "PVT",
    "PRIVATE",
    "TRADERS",
    "ELECTR",
    "INFRA",
    "INDUSTRIAL",
    "SERVICES",
    "ENTERPRISE",
    "INDIA",
    "INDUSTRIES",
    "CO.",
]


def to_decimal(val: Any) -> Optional[Decimal]:
    if val is None:
        return None
    if isinstance(val, Decimal):
        return val
    s = str(val)
    s = s.replace("₹", "").replace("\u20b9", "").replace("INR", "").replace(",", "").strip()
    m = re.search(r"-?\d+(?:\.\d+)?", s)
    if not m:
        return None
    try:
        return Decimal(m.group(0))
    except Exception:
        return None


def quant2(x: Decimal) -> Decimal:
    return x.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def parse_date(s: Optional[str]) -> Optional[str]:
    if not s:
        return None
    s = str(s).strip()
    fmts = ["%d-%b-%y", "%d-%b-%Y", "%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d", "%d %b %Y"]
    for f in fmts:
        try:
            dt = datetime.strptime(s, f)
            return dt.date().isoformat()
        except Exception:
            pass
    try:
        from dateutil import parser as _p
        dt = _p.parse(s, dayfirst=True)
        return dt.date().isoformat()
    except Exception:
        return None


# ---------- HSN -> GST CSV ----------
import csv

def load_hsn_map_from_csv(path: str) -> Dict[str, Decimal]:
    out: Dict[str, Decimal] = {}
    if not os.path.exists(path):
        return out
    try:
        with open(path, newline="", encoding="utf-8") as cf:
            rdr = csv.DictReader(cf)
            if not rdr.fieldnames:
                return out
            heads = [h.lower() for h in rdr.fieldnames]
            hsn_col = None
            rate_col = None
            for h in heads:
                if "hsn" in h or "sac" in h:
                    hsn_col = h
                if "gst" in h or "rate" in h or "tax" in h:
                    rate_col = h
            if not hsn_col:
                hsn_col = heads[0]
            if not rate_col and len(heads) > 1:
                rate_col = heads[1]
            for row in rdr:
                raw_hsn = row.get(hsn_col, "") if hsn_col else ""
                raw_rate = row.get(rate_col, "") if rate_col else ""
                raw_hsn = re.sub(r"\D", "", str(raw_hsn))
                rate_dec = to_decimal(raw_rate)
                if raw_hsn and rate_dec is not None:
                    out[raw_hsn] = rate_dec
    except Exception:
        return {}
    return out

_HSN_MAP = load_hsn_map_from_csv(HSN_CSV_PATH)


def get_gst_for_hsn(hsn: Optional[str], db_client: Optional[Any] = None) -> Optional[Decimal]:
    if not hsn:
        return None
    key = re.sub(r"\D", "", str(hsn))
    if not key:
        return None
    if key in _HSN_MAP:
        return _HSN_MAP[key]
    if db_client and MONGO_AVAILABLE:
        try:
            db = db_client[MONGO_DB]
            doc = db.get_collection("users").find_one({"HSN_SAC_Code": {"$regex": key}})
            if doc:
                rate = doc.get("Tax_Rate") or doc.get("gst_rate") or doc.get("Rate")
                return to_decimal(rate)
        except Exception:
            pass
    return None


# ---------- IO helpers ----------

def pdf_to_image(pdf_path: str, page: int = 0, dpi: int = 300):
    if not fitz:
        raise RuntimeError("PyMuPDF not installed")
    doc = fitz.open(pdf_path)
    page_obj = doc[page]
    pix = page_obj.get_pixmap(dpi=dpi)
    import numpy as _np
    img = _np.frombuffer(pix.samples, dtype=_np.uint8).reshape(pix.height, pix.width, pix.n)
    if pix.n == 4:
        import cv2 as _cv2
        img = _cv2.cvtColor(img, _cv2.COLOR_RGBA2RGB)
    return img


def pil_to_cv(img_pil):
    rgb = img_pil.convert("RGB")
    import numpy as _np
    return _np.array(rgb)


def load_image_any(path: str, page: int = 0):
    pl = path.lower()
    if pl.endswith(".pdf"):
        return pdf_to_image(path, page=page, dpi=400)
    try:
        from PIL import Image as _Image
        pil = _Image.open(path)
        if getattr(pil, "n_frames", 1) > 1:
            pil.seek(0)
        return pil_to_cv(pil)
    except Exception:
        if cv2 is None:
            raise
        img = cv2.imread(path, cv2.IMREAD_UNCHANGED)
        if img is None:
            raise FileNotFoundError(f"Unable to open image: {path}")
        if img.ndim == 2:
            img = cv2.cvtColor(img, cv2.COLOR_GRAY2RGB)
        elif img.shape[2] == 4:
            img = cv2.cvtColor(img, cv2.COLOR_BGRA2RGB)
        else:
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        return img


def deskew_image(img_rgb, max_skew_deg: float = 15.0):
    if cv2 is None:
        return img_rgb
    try:
        gray = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2GRAY)
        h, w = gray.shape
        scale = 1.0
        if max(w, h) > 2000:
            scale = 2000.0 / max(w, h)
            small = cv2.resize(gray, (int(w * scale), int(h * scale)))
        else:
            small = gray.copy()
        blur = cv2.GaussianBlur(small, (5, 5), 0)
        _, bw = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        bw = 255 - bw
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (9, 3))
        bw = cv2.morphologyEx(bw, cv2.MORPH_CLOSE, kernel)
        contours, _ = cv2.findContours(bw, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return img_rgb
        largest = max(contours, key=cv2.contourArea)
        rect = cv2.minAreaRect(largest)
        angle = rect[-1]
        if angle < -45:
            angle = 90 + angle
        if scale != 1.0:
            angle = angle / scale
        if abs(angle) < 0.05:
            angle = 0.0
        if abs(angle) > 45:
            import numpy as _np
            img_rgb = _np.rot90(img_rgb)
            return deskew_image(img_rgb, max_skew_deg=max_skew_deg)
        if 0.1 < abs(angle) < max_skew_deg:
            (h, w) = img_rgb.shape[:2]
            center = (w // 2, h // 2)
            M = cv2.getRotationMatrix2D(center, -angle, 1.0)
            img_rgb = cv2.warpAffine(
                img_rgb, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE
            )
        return img_rgb
    except Exception:
        return img_rgb


# ---------- OCR ----------

def tesseract_text(img) -> str:
    if not TESS_AVAILABLE:
        return ""
    try:
        return pytesseract.image_to_string(Image.fromarray(img))
    except Exception:
        return ""


# ---------- Azure invoice extraction ----------

def azure_extract(pdf_bytes: bytes) -> Dict[str, Any]:
    if not (AZURE_ENDPOINT and AZURE_KEY and requests):
        return {}
    api_url = f"{AZURE_ENDPOINT.rstrip('/')}/documentintelligence/documentModels/prebuilt-invoice:analyze?api-version=2024-02-29-preview"
    headers = {"Ocp-Apim-Subscription-Key": AZURE_KEY, "Content-Type": "application/pdf"}
    r = requests.post(api_url, headers=headers, data=pdf_bytes)
    if r.status_code not in (200, 202):
        return {}
    op = r.headers.get("operation-location")
    if not op:
        return {}
    for _ in range(90):
        poll = requests.get(op, headers={"Ocp-Apim-Subscription-Key": AZURE_KEY})
        if poll.status_code not in (200, 202):
            break
        j = poll.json()
        status = j.get("status")
        if status == "succeeded":
            docs = j.get("analyzeResult", {}).get("documents", [])
            if not docs:
                return {}
            fields = docs[0].get("fields", {})

            def val(k):
                return fields.get(k, {}).get("content")

            return {
                "vendor": val("VendorName"),
                "invoice_no": val("InvoiceId"),
                "invoice_date": val("InvoiceDate") or val("InvoiceDateIssued") or val("DueDate"),
                "gst": val("TotalTax") or val("TaxAmount"),
                "total_amount": val("InvoiceTotal"),
                "items_azure": fields.get("Items"),
                "raw_fields": fields,
            }
        elif status == "failed":
            break
        time.sleep(1)
    return {}


def normalize_azure_item(valobj: Dict[str, Any]) -> Dict[str, Any]:
    out = {
        "description": None,
        "hsn": None,
        "quantity": None,
        "unit": None,
        "unit_price": None,
        "taxable_value": None,
        "cgst_percent": None,
        "cgst_amount": None,
        "sgst_percent": None,
        "sgst_amount": None,
        "gst_percent": None,
        "gst_amount": None,
        "igst_percent": None,
        "igst_amount": None,
        "line_total": None,
    }
    v = valobj.get("valueObject", {}) if isinstance(valobj, dict) else valobj
    out["description"] = v.get("Description", {}).get("content") or v.get("Description", {}).get("valueString")
    out["hsn"] = v.get("ProductCode", {}).get("content") or v.get("ProductCode", {}).get("valueString")
    qty = v.get("Quantity", {}).get("valueNumber") or v.get("Quantity", {}).get("content")
    if isinstance(qty, (int, float)):
        out["quantity"] = int(qty) if isinstance(qty, int) or (isinstance(qty, float) and qty.is_integer()) else float(qty)
    else:
        try:
            out["quantity"] = int(str(qty)) if str(qty).isdigit() else float(qty)
        except Exception:
            out["quantity"] = None
    up = v.get("UnitPrice", {}).get("valueCurrency", {}).get("amount") or v.get("UnitPrice", {}).get("content")
    out["unit_price"] = float(to_decimal(up)) if up else None
    amt = v.get("Amount", {}).get("valueCurrency", {}).get("amount") or v.get("Amount", {}).get("content")
    out["taxable_value"] = float(to_decimal(amt)) if amt else None
    out["unit"] = v.get("Unit", {}).get("valueString") or v.get("Unit", {}).get("content")
    return out


def extract_gstins_with_context(text: str) -> List[Tuple[str, int, str]]:
    out: List[Tuple[str, int, str]] = []
    if not text:
        return out
    upper = text.upper()
    for pat in GST_LABEL_PATTERNS:
        for m in re.finditer(pat, upper, flags=re.I | re.S):
            raw = m.group(1)
            pos = m.start(1)
            cleaned = re.sub(r"[^0-9A-Z]", "", raw.upper())
            if len(cleaned) == 15 and re.match(r"[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z0-9]{3}", cleaned):
                window = upper[max(0, pos - 60) : pos + 60]
                label = "other"
                if any(k in window for k in ("COMPANY", "VENDOR", "SELLER", "SUPPLIER", "FROM")):
                    label = "company"
                if any(k in window for k in ("BUYER", "BILL TO", "CONSIGNEE", "SHIP TO", "TO")):
                    label = "buyer"
                out.append((cleaned, pos, label))
    if not out:
        for m in re.finditer(GST_SIMPLE, upper):
            gst = m.group(1)
            pos = m.start(1)
            if re.match(r"[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z0-9]{3}", gst):
                window = upper[max(0, pos - 60) : pos + 60]
                label = "other"
                if any(k in window for k in ("COMPANY", "VENDOR", "SELLER", "SUPPLIER", "FROM")):
                    label = "company"
                if any(k in window for k in ("BUYER", "BILL TO", "CONSIGNEE", "SHIP TO", "TO")):
                    label = "buyer"
                out.append((gst, pos, label))
    seen = set()
    out2: List[Tuple[str, int, str]] = []
    for g, p, l in sorted(out, key=lambda x: x[1]):
        if g not in seen:
            seen.add(g)
            out2.append((g, p, l))
    return out2


def extract_irn_loose(text: str) -> Optional[str]:
    if not text:
        return None
    m = IRN_RE.search(text)
    if m:
        return m.group(1).replace(" ", "").lower()
    cleaned = re.sub(r"\s+", "", text)
    m2 = IRN_RE.search(cleaned)
    if m2:
        return m2.group(1).replace(" ", "").lower()
    m3 = re.search(r"([a-f0-9]{60,64}).{0,8}?-?.{0,8}?([a-f0-9]{28,32})", cleaned, flags=re.I)
    if m3:
        return (m3.group(1) + "-" + m3.group(2)).lower()
    return None


def extract_amount_in_words_best(text: str) -> Optional[str]:
    if not text:
        return None
    m = re.search(r"(INR[\s\S]{0,120}?Only)", text, flags=re.I)
    if m:
        return m.group(1).strip()
    m2 = re.search(r"Amount Chargeable\s*\(in words\)\s*[:\-\s]*([\s\S]{1,120})", text, flags=re.I)
    if m2:
        return m2.group(1).splitlines()[0].strip()
    return None


def find_company_like_line(lines: List[str]) -> Optional[str]:
    for ln in lines[:30]:
        L = ln.upper()
        if any(k in L for k in COMPANY_KEYWORDS) and len(ln) > 3 and not re.search(r"GSTIN|TAX|INVOICE|IRN|ACK", L):
            return ln
    for ln in lines[:12]:
        if len(ln) > 4 and ln.isupper() and not re.search(r"TAX|INVOICE|GSTIN|IRN|ACK", ln.upper()):
            return ln
    for ln in lines[:20]:
        if len(ln) > 3 and not re.search(r"TAX INVOICE|INVOICE|IRN|ACK|DATE|HSN|GSTIN", ln, flags=re.I):
            return ln
    return None


def find_buyer_name(lines: List[str]) -> Optional[str]:
    for i, ln in enumerate(lines):
        if re.search(r"Buyer|Bill to|Bill To|Buyer \(Bill to\)|Consignee|Ship to|Bill\s*to", ln, flags=re.I):
            for j in range(i + 1, min(i + 6, len(lines))):
                cand = lines[j].strip()
                if cand and not re.search(r"GSTIN|GST|ADDRESS|STATE|PIN|PHONE|MOBILE", cand, flags=re.I):
                    return cand
    for ln in lines:
        if any(k in ln.upper() for k in COMPANY_KEYWORDS) and not re.search(r"TAX|INVOICE|GSTIN", ln, flags=re.I):
            return ln
    return None


def compute_item_gst(item: Dict[str, Any], db_client: Optional[Any] = None) -> Dict[str, Any]:
    taxable = to_decimal(item.get("taxable_value") or item.get("taxable") or item.get("amount"))
    gst_pct = to_decimal(item.get("gst_percent") or item.get("gst") or item.get("total_gst"))
    cgst_pct = to_decimal(item.get("cgst_percent") or item.get("cgst"))
    sgst_pct = to_decimal(item.get("sgst_percent") or item.get("sgst"))
    igst_pct = to_decimal(item.get("igst_percent") or item.get("igst"))

    if gst_pct is None and (cgst_pct is not None or sgst_pct is not None):
        cg = cgst_pct or Decimal("0")
        sg = sgst_pct or Decimal("0")
        gst_pct = cg + sg

    if gst_pct is None and item.get("hsn"):
        gst_from_hsn = get_gst_for_hsn(item.get("hsn"), db_client=db_client)
        if gst_from_hsn is not None:
            gst_pct = gst_from_hsn
            item.setdefault("notes", {})
            item["notes"]["filled_gst_from_hsn"] = True

    if gst_pct is not None and (cgst_pct is None and sgst_pct is None and igst_pct is None):
        try:
            matched_slab = any(abs(gst_pct - s) <= SLAB_TOLERANCE for s in STANDARD_GST_SLABS)
            half = (gst_pct / 2).quantize(Decimal("0.01"))
            if matched_slab and gst_pct <= Decimal("28"):
                cgst_pct = sgst_pct = half
                igst_pct = Decimal("0")
            else:
                igst_pct = gst_pct
                cgst_pct = sgst_pct = Decimal("0")
        except Exception:
            igst_pct = gst_pct
            cgst_pct = sgst_pct = Decimal("0")

    cgst_amt = None
    sgst_amt = None
    igst_amt = None
    gst_amt = None
    if taxable is not None:
        if cgst_pct is not None:
            cgst_amt = quant2(taxable * cgst_pct / Decimal("100"))
        if sgst_pct is not None:
            sgst_amt = quant2(taxable * sgst_pct / Decimal("100"))
        if igst_pct is not None:
            igst_amt = quant2(taxable * igst_pct / Decimal("100"))
        amounts = [a for a in (cgst_amt, sgst_amt, igst_amt) if a is not None]
        if amounts:
            gst_amt = sum(amounts)
    if gst_amt is None and gst_pct is not None and taxable is not None:
        gst_amt = quant2(taxable * gst_pct / Decimal("100"))

    line_total = None
    if taxable is not None:
        line_total = float((taxable + (gst_amt or Decimal("0"))).quantize(Decimal("0.01")))

    if gst_pct is not None:
        item["gst_percent"] = float(gst_pct)
    else:
        item["gst_percent"] = None
    item["gst_amount"] = float(gst_amt) if gst_amt is not None else None
    item["cgst_percent"] = float(cgst_pct) if cgst_pct is not None else None
    item["sgst_percent"] = float(sgst_pct) if sgst_pct is not None else None
    item["igst_percent"] = float(igst_pct) if igst_pct is not None else None
    item["cgst_amount"] = float(cgst_amt) if cgst_amt is not None else None
    item["sgst_amount"] = float(sgst_amt) if sgst_amt is not None else None
    item["igst_amount"] = float(igst_amt) if igst_amt is not None else None
    item["line_total"] = line_total

    if (item.get("gst_percent") is None) and (not item.get("hsn")):
        item.setdefault("anomalies", []).append("missing_gst_and_hsn")
    try:
        if item.get("gst_percent") is not None:
            gp = Decimal(str(item["gst_percent"]))
            if not any(abs(gp - s) <= SLAB_TOLERANCE for s in STANDARD_GST_SLABS):
                item.setdefault("anomalies", []).append("nonstandard_gst_slab")
    except Exception:
        pass

    return item


def build_priority_nested_json(flat_result: Dict[str, Any]) -> Dict[str, Any]:
    nested: Dict[str, Any] = {}
    nested["company"] = {
        "vendor_name": flat_result.get("vendor_name"),
        "gstin": flat_result.get("seller_gstin"),
        "other_gstins": [flat_result.get("buyer_gstin")] if flat_result.get("buyer_gstin") else [],
    }
    nested["invoice"] = {
        "invoice_no": flat_result.get("invoice_no"),
        "invoice_date": flat_result.get("invoice_date"),
        "ack_no": flat_result.get("ack_no"),
        "ack_date": flat_result.get("ack_date"),
        "irn": flat_result.get("irn"),
    }
    nested["totals"] = {
        "total_amount": flat_result.get("total_amount"),
        "total_tax": flat_result.get("total_tax"),
        "total_cgst": flat_result.get("total_cgst"),
        "total_sgst": flat_result.get("total_sgst"),
        "total_igst": flat_result.get("total_igst") if flat_result.get("total_igst") else None,
        "amount_in_words": flat_result.get("amount_in_words"),
    }
    nested_items: List[Dict[str, Any]] = []
    for it in flat_result.get("items", []):
        nested_items.append(
            {
                "hsn": it.get("hsn"),
                "description": it.get("description"),
                "quantity": it.get("quantity"),
                "unit": it.get("unit"),
                "unit_price": it.get("unit_price"),
                "taxable_value": it.get("taxable_value"),
                "gst_percent": it.get("gst_percent"),
                "gst_amount": it.get("gst_amount"),
                "cgst_percent": it.get("cgst_percent"),
                "cgst_amount": it.get("cgst_amount"),
                "sgst_percent": it.get("sgst_percent"),
                "sgst_amount": it.get("sgst_amount"),
                "igst_percent": it.get("igst_percent"),
                "igst_amount": it.get("igst_amount"),
                "line_total": it.get("line_total"),
                "line_no": it.get("line_no"),
                "anomalies": it.get("anomalies", []),
            }
        )
    nested["items"] = nested_items
    nested["metadata"] = {
        "hsn_codes_detected": flat_result.get("hsn_codes"),
        "notes": flat_result.get("notes"),
        "computed_items_sum": flat_result.get("computed_items_sum"),
        "raw_text_sample": (flat_result.get("raw_text_sample")[:2000] if flat_result.get("raw_text_sample") else None),
        "azure_raw_fields": flat_result.get("azure_raw", None),
    }
    nested["source_file"] = flat_result.get("file")
    nested["anomalies"] = flat_result.get("anomalies", [])
    return nested


def build_output(pdf_path: str, page: int = 0) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "file": pdf_path,
        "invoice_no": None,
        "invoice_date": None,
        "vendor_name": None,
        "seller_gstin": None,
        "buyer_name": None,
        "buyer_gstin": None,
        "irn": None,
        "ack_no": None,
        "ack_date": None,
        "hsn_codes": [],
        "items": [],
        "computed_items_sum": None,
        "total_cgst": None,
        "total_sgst": None,
        "total_igst": None,
        "total_tax": None,
        "total_amount": None,
        "amount_in_words": None,
        "notes": {},
        "anomalies": [],
    }

    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()

    azure = {}
    try:
        azure = azure_extract(pdf_bytes)
    except Exception:
        azure = {}

    img = load_image_any(pdf_path, page=page)
    img = deskew_image(img)

    paddle_txt = ""
    tess_txt = ""
    if TESS_AVAILABLE:
        tess_txt = tesseract_text(img)

    agg_text = "\n".join([s for s in (paddle_txt, tess_txt) if s]).strip()
    result["raw_text_sample"] = agg_text
    result["azure_raw"] = azure.get("raw_fields") if azure else None
    text_lines = [ln.strip() for ln in (tess_txt or paddle_txt).splitlines() if ln.strip()]

    if azure.get("vendor"):
        result["vendor_name"] = azure.get("vendor")
    if azure.get("invoice_no"):
        result["invoice_no"] = azure.get("invoice_no")
    if azure.get("invoice_date"):
        result["invoice_date"] = parse_date(azure.get("invoice_date"))
    if azure.get("total_amount"):
        result["total_amount"] = float(to_decimal(azure.get("total_amount")) or 0)
    if azure.get("gst"):
        result["total_tax"] = float(to_decimal(azure.get("gst")) or 0)

    irn_candidate = extract_irn_loose(agg_text)
    result["irn"] = irn_candidate or result.get("irn")
    m_ack = re.search(r"\bAck\s*No\.?\s*[:\-]?\s*([0-9]{6,})", agg_text, flags=re.I)
    if m_ack:
        result["ack_no"] = m_ack.group(1)
    m_ackd = re.search(r"\bAck\s*Date\s*[:\-]?\s*([0-9]{1,2}[/-][A-Za-z0-9]{1,3}[/-][0-9]{2,4})", agg_text, flags=re.I)
    if m_ackd:
        result["ack_date"] = parse_date(m_ackd.group(1))

    gst_positions = extract_gstins_with_context(agg_text)
    if gst_positions:
        seller = None
        buyer = None
        for gst, pos, label in gst_positions:
            if label == "company" and not seller:
                seller = gst
            elif label == "buyer" and not buyer:
                buyer = gst
        if not seller:
            seller = gst_positions[0][0]
        if not buyer and len(gst_positions) > 1:
            buyer = gst_positions[1][0] if gst_positions[1][0] != seller else None
        result["seller_gstin"] = seller
        result["buyer_gstin"] = buyer

    if not result.get("vendor_name"):
        v = find_company_like_line(text_lines)
        if v:
            result["vendor_name"] = v
    if not result.get("buyer_name"):
        b = find_buyer_name(text_lines)
        if b:
            result["buyer_name"] = b

    result["hsn_codes"] = list(dict.fromkeys(HSN_RE.findall(agg_text)))

    items_out: List[Dict[str, Any]] = []
    if azure.get("items_azure"):
        try:
            arr = (
                azure["items_azure"].get("valueArray", [])
                if isinstance(azure["items_azure"], dict)
                else azure["items_azure"]
            )
            idx = 1
            for entry in arr:
                try:
                    normalized = normalize_azure_item(entry if isinstance(entry, dict) else {"valueObject": entry})
                    normalized["line_no"] = idx
                    items_out.append(normalized)
                except Exception:
                    pass
                idx += 1
        except Exception:
            items_out = []

    # Fallback: if Azure didn't provide items, we leave empty (text table parsing omitted for brevity)

    db_client = None
    if MONGO_AVAILABLE and MONGO_URI:
        try:
            db_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000)
            db_client.server_info()
        except Exception:
            db_client = None

    for i, it in enumerate(items_out):
        try:
            items_out[i] = compute_item_gst(it, db_client=db_client)
        except Exception:
            items_out[i]["anomalies"] = items_out[i].get("anomalies", []) + ["gst_compute_error"]

    result["items"] = items_out
    try:
        result["computed_items_sum"] = float(sum(Decimal(str(it.get("taxable_value") or 0)) for it in items_out))
    except Exception:
        result["computed_items_sum"] = None

    sum_cgst = sum(Decimal(str(it.get("cgst_amount") or 0)) for it in items_out) if items_out else Decimal("0")
    sum_sgst = sum(Decimal(str(it.get("sgst_amount") or 0)) for it in items_out) if items_out else Decimal("0")
    sum_igst = sum(Decimal(str(it.get("igst_amount") or 0)) for it in items_out) if items_out else Decimal("0")
    sum_gst = sum(Decimal(str(it.get("gst_amount") or 0)) for it in items_out) if items_out else Decimal("0")

    result["total_cgst"] = float(sum_cgst) if sum_cgst else result.get("total_cgst")
    result["total_sgst"] = float(sum_sgst) if sum_sgst else result.get("total_sgst")
    result["total_igst"] = float(sum_igst) if sum_igst else result.get("total_igst")
    if result.get("total_tax") is None and sum_gst:
        result["total_tax"] = float(sum_gst)

    maybe_words = extract_amount_in_words_best(agg_text)
    if maybe_words:
        result["amount_in_words"] = maybe_words

    panm = PAN_RE.search(agg_text)
    if panm:
        result["notes"]["company_pan"] = panm.group(1)

    anomalies: List[str] = []
    try:
        line_totals_sum = sum(Decimal(str(it.get("line_total") or 0)) for it in items_out)
        if result["total_amount"] is not None:
            if abs(Decimal(str(result["total_amount"])) - Decimal(str(line_totals_sum))) > Decimal("0.5"):
                anomalies.append(
                    f"Total mismatch: stated {result['total_amount']} vs sum of line_totals {line_totals_sum}."
                )
    except Exception:
        pass
    try:
        computed_gst_sum = sum(Decimal(str(it.get("gst_amount") or 0)) for it in items_out)
        if result.get("total_tax") is not None:
            if abs(Decimal(str(result.get("total_tax"))) - computed_gst_sum) > Decimal("0.5"):
                anomalies.append("GST mismatch between reported GST and sum(item gst amounts).")
    except Exception:
        pass

    try:
        if result.get("invoice_date"):
            d = datetime.fromisoformat(result["invoice_date"]).date()
            if d > date.today():
                anomalies.append("Invoice date is in the future.")
    except Exception:
        pass

    result["anomalies"] = anomalies
    return result


def insert_into_mongo(nested_doc: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    if not (MONGO_AVAILABLE and MONGO_URI):
        return False, "mongodb not configured"
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        client.server_info()
        db = client[MONGO_DB]
        coll = db[MONGO_COLLECTION]
        res = coll.insert_one(nested_doc)
        client.close()
        return True, str(res.inserted_id)
    except Exception as e:
        return False, str(e)


# Public API expected by the Flask adapter

def extract(input: Dict[str, Any]) -> Dict[str, Any]:
    """
    input may include: text, file_path, url, options
    returns: extracted nested dict
    """
    options = input.get("options") or {}

    # If text-only, return minimal stub
    if input.get("text") and not (input.get("file_path") or input.get("url")):
        text = str(input["text"])[:2000]
        return {
            "company": {},
            "invoice": {},
            "totals": {},
            "items": [],
            "metadata": {"raw_text_sample": text},
            "source_file": None,
            "anomalies": ["text_only_input"],
        }

    # Resolve file
    file_path = input.get("file_path")
    temp_file = None
    if not file_path and input.get("url"):
        if not requests:
            raise RuntimeError("requests not installed to download URL")
        resp = requests.get(input["url"], timeout=30)
        resp.raise_for_status()
        upload_dir = options.get("upload_dir") or os.path.join(os.getcwd(), "uploads")
        os.makedirs(upload_dir, exist_ok=True)
        fd, temp_file = tempfile.mkstemp(suffix=".bin", dir=upload_dir)
        with os.fdopen(fd, "wb") as f:
            f.write(resp.content)
        file_path = temp_file

    if not file_path:
        raise ValueError("file_path or url or text must be provided")

    flat = build_output(file_path)
    nested = build_priority_nested_json(flat)

    if options.get("insert_into_mongo"):
        insert_into_mongo(nested)

    # cleanup temp
    if temp_file and os.path.exists(temp_file):
        try:
            os.remove(temp_file)
        except Exception:
            pass

    return nested
