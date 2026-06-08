from __future__ import annotations

from draftcheck.domain.sources.fetching import (
    extract_candidate_links,
    extract_source_text,
    parse_robots_allows,
)


def test_parse_robots_allows_uses_longest_matching_rule() -> None:
    robots = """
User-agent: *
Disallow: /Building-Planning-and-Roads/
Allow: /Building-Planning-and-Roads/Town-Planning-and-Development
"""

    assert parse_robots_allows(
        robots,
        "/Building-Planning-and-Roads/Town-Planning-and-Development",
    )
    assert not parse_robots_allows(
        robots,
        "/Building-Planning-and-Roads/private-policy.pdf",
    )


def test_extract_html_source_text_keeps_candidate_public_links() -> None:
    html = b"""
<html>
  <head><title>Cockburn Planning</title><script>ignore()</script></head>
  <body>
    <h1>Town Planning and Development</h1>
    <p>Local planning information for residential applications.</p>
    <a href="/Building-Planning-and-Roads/Town-Planning-and-Development/Local-Planning-Policies">
      Local Planning Policies
    </a>
    <a href="/login/private-policy.pdf">Private Policy</a>
  </body>
</html>
"""

    text = extract_source_text(
        html,
        content_type="text/html",
        final_url="https://www.cockburn.wa.gov.au/Building-Planning-and-Roads",
    )

    assert "Cockburn Planning" in text
    assert "Town Planning and Development" in text
    assert "Local Planning Policies" in text
    assert "/login/private-policy.pdf" not in text


def test_extract_candidate_links_returns_structured_source_targets() -> None:
    html = b"""
<html>
  <body>
    <a href="/DATA/DocSetID-1234/Cockburn-Scheme-Text.pdf">Cockburn Scheme Text</a>
    <a href="/Building-Planning-and-Roads/Town-Planning-and-Development/Local-Development-Plans">
      Local Development Plans
    </a>
    <a href="/private/secret-map.pdf">Private Map</a>
    <a href="https://example.com/planning-policy.pdf">External Policy</a>
  </body>
</html>
"""

    links = extract_candidate_links("https://www.cockburn.wa.gov.au/planning", html)

    assert [(link.label, link.source_type, link.url) for link in links] == [
        (
            "Cockburn Scheme Text",
            "local_planning_scheme",
            "https://www.cockburn.wa.gov.au/DATA/DocSetID-1234/Cockburn-Scheme-Text.pdf",
        ),
        (
            "Local Development Plans",
            "local_development_plan",
            "https://www.cockburn.wa.gov.au/Building-Planning-and-Roads/Town-Planning-and-Development/Local-Development-Plans",
        ),
    ]
