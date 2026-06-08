from __future__ import annotations

from draftcheck.domain.sources.fetching import (
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
