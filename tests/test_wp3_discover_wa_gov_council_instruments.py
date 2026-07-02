from scripts.wp3_discover_wa_gov_council_instruments import (
    classify_document,
    council_slug,
    extract_instruments,
    instrument_name,
)


def test_council_slug_handles_punctuation() -> None:
    assert council_slug("Shire of Wyndham-East Kimberley") == (
        "shire-of-wyndham-east-kimberley-planning-information"
    )
    assert council_slug("Shire of Cocos (Keeling) Islands") == (
        "shire-of-cocos-keeling-islands-planning-information"
    )
    assert council_slug("Shire of Derby-West Kimberley") == (
        "shire-of-derbywest-kimberley-planning-information"
    )


def test_classify_scheme_map_before_scheme_text() -> None:
    assert classify_document("Map 01 - Central locality", "Local planning scheme", "https://x.test/a.pdf") == (
        "scheme_map"
    )
    assert classify_document("Albany Scheme Text", "Local planning scheme", "https://x.test/a.pdf") == (
        "local_planning_scheme"
    )


def test_instrument_name_prefixes_authority_and_section_for_maps() -> None:
    assert instrument_name("Shire of Murray", "Local planning scheme", "Map 01 - Murray overall", "scheme_map") == (
        "Shire of Murray Local planning scheme - Map 01 - Murray overall"
    )


def test_instrument_name_does_not_double_prefix_authority() -> None:
    assert instrument_name(
        "City of Fremantle",
        "Local planning strategy",
        "City of Fremantle Local Planning Strategy",
        "local_planning_strategy",
    ) == "City of Fremantle Local Planning Strategy"


def test_extract_instruments_from_wa_gov_collection_html() -> None:
    html = """
    <main>
      <h2>Local planning strategy</h2>
      <a href="/system/files/2026-01/fremantle-strategy.pdf">
        Local Planning Strategy for the City of Fremantle (PDF, 10.14MB)
      </a>
      <h2>Local planning scheme</h2>
      <a href="/system/files/2026-01/fremantle-scheme-text.pdf">
        Fremantle Scheme Text (PDF, 2MB)
      </a>
      <a href="/system/files/2026-01/fremantle-map-01.pdf">
        Map 01 - Fremantle overall (PDF, 5MB)
      </a>
      <h2>Structure plans</h2>
      <a href="/system/files/2026-01/fremantle-east-end-structure-plan.pdf">
        East End Structure Plan (PDF, 7MB)
      </a>
      <h2>Provided by</h2>
      <a href="/contact">Department contact</a>
    </main>
    """

    rows = extract_instruments(
        "City of Fremantle",
        "https://www.wa.gov.au/government/document-collections/city-of-fremantle-planning-information",
        html,
    )

    assert [row.category for row in rows] == [
        "local_planning_strategy",
        "local_planning_scheme",
        "scheme_map",
        "structure_plan",
    ]
    assert rows[0].canonical_url == "https://www.wa.gov.au/system/files/2026-01/fremantle-strategy.pdf"
    assert rows[2].instrument_name == "City of Fremantle Local planning scheme - Map 01 - Fremantle overall"
