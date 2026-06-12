"""Resolve pending target_manifest URLs from official WA Legislation indexes.

This is a deterministic helper for the WP5/WP4 fixpoint. It only reads the
Western Australian Legislation acts/subsidiary "in force" letter indexes and
fills exact title matches with the official PDF URL.

Run inside the api container:
    python /app/scripts/resolve_manifest_urls.py --apply --report /app/reports/manifest_url_resolution.json
"""
from __future__ import annotations

import argparse
import json
import os
import re
import string
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup
from sqlalchemy import create_engine, text

sys.path.insert(0, "/app/src")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

BASE_URL = "https://www.legislation.wa.gov.au/legislation/statutes.nsf/"
DEFAULT_REPORT = Path(__file__).resolve().parent.parent / "reports" / "manifest_url_resolution.json"
LETTERS = tuple(ch for ch in string.ascii_lowercase if ch != "x")
ACT_CATEGORIES = {"act"}
SUBSIDIARY_CATEGORIES = {"regulations"}


@dataclass(frozen=True)
class IndexEntry:
    title: str
    title_url: str
    pdf_url: str
    collection: str


def norm(value: str) -> str:
    cleaned = re.sub(r"\s+", " ", value).strip()
    return cleaned.casefold()


def parse_index_page(html: str, *, collection: str, page_url: str) -> list[IndexEntry]:
    soup = BeautifulSoup(html, "html.parser")
    entries: list[IndexEntry] = []
    for row in soup.select("article table tbody tr"):
        cells = row.find_all("td")
        if not cells:
            continue
        title_link = cells[0].find("a", href=True)
        if title_link is None:
            continue
        title = title_link.get_text(" ", strip=True)
        pdf_link = row.find("a", href=re.compile(r"query=mrdoc_[^\"']+\.pdf", re.IGNORECASE))
        if pdf_link is None:
            continue
        entries.append(
            IndexEntry(
                title=title,
                title_url=urljoin(page_url, title_link["href"]),
                pdf_url=urljoin(page_url, pdf_link["href"]),
                collection=collection,
            )
        )
    return entries


def fetch_index(client: httpx.Client, *, collection: str) -> dict[str, IndexEntry]:
    prefix = "actsif" if collection == "acts" else "subsif"
    entries: dict[str, IndexEntry] = {}
    for letter in LETTERS:
        page_url = urljoin(BASE_URL, f"{prefix}_{letter}.html")
        response = client.get(page_url)
        if response.status_code == 404:
            continue
        response.raise_for_status()
        for entry in parse_index_page(response.text, collection=collection, page_url=page_url):
            entries.setdefault(norm(entry.title), entry)
    return entries


def pending_rows(database_url: str) -> list[dict[str, Any]]:
    engine = create_engine(database_url)
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT id::text, instrument_name, category, issuing_authority
                FROM target_manifest
                WHERE status = 'pending'
                  AND COALESCE(canonical_url, '') = ''
                  AND category IN ('act', 'regulations')
                ORDER BY category, instrument_name
                """
            )
        ).mappings()
        return [dict(row) for row in rows]


def resolve_rows(rows: list[dict[str, Any]], indexes: dict[str, dict[str, IndexEntry]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    resolved: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []
    for row in rows:
        category = str(row["category"])
        collection = "acts" if category in ACT_CATEGORIES else "subsidiary"
        entry = indexes[collection].get(norm(str(row["instrument_name"])))
        if entry is None:
            unresolved.append(row)
            continue
        resolved.append(
            {
                **row,
                "collection": collection,
                "title_url": entry.title_url,
                "canonical_url": entry.pdf_url,
                "matched_title": entry.title,
            }
        )
    return resolved, unresolved


def apply_resolutions(database_url: str, resolved: list[dict[str, Any]]) -> None:
    engine = create_engine(database_url)
    with engine.begin() as conn:
        for row in resolved:
            conn.execute(
                text(
                    """
                    UPDATE target_manifest
                    SET canonical_url = :canonical_url,
                        index_source_url = COALESCE(index_source_url, :title_url),
                        notes = 'Resolved from official WA Legislation in-force index; run WP4 acquisition.',
                        updated_at = now()
                    WHERE id = CAST(:id AS uuid)
                      AND status = 'pending'
                      AND COALESCE(canonical_url, '') = ''
                    """
                ),
                {
                    "id": row["id"],
                    "canonical_url": row["canonical_url"],
                    "title_url": row["title_url"],
                },
            )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="write resolved URLs to target_manifest")
    parser.add_argument("--report", default=str(DEFAULT_REPORT))
    args = parser.parse_args()

    database_url = os.environ["DATABASE_URL"]
    rows = pending_rows(database_url)
    with httpx.Client(timeout=30.0, follow_redirects=True) as client:
        indexes = {
            "acts": fetch_index(client, collection="acts"),
            "subsidiary": fetch_index(client, collection="subsidiary"),
        }

    resolved, unresolved = resolve_rows(rows, indexes)
    if args.apply and resolved:
        apply_resolutions(database_url, resolved)

    report = {
        "wp": "B3",
        "mode": "apply" if args.apply else "dry_run",
        "pending_rows_scanned": len(rows),
        "resolved": len(resolved),
        "unresolved": len(unresolved),
        "index_counts": {name: len(values) for name, values in indexes.items()},
        "resolved_rows": resolved,
        "unresolved_rows": unresolved,
    }
    output = json.dumps(report, indent=2, default=str)
    print(output)
    if args.report:
        Path(args.report).parent.mkdir(parents=True, exist_ok=True)
        Path(args.report).write_text(output, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
