"""WP3 council expansion from WA.gov.au planning-information collections.

This script turns existing WALGA council anchors in ``target_manifest`` into
concrete manifest rows for public WA.gov.au planning documents. It is intentionally
only a discovery/import step: WP4 remains responsible for acquiring document
content, parsing, chunking, and source-version creation.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse, urlunparse

import httpx
from bs4 import BeautifulSoup
from sqlalchemy import create_engine, text

sys.path.insert(0, "/app/src")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

NS = uuid.UUID("7b1e5a52-4f2c-4cf7-9e83-0c8f2a3d6e91")
WA_GOV_BASE = "https://www.wa.gov.au"
WA_GOV_COLLECTION_BASE = f"{WA_GOV_BASE}/government/document-collections"
DEFAULT_REPORT = (
    Path(__file__).resolve().parent.parent / "reports" / "wp3" / "wa_gov_council_instruments.json"
)
USER_AGENT = "DraftCheck-WA-WP3-local-council-discovery/1.0"
SLUG_OVERRIDES = {
    "Shire of Derby-West Kimberley": "shire-of-derbywest-kimberley-planning-information",
}

PDF_RE = re.compile(r"\((?:PDF|DOCX?|XLSX?)[^)]+\)", re.IGNORECASE)
DOCUMENT_PATH_RE = re.compile(r"\.(?:pdf|docx?|xlsx?)(?:$|[?#])", re.IGNORECASE)
MAP_TITLE_RE = re.compile(r"^(?:map|sheet)\s*\d+|\bmap\s+index\b", re.IGNORECASE)
LPP_RE = re.compile(r"\b(?:local planning policy|lpp)\b", re.IGNORECASE)
LDP_RE = re.compile(r"\b(?:local development plan|ldp)\b", re.IGNORECASE)
MRS_RE = re.compile(
    r"\b(?:mrs|prs|gbrs|metropolitan region scheme|peel region scheme|greater bunbury region scheme|region scheme)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class CouncilAnchor:
    authority: str
    canonical_url: str | None
    metadata: dict[str, Any]


@dataclass(frozen=True)
class DiscoveredInstrument:
    instrument_name: str
    category: str
    issuing_authority: str
    index_source_url: str
    canonical_url: str
    source_section: str
    link_text: str
    status: str = "pending"


@dataclass(frozen=True)
class CouncilDiscovery:
    authority: str
    page_url: str
    status_code: int | None
    discovered: list[DiscoveredInstrument]
    error: str | None = None


def database_url() -> str:
    return os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql+psycopg://")


def deterministic_id(kind: str, *parts: object) -> str:
    return str(uuid.uuid5(NS, "|".join([kind, *(str(part) for part in parts)])))


def clean_text(value: str | None) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def clean_link_text(value: str | None) -> str:
    cleaned = clean_text(value)
    cleaned = PDF_RE.sub("", cleaned)
    cleaned = re.sub(r"\s+-\s+Download$", "", cleaned, flags=re.IGNORECASE)
    return clean_text(cleaned).strip(" -")


def council_slug(authority: str) -> str:
    if authority in SLUG_OVERRIDES:
        return SLUG_OVERRIDES[authority]
    value = authority.casefold().replace("&", " and ")
    value = re.sub(r"[^a-z0-9]+", "-", value).strip("-")
    return f"{value}-planning-information"


def wa_gov_planning_url(authority: str) -> str:
    return f"{WA_GOV_COLLECTION_BASE}/{council_slug(authority)}"


def normalise_url(base_url: str, href: str | None) -> str | None:
    if not href:
        return None
    full = urljoin(base_url, href.strip())
    parsed = urlparse(full)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    return urlunparse(parsed._replace(fragment=""))


def is_document_link(url: str, text_value: str) -> bool:
    parsed = urlparse(url)
    if not parsed.netloc.endswith("wa.gov.au"):
        return False
    if "/system/files/" in parsed.path:
        return True
    if DOCUMENT_PATH_RE.search(url):
        return True
    return bool(re.search(r"\b(?:PDF|DOC|DOCX|XLS|XLSX)\b", text_value, re.IGNORECASE))


def classify_document(link_text: str, section: str, url: str) -> str | None:
    haystack = f"{section} {link_text} {url}".casefold()
    section_value = section.casefold()

    if MAP_TITLE_RE.search(link_text) or "scheme map" in haystack:
        return "scheme_map"
    if LPP_RE.search(haystack):
        return "local_planning_policy"
    if LDP_RE.search(haystack):
        return "local_development_plan"
    if "structure plan" in haystack:
        return "structure_plan"
    if "planning strategy" in haystack:
        return "local_planning_strategy"
    if "local planning scheme" in section_value and "map" in link_text.casefold():
        return "scheme_map"
    if "scheme text" in haystack or "local planning scheme" in haystack:
        return "local_planning_scheme"
    if MRS_RE.search(haystack):
        return "region_scheme"
    if "heritage" in haystack:
        return "heritage_register"
    if any(
        term in section_value
        for term in (
            "local planning scheme",
            "local planning strategy",
            "structure plans",
            "mrs amendments",
        )
    ):
        return "planning_publication"
    return None


def instrument_name(authority: str, section: str, link_text: str, category: str) -> str:
    title = clean_link_text(link_text)
    section_title = clean_text(section).strip(" .")
    authority_cf = authority.casefold()
    title_cf = title.casefold()

    if category == "scheme_map" and section_title and section_title.casefold() not in title_cf:
        title = f"{section_title} - {title}"
    elif category in {"structure_plan", "local_development_plan"} and section_title:
        if "structure plan" not in title_cf and "development plan" not in title_cf:
            title = f"{section_title} - {title}"

    if authority_cf not in title.casefold():
        title = f"{authority} {title}"
    return clean_text(title)[:500]


def extract_instruments(authority: str, page_url: str, html: str) -> list[DiscoveredInstrument]:
    soup = BeautifulSoup(html, "lxml")
    section = ""
    discovered: list[DiscoveredInstrument] = []
    seen: set[tuple[str, str]] = set()

    for node in soup.find_all(["h2", "h3", "a"]):
        if node.name in {"h2", "h3"}:
            candidate = clean_text(node.get_text(" "))
            if candidate and candidate.casefold() not in {"contents", "provided by", "contact"}:
                section = candidate
            continue

        raw_text = clean_text(node.get_text(" "))
        link_text = clean_link_text(raw_text)
        url = normalise_url(page_url, node.get("href"))
        if not url or not link_text or not is_document_link(url, raw_text):
            continue

        category = classify_document(link_text, section, url)
        if category is None:
            continue

        name = instrument_name(authority, section, link_text, category)
        key = (name.casefold(), url)
        if key in seen:
            continue
        seen.add(key)
        discovered.append(
            DiscoveredInstrument(
                instrument_name=name,
                category=category,
                issuing_authority=authority,
                index_source_url=page_url,
                canonical_url=url,
                source_section=section,
                link_text=link_text,
            )
        )

    return discovered


def fetch_council(client: httpx.Client, anchor: CouncilAnchor) -> CouncilDiscovery:
    page_url = wa_gov_planning_url(anchor.authority)
    try:
        response = client.get(page_url)
        if response.status_code != 200:
            return CouncilDiscovery(
                authority=anchor.authority,
                page_url=page_url,
                status_code=response.status_code,
                discovered=[],
                error=f"WA.gov planning collection returned HTTP {response.status_code}",
            )
        return CouncilDiscovery(
            authority=anchor.authority,
            page_url=str(response.url),
            status_code=response.status_code,
            discovered=extract_instruments(anchor.authority, str(response.url), response.text),
        )
    except Exception as exc:  # noqa: BLE001
        return CouncilDiscovery(
            authority=anchor.authority,
            page_url=page_url,
            status_code=None,
            discovered=[],
            error=str(exc),
        )


def load_council_anchors(database_url_value: str, authority_like: str | None = None) -> list[CouncilAnchor]:
    query = """
        SELECT issuing_authority, canonical_url, metadata_json
        FROM target_manifest
        WHERE category = 'council_page'
          AND metadata_json->>'wp3_council_anchor' = 'true'
    """
    params: dict[str, Any] = {}
    if authority_like:
        query += " AND issuing_authority ILIKE :authority_like"
        params["authority_like"] = authority_like
    query += " ORDER BY issuing_authority"

    engine = create_engine(database_url_value)
    with engine.connect() as conn:
        rows = conn.execute(text(query), params).mappings().all()
    return [
        CouncilAnchor(
            authority=str(row["issuing_authority"]),
            canonical_url=row["canonical_url"],
            metadata=dict(row["metadata_json"] or {}),
        )
        for row in rows
    ]


def discover_all(
    anchors: list[CouncilAnchor],
    *,
    workers: int,
    timeout_seconds: float,
    limit_councils: int | None = None,
) -> list[CouncilDiscovery]:
    selected = anchors[:limit_councils] if limit_councils else anchors
    limits = httpx.Limits(max_connections=max(workers, 1), max_keepalive_connections=max(workers, 1))
    timeout = httpx.Timeout(timeout_seconds)
    with httpx.Client(
        follow_redirects=True,
        timeout=timeout,
        limits=limits,
        headers={"User-Agent": USER_AGENT},
    ) as client:
        with ThreadPoolExecutor(max_workers=max(workers, 1)) as pool:
            futures = {pool.submit(fetch_council, client, anchor): anchor for anchor in selected}
            results = [future.result() for future in as_completed(futures)]
    return sorted(results, key=lambda result: result.authority)


def apply_instruments(database_url_value: str, discoveries: list[CouncilDiscovery]) -> dict[str, int]:
    engine = create_engine(database_url_value)
    now = datetime.now(UTC).isoformat()
    inserted_or_updated = 0
    unchanged = 0
    with engine.begin() as conn:
        for discovery in discoveries:
            for instrument in discovery.discovered:
                metadata = {
                    "wp3_wa_gov_discovery": True,
                    "source_page": discovery.page_url,
                    "source_section": instrument.source_section,
                    "link_text": instrument.link_text,
                    "discovered_at": now,
                }
                result = conn.execute(
                    text(
                        """
                        INSERT INTO target_manifest (
                            id, instrument_name, category, issuing_authority,
                            index_source_url, canonical_url, status, notes,
                            metadata_json, last_checked_at, created_at, updated_at
                        )
                        VALUES (
                            CAST(:id AS uuid), :instrument_name, :category, :issuing_authority,
                            :index_source_url, :canonical_url, 'pending', :notes,
                            CAST(:metadata AS jsonb), now(), now(), now()
                        )
                        ON CONFLICT (instrument_name, issuing_authority) DO UPDATE SET
                            category = EXCLUDED.category,
                            index_source_url = EXCLUDED.index_source_url,
                            canonical_url = EXCLUDED.canonical_url,
                            status = CASE
                                WHEN target_manifest.status = 'acquired' THEN target_manifest.status
                                WHEN target_manifest.status = 'out_of_scope' THEN target_manifest.status
                                ELSE 'pending'
                            END,
                            notes = CASE
                                WHEN target_manifest.status = 'acquired' THEN target_manifest.notes
                                ELSE EXCLUDED.notes
                            END,
                            metadata_json = target_manifest.metadata_json || EXCLUDED.metadata_json,
                            last_checked_at = now(),
                            updated_at = now()
                        WHERE target_manifest.status <> 'acquired'
                           OR target_manifest.canonical_url IS DISTINCT FROM EXCLUDED.canonical_url
                           OR target_manifest.index_source_url IS DISTINCT FROM EXCLUDED.index_source_url
                           OR target_manifest.category IS DISTINCT FROM EXCLUDED.category
                        """
                    ),
                    {
                        "id": deterministic_id(
                            "manifest", instrument.instrument_name, instrument.issuing_authority
                        ),
                        "instrument_name": instrument.instrument_name,
                        "category": instrument.category,
                        "issuing_authority": instrument.issuing_authority,
                        "index_source_url": instrument.index_source_url,
                        "canonical_url": instrument.canonical_url,
                        "notes": (
                            "WP3 WA.gov council planning collection discovery; "
                            "run WP4 acquisition for this official public document URL."
                        ),
                        "metadata": json.dumps(metadata, sort_keys=True),
                    },
                )
                if result.rowcount:
                    inserted_or_updated += result.rowcount
                else:
                    unchanged += 1
    return {"inserted_or_updated": inserted_or_updated, "unchanged": unchanged}


def report_for(
    discoveries: list[CouncilDiscovery],
    *,
    mode: str,
    anchors_scanned: int,
    changed: dict[str, int],
) -> dict[str, Any]:
    by_category: dict[str, int] = {}
    by_authority: dict[str, int] = {}
    failed: list[dict[str, Any]] = []
    for discovery in discoveries:
        by_authority[discovery.authority] = len(discovery.discovered)
        if discovery.error:
            failed.append(
                {
                    "authority": discovery.authority,
                    "page_url": discovery.page_url,
                    "status_code": discovery.status_code,
                    "error": discovery.error,
                }
            )
        for instrument in discovery.discovered:
            by_category[instrument.category] = by_category.get(instrument.category, 0) + 1

    instruments = [asdict(item) for discovery in discoveries for item in discovery.discovered]
    return {
        "wp": "WP3",
        "mode": mode,
        "source": "wa.gov.au council planning-information collections",
        "anchors_scanned": anchors_scanned,
        "councils_with_documents": sum(1 for discovery in discoveries if discovery.discovered),
        "documents_discovered": len(instruments),
        "by_category": dict(sorted(by_category.items())),
        "by_authority": dict(sorted(by_authority.items())),
        "failed_collections": failed,
        "db_changes": changed,
        "instruments": sorted(instruments, key=lambda item: (item["issuing_authority"], item["instrument_name"])),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--report", default=str(DEFAULT_REPORT))
    parser.add_argument("--limit-councils", type=int)
    parser.add_argument("--authority-like")
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--timeout-seconds", type=float, default=30.0)
    args = parser.parse_args()

    db_url = database_url()
    anchors = load_council_anchors(db_url, authority_like=args.authority_like)
    discoveries = discover_all(
        anchors,
        workers=args.workers,
        timeout_seconds=args.timeout_seconds,
        limit_councils=args.limit_councils,
    )
    changed = apply_instruments(db_url, discoveries) if args.apply else {"inserted_or_updated": 0, "unchanged": 0}
    report = report_for(
        discoveries,
        mode="apply" if args.apply else "dry_run",
        anchors_scanned=len(discoveries),
        changed=changed,
    )
    output = json.dumps(report, indent=2, sort_keys=True)
    print(output)
    if args.report:
        report_path = Path(args.report)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(output, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
