from __future__ import annotations

from pathlib import Path

from draftcheck_document_ai.extraction import extract_text_from_bytes
from draftcheck_scraper.lawful_fetcher import assert_lawful_source, parse_robots_allows


def test_robots_parser_honours_disallow_rules():
    robots = """
    User-agent: *
    Disallow: /private
    Disallow: /tmp/
    """
    assert parse_robots_allows(robots, "/public/policy.pdf") is True
    assert parse_robots_allows(robots, "/private/policy.pdf") is False
    assert parse_robots_allows(robots, "/tmp/source.pdf") is False


def test_html_extraction_for_source_fetch_path():
    html = b"<html><body><h1>5.1.3 Front setback</h1><p>Primary street setback text.</p></body></html>"
    text = extract_text_from_bytes(html, "text/html")
    assert "5.1.3 Front setback" in text
    assert "Primary street setback text" in text


def test_lawful_fetcher_refuses_restricted_access_terms():
    for notes in [
        "subscription required",
        "paid access only",
        "proprietary no redistribution",
        "licence required before reuse",
    ]:
        try:
            assert_lawful_source(
                "https://www.wa.gov.au/public-policy",
                licence_notes=notes,
                access_type="public",
            )
        except ValueError as exc:
            assert str(exc) == "Source metadata indicates restricted access"
        else:  # pragma: no cover - assertion branch
            raise AssertionError(f"restricted notes were accepted: {notes}")


def test_source_ingest_refuses_fetch_when_scrape_disallowed(client):
    response = client.post(
        "/v1/sources/ingest",
        json={
            "title": "No scrape source",
            "jurisdiction": "WA",
            "authority": "Example authority",
            "source_type": "local_planning_policy",
            "canonical_url": "https://example.test/no-scrape-policy",
            "licence_notes": "Do not fetch.",
            "access_type": "public",
            "scrape_allowed": False,
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "scrape_allowed is false for this source"


def test_check_definition_yaml_import_endpoint(client):
    yaml_text = Path("data/seed/check_definitions.example.yaml").read_text(encoding="utf-8")
    response = client.post("/v1/checks/definitions/import", json={"manifest_yaml": yaml_text})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["imported"] >= 24
    assert {
        "site_cover",
        "open_space",
        "front_setback",
        "garage_dominance",
        "bal_bushfire_trigger",
        "dimension_completeness",
    }.issubset(set(body["keys"]))
