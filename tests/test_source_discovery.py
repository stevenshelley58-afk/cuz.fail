from __future__ import annotations

import asyncio
import json
from pathlib import Path

import httpx

from draftcheck_scraper.source_discovery import (
    DiscoverySettings,
    discover_manifest_sources,
    extract_candidate_links,
)


def test_extract_candidate_links_filters_to_lawful_public_documents() -> None:
    html = """
    <a href="/documents/r-codes-volume-1.pdf">R-Codes Volume 1</a>
    <a href="https://www.standards.org.au/standards-catalogue/fixture/as-0000">AS metadata</a>
    <a href="https://example.com/private.pdf">External private PDF</a>
    <a href="/login/secret-policy.pdf">Login PDF</a>
    <a href="mailto:test@example.com">Email</a>
    """

    links = extract_candidate_links("https://www.wa.gov.au/source-page", html)

    assert [link.url for link in links] == [
        "https://www.wa.gov.au/documents/r-codes-volume-1.pdf",
        "https://www.standards.org.au/standards-catalogue/fixture/as-0000",
    ]


def test_discover_manifest_sources_writes_inventory_and_metadata_only_rows(tmp_path: Path) -> None:
    manifest_yaml = """
sources:
  - title: WA source anchor
    jurisdiction: WA
    authority: Department of Planning, Lands and Heritage
    source_type: r_code
    canonical_url: https://www.wa.gov.au/source-page
    licence_notes: Public source fixture.
    access_type: public
    scrape_allowed: true
  - title: AS metadata anchor
    jurisdiction: AU
    authority: Standards Australia
    source_type: standard_metadata
    canonical_url: https://www.standards.org.au/standards-catalogue/fixture/as-0000
    licence_notes: Metadata only.
    access_type: public
    scrape_allowed: true
"""

    transport = httpx.MockTransport(_mock_discovery_response)
    summary = asyncio.run(
        discover_manifest_sources(
            manifest_yaml,
            tmp_path,
            DiscoverySettings(max_depth=1, max_urls_per_anchor=5, delay_seconds=0),
            transport=transport,
        )
    )

    assert summary.inventory_rows == 2
    assert summary.parsed_rows == 1
    assert summary.metadata_only_rows == 1

    inventory = [
        json.loads(line)
        for line in (tmp_path / "source_inventory.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    parsed = next(row for row in inventory if row["parse_status"] == "ok")
    metadata = next(row for row in inventory if row["parse_status"] == "metadata_only")

    assert parsed["canonical_url"] == "https://www.wa.gov.au/documents/r-codes-volume-1.txt"
    assert parsed["parsed_path"]
    assert (tmp_path / parsed["parsed_path"]).read_text(encoding="utf-8").startswith("1.1 Front setback")
    assert metadata["canonical_url"] == "https://www.standards.org.au/standards-catalogue/fixture/as-0000"
    assert metadata["raw_path"] is None
    assert metadata["parsed_path"] is None
    assert (tmp_path / "reports" / "source_summary.md").is_file()


def _mock_discovery_response(request: httpx.Request) -> httpx.Response:
    if request.url.path == "/robots.txt":
        return httpx.Response(200, text="User-agent: *\n")
    if str(request.url) == "https://www.wa.gov.au/source-page":
        return httpx.Response(
            200,
            headers={"content-type": "text/html"},
            text='<a href="/documents/r-codes-volume-1.txt">R-Codes Volume 1</a>',
        )
    if str(request.url) == "https://www.wa.gov.au/documents/r-codes-volume-1.txt":
        return httpx.Response(
            200,
            headers={"content-type": "text/plain"},
            text="1.1 Front setback\nPublic planning source fixture.",
        )
    return httpx.Response(404, text="not found")
