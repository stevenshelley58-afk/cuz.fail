"""Shared helpers for the WA Planning Corpus workbench.

Layout:
  data/manifest.csv              instrument manifest (single source of truth)
  data/instrument_aliases.json   alias -> manifest id map for citation closure
  corpus/docs/{id}/source.pdf    acquired documents (+ meta.json)
  corpus/extracted/{id}/         full_text.txt, tables.json, summary.json
  reports/                       acquisition_report.json, extraction_report.json
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import sys
import threading
from datetime import date, datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = REPO_ROOT / "data" / "manifest.csv"
ALIASES_PATH = REPO_ROOT / "data" / "instrument_aliases.json"
DOCS_ROOT = REPO_ROOT / "corpus" / "docs"
EXTRACTED_ROOT = REPO_ROOT / "corpus" / "extracted"
REPORTS_ROOT = REPO_ROOT / "reports"

MANIFEST_COLUMNS = [
    "id",
    "instrument_name",
    "category",
    "issuing_authority",
    "index_source_url",
    "canonical_url",
    "expected_version_hint",
    "status",
    "source_document_id",
    "last_checked_at",
    "notes",
]

USER_AGENT = (
    "DraftCheck-WA-Corpus/1.0 (planning research; contact stevenshelley58@gmail.com)"
)

_manifest_lock = threading.Lock()


def today() -> str:
    return date.today().isoformat()


def utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_manifest() -> list[dict]:
    if not MANIFEST_PATH.exists():
        return []
    with open(MANIFEST_PATH, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_manifest(rows: list[dict]) -> None:
    """Atomic single-writer manifest update."""
    with _manifest_lock:
        tmp = MANIFEST_PATH.with_suffix(".csv.tmp")
        MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(tmp, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=MANIFEST_COLUMNS, extrasaction="ignore")
            writer.writeheader()
            for row in rows:
                writer.writerow({c: row.get(c, "") for c in MANIFEST_COLUMNS})
        os.replace(tmp, MANIFEST_PATH)


def update_row(rows: list[dict], row_id: str, **fields) -> None:
    for row in rows:
        if row["id"] == row_id:
            row.update({k: str(v) for k, v in fields.items()})
            return
    raise KeyError(f"manifest row not found: {row_id}")


def doc_dir(row_id: str) -> Path:
    return DOCS_ROOT / row_id


def extracted_dir(row_id: str) -> Path:
    return EXTRACTED_ROOT / row_id


def append_report(report_path: Path, entry: dict) -> None:
    """Append an entry to a JSON report file (list of entries)."""
    report_path.parent.mkdir(parents=True, exist_ok=True)
    entries = []
    if report_path.exists():
        try:
            entries = json.loads(report_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            entries = []
    entries.append(entry)
    tmp = report_path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(entries, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, report_path)


def normalize_name(name: str) -> str:
    """Normalise an instrument name for fuzzy matching."""
    name = name.lower()
    name = re.sub(r"\bno\.?\s*", "", name)
    name = re.sub(r"[^a-z0-9. ]+", " ", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name


def log(msg: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)
    sys.stdout.flush()
