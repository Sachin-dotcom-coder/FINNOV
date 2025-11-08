from __future__ import annotations

import os
import re
from datetime import datetime, date
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, Optional, Tuple, List

try:
    from pymongo import MongoClient
    MONGO_AVAILABLE = True
except Exception:
    MONGO_AVAILABLE = False

import json

# Env
MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB = os.getenv("MONGO_DB", "online_db")
HSN_COLLECTION_NAME = os.getenv("HSN_COLLECTION", "users")
HSN_CSV_FALLBACK = os.getenv("HSN_CSV_FALLBACK", os.path.join(os.getcwd(), "Collection_HSN_and_GST_Data.csv"))

AMOUNT_TOLERANCE = Decimal("1.0")
STANDARD_SLABS = {0, 0.0, 5, 12, 18, 28, 3, 1}

GST_RE = re.compile(r"\b([0-9]{2}[A-Z]{5}[0-9]{4}[A-Z0-9]{3})\b", flags=re.I)
PAN_RE = re.compile(r"\b([A-Z]{5}[0-9]{4}[A-Z])\b")
NUM_RE = re.compile(r"-?\d+(?:\.\d+)?")
UPI_ID_RE = re.compile(r"[a-zA-Z0-9.\-_]{2,}@[a-zA-Z]{2,}", flags=re.I)
UPI_TXN_RE = re.compile(r"(?:Txn ID|Transaction ID|UTR|Ref|TXN|Transaction No|Trans ID)\s*[:\-\s]*([A-Za-z0-9\-_/]{6,})", flags=re.I)
AMOUNT_RE = re.compile(r"([0-9]{1,3}(?:,[0-9]{3})*(?:\.\d+)?)")

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except Exception:
    PANDAS_AVAILABLE = False


def to_decimal(x: Any) -> Optional[Decimal]:
    if x is None:
        return None
    if isinstance(x, Decimal):
        return x
    try:
        s = str(x)
        s = s.replace("₹", "").replace("\u20b9", "").replace("INR", "")
        s = s.replace(",", "").strip()
        m = re.search(r"-?\d+(?:\.\d+)?", s)
        if not m:
            return None
        return Decimal(m.group(0))
    except Exception:
        return None


def safe_div(a: Decimal, b: Decimal) -> Decimal:
    try:
        return (a / b).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except Exception:
        return Decimal("0")


def decimal_equal(a: Decimal, b: Decimal, tol: Decimal) -> bool:
    return abs(a - b) <= tol


