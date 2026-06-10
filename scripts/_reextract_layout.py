"""Re-extract text from a PDF using layout-aware column detection.

Strategy:
- Use pdfplumber to get per-character positions per page
- Group characters by approximate column x-coordinate cluster
- Read columns left-to-right with vertical position ordering
- Strip repeating page headers/footers when present on >50% of pages
- Strip (cid:N) glyph placeholders from unembedded font references
"""
from __future__ import annotations

import re
import statistics
import sys
from collections import Counter
from pathlib import Path

import pdfplumber

# Pages where the dominant text is rotated (e.g. sidebars) — drop them.
ROTATION_DROP = {90, 180, 270}

# Regex of repeated-header candidates (learned from >50% page repetition).
HEADER_FOOTER_MIN_PAGES = 0.5

# (cid:N) placeholders from PDFs with unembedded fonts
CID_RE = re.compile(r"\(cid:\d+\)")

# Mirror-text artifacts (rotated labels) — lines whose letters are reversed.
MIRROR_RE = re.compile(r"^(?:[a-z]{3,}\s)+$")
COMMON_ENGLISH = {
    "the", "and", "for", "are", "but", "not", "you", "all", "can", "had", "her", "was",
    "one", "our", "out", "day", "get", "has", "him", "his", "how", "its", "may", "new",
    "now", "old", "see", "way", "who", "did", "let", "say", "she", "too", "use",
}


def _strip_cid(text: str) -> str:
    cleaned = CID_RE.sub("", text)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


def _page_words(page: pdfplumber.page.Page) -> list[dict]:
    return page.extract_words(
        keep_blank_chars=False,
        use_text_flow=True,
        x_tolerance=2,
        y_tolerance=3,
    )


def _column_groups(words: list[dict], page_width: float) -> list[list[dict]]:
    """Bin words into columns by their x0/x1 midpoint x-coordinate.

    Uses a simple 1-D density peak detection on word midpoints.
    """
    if not words:
        return []
    midpoints = sorted((w["x0"] + w["x1"]) / 2 for w in words)
    # Try a few candidate column counts by clustering on x0 directly.
    # If a clear gap (>20% of page width) exists in the lower 1/3 of x0s, split there.
    x0s = sorted(w["x0"] for w in words)
    if len(x0s) < 4:
        return [words]
    # Look for a gap between adjacent x0s that's much larger than the median gap.
    gaps = [b - a for a, b in zip(x0s, x0s[1:])]
    if not gaps:
        return [words]
    median_gap = statistics.median(gaps)
    threshold = max(median_gap * 4, page_width * 0.10)
    big_gaps = [g for g in gaps if g > threshold]
    if not big_gaps:
        return [words]
    # Use the single largest gap if it's > threshold and not at the right margin only.
    max_gap = max(gaps)
    if max_gap < threshold:
        return [words]
    gap_index = gaps.index(max_gap)
    split_x = (x0s[gap_index] + x0s[gap_index + 1]) / 2
    left = [w for w in words if (w["x0"] + w["x1"]) / 2 < split_x]
    right = [w for w in words if (w["x0"] + w["x1"]) / 2 >= split_x]
    if not left or not right:
        return [words]
    return [left, right]


def _read_column(words: list[dict], page_height: float) -> str:
    """Render a single column's words into lines ordered by y then x."""
    # Group by y-top within tolerance.
    lines: list[list[dict]] = []
    current: list[dict] = []
    last_top: float | None = None
    for w in sorted(words, key=lambda w: (round(w["top"], 1), w["x0"])):
        if last_top is None or abs(w["top"] - last_top) <= 3:
            current.append(w)
        else:
            lines.append(current)
            current = [w]
        last_top = w["top"]
    if current:
        lines.append(current)
    rendered = []
    for line_words in lines:
        line_words = sorted(line_words, key=lambda w: w["x0"])
        text = " ".join(w["text"] for w in line_words)
        rendered.append(text)
    return "\n".join(rendered)


