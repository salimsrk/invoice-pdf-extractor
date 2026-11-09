"""CLI: python main.py --input samples --output output"""
import argparse
from pathlib import Path

from src.extractor import run


def main():
    ap = argparse.ArgumentParser(description="Extract structured data from invoice PDFs")
    ap.add_argument("--input", default="samples", help="folder with PDF invoices")
    ap.add_argument("--output", default="output", help="folder for CSV/Excel results")
    args = ap.parse_args()

    df = run(Path(args.input), Path(args.output))
    print(df[["file", "invoice_no", "seller", "grand_total", "status", "issues"]].to_string(index=False))
    ok = (df["status"] == "OK").sum()
    print(f"\n{ok}/{len(df)} invoices passed validation. Results in '{args.output}/'")


if __name__ == "__main__":
    main()
