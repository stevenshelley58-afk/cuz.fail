from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


MANIFEST_PATH = Path("data/seed/source_manifest.example.yaml")


def test_cockburn_manifest_has_official_anchor_only_sources() -> None:
    sources = _manifest_sources()

    cockburn_anchor_rows = [
        source
        for source in sources
        if source.get("local_government") == "Cockburn"
        and source.get("version_label") == "anchor-only"
    ]

    assert {
        source["canonical_url"] for source in cockburn_anchor_rows
    } == {
        "https://www.wa.gov.au/government/document-collections/city-of-cockburn-planning-information",
        "https://www.cockburn.wa.gov.au/Building-Planning-and-Roads/Town-Planning-and-Development",
    }
    assert {source["authority"] for source in cockburn_anchor_rows} == {
        "City of Cockburn",
        "Department of Planning, Lands and Heritage",
    }
    assert all(source["access_type"] == "public" for source in cockburn_anchor_rows)
    assert all(source["scrape_allowed"] is True for source in cockburn_anchor_rows)
    assert all("content" not in source for source in cockburn_anchor_rows)
    assert all(
        "approve" in source["licence_notes"].lower()
        or "review" in source["licence_notes"].lower()
        for source in cockburn_anchor_rows
    )


def test_cockburn_example_fixture_remains_non_official_and_review_gated() -> None:
    sources = _manifest_sources()

    example = next(
        source
        for source in sources
        if source["title"] == "Cockburn residential policy example fixture"
    )

    assert example["local_government"] == "Cockburn"
    assert example["version_label"] == "example-current"
    assert "content" in example
    assert "example fixture" in example["licence_notes"].lower()
    assert "approved before use as a citable source" in example["licence_notes"].lower()


def _manifest_sources() -> list[dict[str, Any]]:
    manifest = yaml.safe_load(MANIFEST_PATH.read_text(encoding="utf-8"))
    assert isinstance(manifest, dict)
    sources = manifest.get("sources")
    assert isinstance(sources, list)
    return sources
