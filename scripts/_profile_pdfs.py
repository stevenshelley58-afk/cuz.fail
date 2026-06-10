"""Profile source PDFs: page count, file size, font count."""
import sys
import time
from pathlib import Path

import pdfplumber

root = Path(r"C:\Dev\Cuz\.claude\worktrees\objective-rubin-7d1432")
docs_root = root / "corpus" / "docs"
extracted_root = root / "corpus" / "extracted"

# Read partial candidates
import json
candidates = json.loads((root / "reports" / "partial_candidates.json").read_text(encoding="utf-8"))

# Take top 20 by char count
top = [c["id"] for c in candidates[:25]]

print(f"{'id':<14} {'pages':>6} {'mb':>6} {'t1st':>5} {'txtlen':>8} {'ext_chars':>10}")
for doc_id in top:
    pdf = docs_root / doc_id / "source.pdf"
    if not pdf.exists():
        print(f"{doc_id}: NO PDF")
        continue
    try:
        with pdfplumber.open(pdf) as pdfobj:
            n = len(pdfobj.pages)
        mb = pdf.stat().st_size / 1_048_576
        t0 = time.time()
        with pdfplumber.open(pdf) as pdfobj:
            t = pdfobj.pages[0].extract_text() or ""
        first = time.time() - t0
        ext = extracted_root / doc_id / "full_text.txt"
        ext_chars = ext.stat().st_size if ext.exists() else 0
        print(f"{doc_id:<14} {n:>6} {mb:>6.1f} {first:>5.2f} {len(t):>8} {ext_chars:>10}")
    except Exception as exc:  # noqa: BLE001
        print(f"{doc_id}: ERR {exc}")
