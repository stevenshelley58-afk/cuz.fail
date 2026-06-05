from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def test_hermes_corpus_import_ingests_public_council_text_and_excludes_standard_text(
    client,
    tmp_path: Path,
) -> None:
    council_text = "\n".join(
        [
            "1.1 Front setback and open space",
            "The front setback should be shown on the site plan.",
            "Open space calculations must identify uncovered outdoor areas.",
        ]
    )
    standard_text = "\n".join(
        [
            "9.9 Proprietary standard fixture",
            "This fake Standards Australia full text mentions sardonyx balustrade spacing.",
        ]
    )
    _write_text(tmp_path, "parsed/council-policy.txt", council_text)
    _write_text(tmp_path, "parsed/fake-standard.txt", standard_text)
    _write_bytes(tmp_path, "raw/council-policy.pdf", b"public council policy fixture")
    _write_bytes(tmp_path, "raw/fake-standard.pdf", b"metadata-only standard fixture")

    inventory_path = _write_inventory(
        tmp_path,
        [
            _inventory_row(
                title="City of Stirling Residential Design Policy",
                authority="City of Stirling",
                local_government="Stirling",
                source_type="local_planning_policy",
                canonical_url="https://www.stirling.wa.gov.au/planning/residential-design-policy",
                parsed_path="parsed/council-policy.txt",
                raw_path="raw/council-policy.pdf",
                text=council_text,
                licence_notes="Public council policy fixture for importer tests.",
            ),
            _inventory_row(
                title="AS 0000 Metadata Only Fixture",
                authority="Standards Australia",
                source_type="australian_standard",
                canonical_url="https://www.standards.org.au/standards-catalogue/fixture/as-0000",
                parsed_path="parsed/fake-standard.txt",
                raw_path="raw/fake-standard.pdf",
                text=standard_text,
                licence_notes="Standards catalogue metadata only; full text must not be stored.",
            ),
        ],
    )

    response = client.post(
        "/v1/sources/hermes-corpus/import",
        json={"inventory_path": str(inventory_path), "corpus_root": str(tmp_path)},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["imported"] == 2
    assert body["metadata_only"] == 1
    assert body["items"][1]["metadata_only"] is True

    sources = client.get("/v1/sources")
    assert sources.status_code == 200, sources.text
    assert any(source["title"] == "City of Stirling Residential Design Policy" for source in sources.json())

    public_search = client.get("/v1/source-chunks/search", params={"q": "front setback open space"})
    assert public_search.status_code == 200, public_search.text
    public_results = public_search.json()
    assert public_results
    assert public_results[0]["citation"]["source_title"] == "City of Stirling Residential Design Policy"
    assert "front setback" in public_results[0]["text"].lower()
    assert "open space" in public_results[0]["text"].lower()

    standard_search = client.get("/v1/source-chunks/search", params={"q": "sardonyx balustrade"})
    assert standard_search.status_code == 200, standard_search.text
    assert standard_search.json() == []


def test_hermes_corpus_import_skips_paid_and_robots_blocked_rows(
    client,
    tmp_path: Path,
) -> None:
    paid_text = "2.1 Paid fixture content mentions mezzanine clearance and private access."
    robots_blocked_text = "3.1 Robots blocked fixture mentions obscure courtyard screening."
    _write_text(tmp_path, "parsed/paid-source.txt", paid_text)
    _write_text(tmp_path, "parsed/robots-blocked-source.txt", robots_blocked_text)

    inventory_path = _write_inventory(
        tmp_path,
        [
            _inventory_row(
                title="Paid Access Planning Manual Fixture",
                authority="Department of Planning, Lands and Heritage",
                source_type="guidance",
                canonical_url="https://www.wa.gov.au/paid-planning-manual-fixture",
                parsed_path="parsed/paid-source.txt",
                text=paid_text,
                access_type="paid",
                licence_notes="Paid access fixture; must be skipped by importer.",
            ),
            _inventory_row(
                title="Robots Blocked Council Policy Fixture",
                authority="City of Bayswater",
                local_government="Bayswater",
                source_type="local_planning_policy",
                canonical_url="https://www.bayswater.wa.gov.au/robots-blocked-policy-fixture",
                parsed_path="parsed/robots-blocked-source.txt",
                text=robots_blocked_text,
                robots_allowed=False,
                licence_notes="Robots disallowed fixture; must be skipped by importer.",
            ),
        ],
    )

    response = client.post(
        "/v1/sources/hermes-corpus/import",
        json={"inventory_path": str(inventory_path), "corpus_root": str(tmp_path)},
    )

    assert response.status_code == 200, response.text
    sources = client.get("/v1/sources")
    assert sources.status_code == 200, sources.text
    source_titles = {source["title"] for source in sources.json()}
    assert "Paid Access Planning Manual Fixture" not in source_titles
    assert "Robots Blocked Council Policy Fixture" not in source_titles

    paid_search = client.get("/v1/source-chunks/search", params={"q": "mezzanine clearance"})
    assert paid_search.status_code == 200, paid_search.text
    assert paid_search.json() == []

    blocked_search = client.get("/v1/source-chunks/search", params={"q": "courtyard screening"})
    assert blocked_search.status_code == 200, blocked_search.text
    assert blocked_search.json() == []


def test_hermes_corpus_import_rejects_restricted_unknown_and_external_paths(
    client,
    tmp_path: Path,
) -> None:
    unknown_text = "4.1 Unknown access fixture mentions hidden loft height."
    restricted_notes_text = "5.1 Restricted notes fixture mentions private courtyard benchmark."
    outside_text = "6.1 Outside path fixture mentions offsite side setback."
    _write_text(tmp_path, "parsed/unknown-source.txt", unknown_text)
    _write_text(tmp_path, "parsed/restricted-notes-source.txt", restricted_notes_text)
    outside_path = tmp_path.parent / f"{tmp_path.name}-outside.txt"
    outside_path.write_text(outside_text, encoding="utf-8")

    inventory_path = _write_inventory(
        tmp_path,
        [
            _inventory_row(
                title="Unknown Access Council Fixture",
                authority="City of Melville",
                local_government="Melville",
                source_type="local_planning_policy",
                canonical_url="https://www.melvillecity.com.au/unknown-access-fixture",
                parsed_path="parsed/unknown-source.txt",
                text=unknown_text,
                access_type="unknown",
                licence_notes="Access not confirmed.",
            ),
            _inventory_row(
                title="Proprietary Notes Council Fixture",
                authority="City of Subiaco",
                local_government="Subiaco",
                source_type="local_planning_policy",
                canonical_url="https://www.subiaco.wa.gov.au/restricted-notes-fixture",
                parsed_path="parsed/restricted-notes-source.txt",
                text=restricted_notes_text,
                licence_notes="Public page but no reuse allowed; proprietary fixture.",
            ),
            _inventory_row(
                title="External Path Council Fixture",
                authority="City of Cockburn",
                local_government="Cockburn",
                source_type="local_planning_policy",
                canonical_url="https://www.cockburn.wa.gov.au/external-path-fixture",
                parsed_path=str(outside_path),
                text=outside_text,
                licence_notes="Public council policy fixture.",
            ),
        ],
    )

    response = client.post(
        "/v1/sources/hermes-corpus/import",
        json={"inventory_path": str(inventory_path), "corpus_root": str(tmp_path)},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["imported"] == 0
    assert body["skipped"] == 2
    assert body["error_count"] == 1

    for query in ["hidden loft height", "private courtyard benchmark", "offsite side setback"]:
        search = client.get("/v1/source-chunks/search", params={"q": query})
        assert search.status_code == 200, search.text
        assert search.json() == []


def _write_inventory(corpus_root: Path, rows: list[dict[str, Any]]) -> Path:
    inventory_path = corpus_root / "source_inventory.jsonl"
    inventory_path.write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n",
        encoding="utf-8",
    )
    return inventory_path


def _write_text(corpus_root: Path, relative_path: str, text: str) -> Path:
    path = corpus_root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _write_bytes(corpus_root: Path, relative_path: str, content: bytes) -> Path:
    path = corpus_root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path


def _inventory_row(**overrides: Any) -> dict[str, Any]:
    text = overrides.pop("text")
    row = {
        "title": "Fixture Source",
        "authority": "Fixture Authority",
        "jurisdiction": "WA",
        "local_government": None,
        "source_type": "fixture",
        "canonical_url": "https://www.wa.gov.au/fixture-source",
        "parsed_path": "parsed/fixture.txt",
        "raw_path": "raw/fixture.pdf",
        "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "published_date": "2026-05-01",
        "effective_date": "2026-05-15",
        "licence_notes": "Public metadata fixture.",
        "robots_allowed": True,
        "access_type": "public",
        "parse_status": "ok",
        "notes": "Hermes importer test fixture.",
    }
    row.update(overrides)
    return row
