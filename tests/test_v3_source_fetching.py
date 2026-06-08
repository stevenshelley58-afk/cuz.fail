from __future__ import annotations

from draftcheck.domain.sources.fetching import (
    extract_candidate_links,
    extract_source_text,
    infer_source_type,
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


def test_infer_source_type_does_not_treat_https_as_tps_scheme() -> None:
    assert (
        infer_source_type(
            "https://www.cockburn.wa.gov.au/City-and-Council/Strategies-and-Plans",
            "Corporate Strategic Planning",
        )
        == "source_document"
    )
    assert (
        infer_source_type(
            "https://www.wa.gov.au/system/files/2026-03/map16_cockburn_tps3_beeliar_locality.pdf",
            "Map 16 - Beeliar locality",
        )
        == "scheme_map"
    )


def test_extract_candidate_links_excludes_non_source_project_and_generic_policy_pages() -> None:
    html = b"""
<html>
  <body>
    <a href="/Building-Planning-and-Roads/Town-Planning-and-Development/Planning-Projects">
      Planning Projects Learn about the City's planning projects.
    </a>
    <a href="/Building-Planning-and-Roads/Town-Planning-and-Development/Glen-Iris-(1)">
      Redevelopment of Cockburn Gateway Shopping City Find out what role the City plays in the redevelopment.
    </a>
    <a href="/Building-Planning-and-Roads/Town-Planning-and-Development/Changing-the-name-of-Port-Coogee">
      Changing the name of North Coogee The City received a proposal and Landgate policy assessment.
    </a>
    <a href="/Building-Planning-and-Roads/Town-Planning-and-Development/Local-Planning-Policies">
      Local Planning Policies
    </a>
    <a href="/Building-Planning-and-Roads/Town-Planning-and-Development/Local-Planning-Strategy-and-Key-Initiatives">
      Local Planning Strategy and Key Initiatives
    </a>
  </body>
</html>
"""

    links = extract_candidate_links(
        "https://www.cockburn.wa.gov.au/Building-Planning-and-Roads/Town-Planning-and-Development",
        html,
    )

    assert [(link.label, link.source_type) for link in links] == [
        ("Local Planning Policies", "local_planning_policy"),
        ("Local Planning Strategy and Key Initiatives", "local_planning_strategy"),
    ]


def test_infer_source_type_requires_planning_specific_policy_and_strategy_tokens() -> None:
    assert (
        infer_source_type(
            "https://www.cockburn.wa.gov.au/Building-Planning-and-Roads/Town-Planning-and-Development/Changing-the-name-of-Port-Coogee",
            "Changing the name of North Coogee The City received a proposal and Landgate policy assessment.",
        )
        == "source_document"
    )
    assert (
        infer_source_type(
            "https://www.cockburn.wa.gov.au/Building-Planning-and-Roads/Town-Planning-and-Development/Local-Planning-Policies",
            "Local Planning Policies",
        )
        == "local_planning_policy"
    )
    assert (
        infer_source_type(
            "https://www.cockburn.wa.gov.au/Building-Planning-and-Roads/Town-Planning-and-Development/Revitalisation-Strategies",
            "Revitalisation Strategies",
        )
        == "source_document"
    )
