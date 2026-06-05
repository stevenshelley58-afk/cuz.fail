from __future__ import annotations

from pathlib import Path

from draftcheck_document_ai.extraction import extract_text_from_bytes
from draftcheck_scraper.lawful_fetcher import parse_robots_allows


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
