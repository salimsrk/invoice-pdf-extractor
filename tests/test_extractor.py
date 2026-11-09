from pathlib import Path

from src.extractor import extract_with_rules, validate, run

SAMPLES = Path(__file__).parent.parent / "samples"

TEXT = """Rockfort Office Supplies
GSTIN: 33PQRSX9876K1Z2
TAX INVOICE
Invoice No: TX/889/26 Invoice Date: 07/11/2026
Bill To: Anbu Coaching Centre
Description Qty Rate Amount
A4 Paper Ream 10 285.00 2,850.00
Office Chair 2 4,200.00 8,400.00
Subtotal: 11,250.00
GST @ 12%: 1,350.00
Grand Total: 12,600.00"""


def test_rules_extract_header_and_items():
    inv = validate(extract_with_rules(TEXT, "t.pdf"))
    assert inv.invoice_no == "TX/889/26"
    assert inv.invoice_date == "07/11/2026"
    assert inv.seller_gstin == "33PQRSX9876K1Z2"
    assert inv.buyer == "Anbu Coaching Centre"
    assert inv.grand_total == 12600.00
    assert len(inv.items) == 2
    assert inv.issues == []


def test_validation_flags_wrong_total():
    bad = TEXT.replace("Grand Total: 12,600.00", "Grand Total: 12,900.00")
    inv = validate(extract_with_rules(bad, "t.pdf"))
    assert "subtotal + GST != grand total" in inv.issues


def test_full_run_on_samples(tmp_path):
    import sys
    sys.path.insert(0, str(SAMPLES))
    from make_samples import INVOICES, make
    pdf_dir = tmp_path / "pdfs"
    pdf_dir.mkdir()
    for i, inv in enumerate(INVOICES, 1):
        make(inv, pdf_dir / f"invoice_{i}.pdf")
    df = run(pdf_dir, tmp_path / "out")
    assert len(df) == 3
    assert (df["status"] == "OK").all()
    assert (tmp_path / "out" / "invoice_report.xlsx").exists()
