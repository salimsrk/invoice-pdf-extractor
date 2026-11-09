# Invoice PDF → Excel Extractor

Turn a folder of invoice PDFs into a clean Excel/CSV report automatically, with built-in validation so nobody has to type invoices into Excel by hand.

**Problem it solves:** accounts teams spend hours copying invoice numbers, dates, GST and totals from PDFs into spreadsheets, and typing errors slip through.

## What it does

```
PDF invoices ──▶ text extraction ──▶ rule-based field + line-item parsing
                                          │ (missing fields?)
                                          ▼
                                  optional LLM fallback (Gemini)
                                          │
                                          ▼
                     validation (items = subtotal, subtotal + GST = total)
                                          │
                                          ▼
          invoices.csv · line_items.csv · invoice_report.xlsx (2 sheets)
```

- Extracts invoice no, date, seller, seller GSTIN, buyer, subtotal, GST rate/amount and grand total
- Extracts every line item (description, qty, rate, amount)
- **Validates the maths** and marks each invoice `OK` or `REVIEW` with the reason
- Rules run first (fast and free); the LLM runs only for fields the rules miss
- Works offline with no API key; set `GEMINI_API_KEY` to switch on the AI fallback for messy layouts

## Quick start

```bash
pip install -r requirements.txt
python samples/make_samples.py      # creates 3 sample GST invoices
python main.py --input samples --output output
```

Output:

```
         file    invoice_no                   seller  grand_total status
invoice_1.pdf INV-2026-0141     Kaveri Power Systems      45548.0     OK
invoice_2.pdf INV-2026-0142     Kaveri Power Systems      11328.0     OK
invoice_3.pdf     TX/889/26 Rockfort Office Supplies      14212.8     OK

3/3 invoices passed validation.
```

Optional AI fallback:

```bash
export GEMINI_API_KEY=your_key      # free key from Google AI Studio
python main.py --input my_invoices
```

## Tests

```bash
python -m pytest -q
```

## Tech

Python · pdfplumber · pandas · openpyxl · Gemini API (optional)

## Extending it for a real client

- Add regex rules for each supplier's invoice layout
- Add OCR (Tesseract) for scanned invoices
- Run it on a schedule against a Google Drive / S3 / email inbox folder
- Push results to Google Sheets, Tally or a database

---
Sample invoices are generated and fictional. Built by Salim, data engineer and AI automation developer.
