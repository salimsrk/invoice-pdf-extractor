"""
Invoice PDF -> structured data pipeline.

Steps:
  1. Read text from each PDF (pdfplumber)
  2. Extract header fields + line items with rules (regex)
  3. If rules miss required fields and GEMINI_API_KEY is set, ask an LLM to fill the gaps
  4. Validate: line items add up to subtotal, subtotal + GST = grand total
  5. Write invoices.csv, line_items.csv and a 2-sheet Excel report
"""
from __future__ import annotations

import json
import os
import re
import urllib.request
from dataclasses import dataclass, field, asdict
from pathlib import Path

import pandas as pd
import pdfplumber

AMOUNT = r"([\d,]+\.\d{2})"
REQUIRED = ["invoice_no", "invoice_date", "seller", "grand_total"]


@dataclass
class LineItem:
    description: str
    qty: float
    rate: float
    amount: float


@dataclass
class Invoice:
    file: str
    invoice_no: str | None = None
    invoice_date: str | None = None
    seller: str | None = None
    seller_gstin: str | None = None
    buyer: str | None = None
    subtotal: float | None = None
    gst_rate: float | None = None
    gst_amount: float | None = None
    grand_total: float | None = None
    items: list[LineItem] = field(default_factory=list)
    method: str = "rules"
    issues: list[str] = field(default_factory=list)


def _num(s: str | None) -> float | None:
    return float(s.replace(",", "")) if s else None


def _find(pattern: str, text: str) -> str | None:
    m = re.search(pattern, text, re.IGNORECASE)
    return m.group(1).strip() if m else None


def read_pdf_text(path: Path) -> str:
    with pdfplumber.open(path) as pdf:
        return "\n".join(page.extract_text() or "" for page in pdf.pages)


def extract_with_rules(text: str, file: str) -> Invoice:
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    inv = Invoice(file=file)
    inv.seller = lines[0] if lines else None
    inv.seller_gstin = _find(r"GSTIN[:\s]+([0-9A-Z]{15})", text)
    inv.invoice_no = _find(r"Invoice\s*No[.:\s]+(\S+)", text)
    inv.invoice_date = _find(r"Invoice\s*Date[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})", text)
    inv.buyer = _find(r"Bill\s*To[:\s]+(.+)", text)
    inv.subtotal = _num(_find(r"Subtotal[:\s]+" + AMOUNT, text))
    gst = re.search(r"GST\s*@\s*([\d.]+)\s*%[:\s]+" + AMOUNT, text, re.IGNORECASE)
    if gst:
        inv.gst_rate, inv.gst_amount = float(gst.group(1)), _num(gst.group(2))
    inv.grand_total = _num(_find(r"Grand\s*Total[:\s]+" + AMOUNT, text))

    # Line items: "<description> <qty> <rate> <amount>"
    item_re = re.compile(r"^(.+?)\s+(\d+(?:\.\d+)?)\s+" + AMOUNT + r"\s+" + AMOUNT + r"$")
    for line in lines:
        m = item_re.match(line)
        if m:
            inv.items.append(LineItem(m.group(1), float(m.group(2)), _num(m.group(3)), _num(m.group(4))))
    return inv


def extract_with_llm(text: str, inv: Invoice) -> Invoice:
    """Fill missing fields with Gemini. Only runs when GEMINI_API_KEY is set."""
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        return inv
    prompt = (
        "Extract these invoice fields as JSON with keys: invoice_no, invoice_date, seller, "
        "seller_gstin, buyer, subtotal, gst_rate, gst_amount, grand_total. Numbers as plain numbers, "
        "null if not present. Return JSON only.\n\nINVOICE TEXT:\n" + text
    )
    body = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json"},
    }).encode()
    model = os.getenv("GEMINI_MODEL", "gemini-flash-latest")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
    try:
        req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=60) as r:
            data = json.loads(r.read())
        fields = json.loads(data["candidates"][0]["content"]["parts"][0]["text"])
    except Exception as e:  # network / quota / parse errors shouldn't crash the batch
        inv.issues.append(f"LLM fallback failed: {e}")
        return inv
    for k, v in fields.items():
        if hasattr(inv, k) and getattr(inv, k) in (None, "") and v not in (None, ""):
            setattr(inv, k, v)
    inv.method = "rules+llm"
    return inv


def validate(inv: Invoice) -> Invoice:
    for f in REQUIRED:
        if getattr(inv, f) in (None, ""):
            inv.issues.append(f"missing {f}")
    if inv.items and inv.subtotal is not None:
        s = round(sum(i.amount for i in inv.items), 2)
        if abs(s - inv.subtotal) > 0.01:
            inv.issues.append(f"line items {s} != subtotal {inv.subtotal}")
    if None not in (inv.subtotal, inv.gst_amount, inv.grand_total):
        if abs(inv.subtotal + inv.gst_amount - inv.grand_total) > 0.01:
            inv.issues.append("subtotal + GST != grand total")
    for i in inv.items:
        if abs(i.qty * i.rate - i.amount) > 0.01:
            inv.issues.append(f"qty x rate mismatch on '{i.description}'")
    return inv


def process_file(path: Path) -> Invoice:
    text = read_pdf_text(path)
    inv = extract_with_rules(text, path.name)
    if any(getattr(inv, f) in (None, "") for f in REQUIRED):
        inv = extract_with_llm(text, inv)
    return validate(inv)


def run(input_dir: Path, output_dir: Path) -> pd.DataFrame:
    output_dir.mkdir(parents=True, exist_ok=True)
    invoices = [process_file(p) for p in sorted(input_dir.glob("*.pdf"))]

    header_rows, item_rows = [], []
    for inv in invoices:
        d = asdict(inv)
        items = d.pop("items")
        d["status"] = "OK" if not inv.issues else "REVIEW"
        d["issues"] = "; ".join(inv.issues)
        header_rows.append(d)
        for it in items:
            item_rows.append({"file": inv.file, "invoice_no": inv.invoice_no, **it})

    headers = pd.DataFrame(header_rows)
    items = pd.DataFrame(item_rows)
    headers.to_csv(output_dir / "invoices.csv", index=False)
    items.to_csv(output_dir / "line_items.csv", index=False)
    with pd.ExcelWriter(output_dir / "invoice_report.xlsx", engine="openpyxl") as xw:
        headers.to_excel(xw, sheet_name="Invoices", index=False)
        items.to_excel(xw, sheet_name="Line Items", index=False)
        for ws in xw.book.worksheets:
            for col in ws.columns:
                ws.column_dimensions[col[0].column_letter].width = min(
                    max(len(str(c.value or "")) for c in col) + 2, 40)
    return headers
