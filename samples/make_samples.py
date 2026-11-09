"""Generate sample GST invoice PDFs for demo/testing (fictional businesses)."""
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from pathlib import Path

INVOICES = [
    dict(no="INV-2026-0141", date="03/11/2026", seller="Kaveri Power Systems", gstin="33ABCDE1234F1Z5",
         buyer="Sri Ranga Electricals", items=[("Inverter 1100VA", 2, 6500.00), ("Tubular Battery 150Ah", 2, 12800.00)], gst=18),
    dict(no="INV-2026-0142", date="05/11/2026", seller="Kaveri Power Systems", gstin="33ABCDE1234F1Z5",
         buyer="Malar Textiles", items=[("UPS 600VA", 3, 2950.00), ("Installation Charges", 1, 750.00)], gst=18),
    dict(no="TX/889/26", date="07/11/2026", seller="Rockfort Office Supplies", gstin="33PQRSX9876K1Z2",
         buyer="Anbu Coaching Centre", items=[("A4 Paper Ream", 10, 285.00), ("Whiteboard Marker Box", 4, 360.00), ("Office Chair", 2, 4200.00)], gst=12),
]

def make(inv, path):
    c = canvas.Canvas(str(path), pagesize=A4)
    w, h = A4
    y = h - 60
    c.setFont("Helvetica-Bold", 16); c.drawString(50, y, inv["seller"]); y -= 18
    c.setFont("Helvetica", 10); c.drawString(50, y, f"GSTIN: {inv['gstin']}"); y -= 30
    c.setFont("Helvetica-Bold", 13); c.drawString(50, y, "TAX INVOICE"); y -= 22
    c.setFont("Helvetica", 10)
    c.drawString(50, y, f"Invoice No: {inv['no']}"); c.drawString(350, y, f"Invoice Date: {inv['date']}"); y -= 16
    c.drawString(50, y, f"Bill To: {inv['buyer']}"); y -= 30
    c.setFont("Helvetica-Bold", 10)
    for x, t in [(50, "Description"), (300, "Qty"), (370, "Rate"), (470, "Amount")]: c.drawString(x, y, t)
    y -= 16; c.setFont("Helvetica", 10)
    sub = 0
    for d, q, r in inv["items"]:
        amt = q * r; sub += amt
        c.drawString(50, y, d); c.drawString(300, y, str(q)); c.drawString(370, y, f"{r:,.2f}"); c.drawString(470, y, f"{amt:,.2f}")
        y -= 16
    gst = round(sub * inv["gst"] / 100, 2)
    y -= 10
    c.drawString(370, y, "Subtotal:"); c.drawString(470, y, f"{sub:,.2f}"); y -= 16
    c.drawString(370, y, f"GST @ {inv['gst']}%:"); c.drawString(470, y, f"{gst:,.2f}"); y -= 16
    c.setFont("Helvetica-Bold", 11)
    c.drawString(370, y, "Grand Total:"); c.drawString(470, y, f"{sub+gst:,.2f}")
    c.save()

if __name__ == "__main__":
    out = Path(__file__).parent
    for i, inv in enumerate(INVOICES, 1):
        make(inv, out / f"invoice_{i}.pdf")
    print(f"Created {len(INVOICES)} sample invoices in {out}")