def parse_iso_date(s: Optional[str]):
    if not s:
        return None
    try:
        return datetime.fromisoformat(str(s)).date()
    except Exception:
        pass
    for fmt in ("%d-%b-%Y","%d-%b-%y","%d-%m-%Y","%d/%m/%Y","%Y-%m-%d","%d %b %Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except Exception:
            pass
    try:
        from dateutil import parser as dp
        return dp.parse(s, dayfirst=True).date()
    except Exception:
        return None


def compute_tax_components_from_total(total_gst: Decimal) -> Tuple[Decimal, Decimal]:
    half = (total_gst / Decimal("2")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return half, half


def connect_db(uri: str):
    client = MongoClient(uri, serverSelectionTimeoutMS=5000)
    client.server_info()
    db = client[MONGO_DB]
    return client, db


def load_hsn_map(db) -> Dict[str, Dict[str, Any]]:
    hsn_map: Dict[str, Dict[str, Any]] = {}
    try:
        coll = db[HSN_COLLECTION_NAME]
        docs = list(coll.find({}))
        if docs:
            for d in docs:
                code = str(d.get("HSN_SAC_Code") or d.get("hsn") or d.get("HSN") or "").strip()
                if not code:
                    continue
                code = re.sub(r"\D", "", code)
                rate = d.get("Tax_Rate") or d.get("GST_Rate") or d.get("gst_rate") or d.get("gst")
                gst = to_decimal(rate)
                if gst is not None:
                    hsn_map[code] = {"gst": float(gst)}
        else:
            if os.path.exists(HSN_CSV_FALLBACK) and PANDAS_AVAILABLE:
                df = pd.read_csv(HSN_CSV_FALLBACK)
                for _, row in df.iterrows():
                    try:
                        code = str(row.get("HSN_SAC_Code") or row.get("HSN") or row.get("hsn") or "").strip()
                        code = re.sub(r"\D", "", code)
                        rate = row.get("Tax_Rate") or row.get("GST_Rate") or row.get("GST%") or row.get("GST")
                        gst = to_decimal(rate)
                        if code and gst is not None:
                            hsn_map[code] = {"gst": float(gst)}
                    except Exception:
                        continue
    except Exception:
        pass
    return hsn_map


def check_invoice(invoice: Dict[str, Any], hsn_map: Dict[str, Dict[str,Any]]) -> Dict[str, Any]:
    checks: Dict[str, Any] = {
        "flags": [],
        "auto_fixes": [],
        "details": {},
        "status": "OK"
    }
    try:
        company = invoice.get("company", {})
        inv_meta = invoice.get("invoice", {})
        totals = invoice.get("totals", {})
        items = invoice.get("items") or invoice.get("items", [])
        raw_text = invoice.get("metadata", {}).get("raw_text_sample") or invoice.get("raw_text_sample") or invoice.get("raw_text") or ""

        missing_gstin = False
        if not (company.get("gstin") or invoice.get("seller_gstin") or invoice.get("company", {}).get("gstin")):
            missing_gstin = True
            checks["flags"].append("missing_company_gstin")
        checks["details"]["missing_gstin"] = missing_gstin

        pan = None
        if raw_text:
            pm = PAN_RE.search(raw_text)
            if pm:
                pan = pm.group(1)
        if not pan and invoice.get("notes", {}).get("company_pan"):
            pan = invoice["notes"]["company_pan"]
        if not pan:
            checks["flags"].append("missing_pan")
            checks["details"]["missing_pan"] = True
        else:
            checks["details"]["company_pan"] = pan

        invoice_date = inv_meta.get("invoice_date") or invoice.get("invoice_date")
        parsed_date = parse_iso_date(invoice_date) if invoice_date else None
        if parsed_date:
            if parsed_date > date.today():
                checks["flags"].append("invoice_date_in_future")
                checks["details"]["invoice_date"] = str(parsed_date)
        else:
            checks["details"]["invoice_date"] = invoice_date

        total_gst = to_decimal(totals.get("total_tax") or totals.get("total_gst") or totals.get("totalTax") or invoice.get("total_tax"))
        total_cgst = to_decimal(totals.get("total_cgst") or invoice.get("total_cgst"))
        total_sgst = to_decimal(totals.get("total_sgst") or invoice.get("total_sgst"))

        item_issues: List[Dict[str, Any]] = []
        hsn_not_found: List[str] = []
        filled_from_hsn_count = 0
        missing_both_count = 0

        taxable_sum = Decimal("0.00")
        computed_line_totals = Decimal("0.00")
        for idx, it in enumerate(items or []):
            try:
                hsn = str(it.get("hsn") or "") if it.get("hsn") is not None else ""
                hsn_clean = re.sub(r"\D", "", hsn) if hsn else ""
                taxable = to_decimal(it.get("taxable_value") or it.get("amount") or it.get("taxable") or it.get("value"))
                if taxable is None:
                    taxable = to_decimal(it.get("line_total")) or Decimal("0.00")
                if taxable is None:
                    taxable = Decimal("0.00")
                taxable_sum += taxable

                cg = to_decimal(it.get("cgst_amount")) or to_decimal(it.get("cgst")) or None
                sg = to_decimal(it.get("sgst_amount")) or to_decimal(it.get("sgst")) or None

                if (total_gst is None or total_gst == Decimal("0")) and (not cg and not sg):
                    if hsn_clean and hsn_clean in hsn_map:
                        gst_pct = Decimal(str(hsn_map[hsn_clean]["gst"]))
                        total_line_gst = (taxable * gst_pct / Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                        cg_amt, sg_amt = compute_tax_components_from_total(total_line_gst)
                        it["cgst_percent"] = float(gst_pct/2)
                        it["sgst_percent"] = float(gst_pct/2)
                        it["cgst_amount"] = float(cg_amt)
                        it["sgst_amount"] = float(sg_amt)
                        it["taxable_value"] = float(taxable)
                        checks["auto_fixes"].append({"file": invoice.get("source_file"), "line_no": it.get("line_no"), "filled_gst_pct": float(gst_pct)})
                        filled_from_hsn_count += 1
                    else:
                        if (not hsn_clean) and (not cg and not sg):
                            missing_both_count += 1
                            item_issues.append({"line": idx + 1, "issue": "missing_hsn_and_gst"})
                        elif hsn_clean and hsn_clean not in hsn_map:
                            hsn_not_found.append(hsn_clean)
                            item_issues.append({"line": idx + 1, "issue": "hsn_not_in_map", "hsn": hsn_clean})

                cg_amt = to_decimal(it.get("cgst_amount")) or Decimal("0.00")
                sg_amt = to_decimal(it.get("sgst_amount")) or Decimal("0.00")
                line_total = to_decimal(it.get("line_total")) or (taxable + cg_amt + sg_amt)
                computed_line_totals += (line_total or Decimal("0.00"))
            except Exception:
                item_issues.append({"line": idx+1, "issue": "parsing_error"})

        checks["details"]["item_issues"] = item_issues
        checks["details"]["hsn_not_found_list"] = list(set(hsn_not_found))
        checks["details"]["filled_from_hsn_count"] = filled_from_hsn_count
        checks["details"]["missing_both_count"] = missing_both_count

        taxable_sum = Decimal(str(sum((to_decimal(it.get("taxable_value")) or Decimal("0.00")) for it in items or []))).quantize(Decimal("0.01"))

        if total_gst is None or total_gst == Decimal("0"):
            total_from_items = Decimal("0.00")
            for it in items or []:
                cg_amt = to_decimal(it.get("cgst_amount")) or Decimal("0.00")
                sg_amt = to_decimal(it.get("sgst_amount")) or Decimal("0.00")
                total_from_items += (cg_amt + sg_amt)
            if total_from_items > 0:
                total_gst = total_from_items
                checks["auto_fixes"].append({"file": invoice.get("source_file"), "filled_total_gst_from_items": float(total_from_items)})
        else:
            if total_cgst is None or total_sgst is None:
                split_c, split_s = compute_tax_components_from_total(total_gst)
                total_cgst = total_cgst or split_c
                total_sgst = total_sgst or split_s
            else:
                sum_csg = (total_cgst or Decimal("0")) + (total_sgst or Decimal("0"))
                if total_gst is not None and not decimal_equal(Decimal(str(total_gst)), sum_csg, AMOUNT_TOLERANCE):
                    checks["flags"].append("gst_mismatch_cgst_sgst")
                    checks["details"]["gst_mismatch_detail"] = {
                        "total_gst": float(total_gst),
                        "sum_c_s": float(sum_csg)
                    }

        checks["details"]["computed_taxable_sum"] = float(taxable_sum)
        checks["details"]["computed_line_totals_sum"] = float(computed_line_totals or Decimal("0.00"))

        total_amount = to_decimal(totals.get("total_amount") or invoice.get("total_amount") or invoice.get("totals", {}).get("total_amount"))
        if total_amount is None:
            total_amount = to_decimal(invoice.get("total_amount") or invoice.get("invoice_total") or invoice.get("grand_total"))

        expected_total = None
        if total_amount is None:
            if total_gst is not None:
                expected_total = (taxable_sum + Decimal(str(total_gst))).quantize(Decimal("0.01"))
            else:
                expected_total = computed_line_totals.quantize(Decimal("0.01"))
        else:
            expected_total = total_amount

        if total_amount is not None:
            diff = None
            try:
                computed = computed_line_totals
                diff = (Decimal(str(total_amount)) - computed).copy_abs()
                if diff > AMOUNT_TOLERANCE:
                    checks["flags"].append("arithmetic_mismatch")
                    checks["details"]["arithmetic"] = {
                        "reported_total": float(total_amount),
                        "computed_from_lines": float(computed),
                        "diff": float(diff)
                    }
            except Exception:
                checks["flags"].append("arithmetic_error_parsing")
        else:
            checks["details"]["expected_total_inferred"] = float(expected_total)

        nonstandard = False
        try:
            gst_pct_candidates = set()
            if total_gst is not None and taxable_sum > 0:
                from Decimal import Decimal as _D  # guard no, but compute directly
            for it in items or []:
                tv = to_decimal(it.get("taxable_value") or 0) or Decimal("0")
                cg_amt = to_decimal(it.get("cgst_amount") or 0) or Decimal("0")
                sg_amt = to_decimal(it.get("sgst_amount") or 0) or Decimal("0")
                if tv > 0:
                    pct = float(((cg_amt + sg_amt) / tv * 100).quantize(Decimal("0.01")))
                    gst_pct_candidates.add(pct)
            for cand in gst_pct_candidates:
                cand_rounded = round(float(cand))
                if cand_rounded not in STANDARD_SLABS:
                    nonstandard = True
                    checks["details"].setdefault("nonstandard_slabs", []).append(cand)
            if nonstandard:
                checks["flags"].append("nonstandard_gst_slab")
        except Exception:
            pass

        upi_found = False
        upi_issues: List[str] = []
        if raw_text:
            if UPI_ID_RE.search(raw_text):
                upi_found = True
            txn_m = UPI_TXN_RE.search(raw_text)
            if upi_found:
                checks["details"]["upi_detected"] = True
                checks["details"]["upi_id"] = UPI_ID_RE.search(raw_text).group(0)
                if txn_m:
                    checks["details"]["upi_txn_id"] = txn_m.group(1)
                m_sender = re.search(r"(?:From|Sender|Remitter|Paid By)\s*[:\-]?\s*([A-Za-z\s]{2,60})", raw_text, flags=re.I)
                if m_sender:
                    checks["details"]["upi_sender"] = m_sender.group(1).strip()
                am = AMOUNT_RE.search(raw_text)
                if am:
                    checks["details"]["upi_amount_detected"] = float(Decimal(am.group(1).replace(",", "")))
                else:
                    upi_issues.append("upi_amount_missing")
                if "upi_txn_id" not in checks["details"]:
                    upi_issues.append("upi_txn_missing")
                if upi_issues:
                    checks["flags"].append("upi_doc_incomplete")
                    checks["details"]["upi_issues"] = upi_issues

        checks["details"]["upi_found"] = upi_found

        txt_len = len(raw_text or "")
        if txt_len < 100:
            checks["flags"].append("low_ocr_text")
            checks["details"]["raw_text_length"] = txt_len

        checks["status"] = "FLAGGED" if checks["flags"] else "OK"

    except Exception as e:
        checks["flags"].append("internal_error")
        checks["details"]["internal_error"] = str(e)
        checks["status"] = "FLAGGED"

    return checks


# Public API

def analyze(extracted: Dict[str, Any], options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Run checks on a single extracted invoice dict.
    options:
      - use_db_hsn_map: bool (default True)
    """
    options = options or {}
    hsn_map: Dict[str, Dict[str, Any]] = {}
    if options.get("use_db_hsn_map", True) and MONGO_AVAILABLE and MONGO_URI:
        try:
            client, db = connect_db(MONGO_URI)
            hsn_map = load_hsn_map(db)
            client.close()
        except Exception:
            hsn_map = {}
    return check_invoice(extracted, hsn_map)