def _looks_like_mirror(line: str) -> bool:
    """Heuristic: line reads backwards compared to English text."""
    if not line or len(line) < 6:
        return False
    words = line.lower().split()
    if not words:
        return False
    if any(w in COMMON_ENGLISH for w in words):
        return False
    # If all words are alphabetic and reverse-dictionary-empty, treat as suspect.
    if all(w.isalpha() and len(w) > 3 for w in words):
        joined = "".join(words)
        reversed_text = joined[::-1]
        if any(word in COMMON_ENGLISH for word in reversed_text.split()):
            return True
    return False


def extract_with_layout(pdf_path: Path) -> tuple[str, int]:
    pages_text: list[str] = []
    cid_pages: list[str] = []
    header_counter: Counter[str] = Counter()
    footer_counter: Counter[str] = Counter()
    import time
    page_times: list[tuple[int, float]] = []
    with pdfplumber.open(pdf_path) as pdf:
        n_pages = len(pdf.pages)
        for i, page in enumerate(pdf.pages):
            t0 = time.time()
            # Skip rotated pages.
            if page.rotation in ROTATION_DROP:
                pages_text.append("")
                page_times.append((i, time.time() - t0))
                continue
            words = _page_words(page)
            if not words:
                pages_text.append("")
                page_times.append((i, time.time() - t0))
                continue
            cols = _column_groups(words, page.width)
            # Render each column in order; if single column, just one.
            col_texts = []
            for col in cols:
                col_texts.append(_read_column(col, page.height))
            page_text = "\n\n".join(t for t in col_texts if t.strip())
            page_text = _strip_cid(page_text)
            pages_text.append(page_text)
            page_times.append((i, time.time() - t0))
            # Track first / last non-empty line for header/footer detection.
            lines = [l for l in page_text.splitlines() if l.strip()]
            if lines:
                header_counter[lines[0]] += 1
                footer_counter[lines[-1]] += 1
            if page_times[-1][1] > 5.0:
                print(f"  page {i}: SLOW {page_times[-1][1]:.2f}s ({len(words)} words, {len(cols)} cols)", flush=True)
    # Drop headers/footers that appear on more than HALF the pages.
    threshold = max(2, int(n_pages * HEADER_FOOTER_MIN_PAGES))
    common_headers = {h for h, c in header_counter.items() if c >= threshold}
    common_footers = {f for f, c in footer_counter.items() if c >= threshold}
    cleaned_pages: list[str] = []
    for p in pages_text:
        lines = p.splitlines()
        if lines and lines[0] in common_headers:
            lines = lines[1:]
        if lines and lines[-1] in common_footers:
            lines = lines[:-1]
        # Drop mirror-text lines.
        lines = [l for l in lines if not _looks_like_mirror(l)]
        cleaned_pages.append("\n".join(lines))
    if page_times:
        slow = sorted(page_times, key=lambda x: -x[1])[:3]
        print(f"  slowest pages: {slow}", flush=True)
    return "\n\n".join(cleaned_pages), n_pages


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: _reextract_layout.py <id> [<id> ...]")
        return 1
    root = Path(r"C:\Dev\Cuz\.claude\worktrees\objective-rubin-7d1432")
    docs_root = root / "corpus" / "docs"
    out_root = root / "corpus" / "extracted"
    for doc_id in argv[1:]:
        pdf = docs_root / doc_id / "source.pdf"
        if not pdf.exists():
            print(f"{doc_id}: no source.pdf")
            continue
        try:
            text, n_pages = extract_with_layout(pdf)
        except Exception as exc:  # noqa: BLE001
            print(f"{doc_id}: FAIL {type(exc).__name__}: {exc}")
            continue
        out = out_root / doc_id / "full_text.txt"
        prev_chars = out.stat().st_size if out.exists() else 0
        out.write_text(text, encoding="utf-8")
        cid_left = text.count("(cid:")
        print(
            f"{doc_id}: pages={n_pages} new_chars={len(text)} prev_chars={prev_chars} "
            f"cid_remaining={cid_left}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
