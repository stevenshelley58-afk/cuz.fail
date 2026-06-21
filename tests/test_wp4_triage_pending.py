from scripts.wp4_triage_pending import ManifestRow, classify_row


def row(**overrides) -> ManifestRow:
    base = {
        "id": "00000000-0000-0000-0000-000000000001",
        "instrument_name": "Example Act 1999",
        "category": "act",
        "issuing_authority": "Government of Western Australia",
        "status": "pending",
        "canonical_url": None,
        "notes": None,
    }
    base.update(overrides)
    return ManifestRow(**base)


def test_classify_url_backed_row_for_acquisition() -> None:
    decision = classify_row(
        row(instrument_name="Planning and Development Act 2005", canonical_url="https://example.test/doc.pdf")
    )

    assert decision.recommended_status == "pending"
    assert "WP4 acquisition" in decision.reason


def test_classify_standards_as_metadata_only() -> None:
    decision = classify_row(row(instrument_name="AS/NZS 3959 Construction of buildings", category="standard"))

    assert decision.recommended_status == "metadata_only"
    assert decision.unblock is None


def test_classify_non_planning_act_as_out_of_scope() -> None:
    decision = classify_row(row(instrument_name="Freedom of Information Act 1992", category="act"))

    assert decision.recommended_status == "out_of_scope"


def test_classify_url_backed_non_planning_act_as_out_of_scope() -> None:
    decision = classify_row(
        row(instrument_name="Debt Collectors Licensing Act 1964", category="act", canonical_url="https://example.test/doc.pdf")
    )

    assert decision.recommended_status == "out_of_scope"


def test_classify_planning_act_without_url_as_blocked() -> None:
    decision = classify_row(row(instrument_name="Planning and Development Act 2005", category="act"))

    assert decision.recommended_status == "blocked"
    assert decision.unblock is not None


def test_classify_commencement_fragment_as_out_of_scope() -> None:
    decision = classify_row(row(instrument_name="Assent Commencement Home Building Contracts Act 1991"))

    assert decision.recommended_status == "out_of_scope"
    assert decision.unblock is None


def test_classify_reprint_fragment_as_out_of_scope() -> None:
    decision = classify_row(row(instrument_name="Reprint of the Regional Development Commissions Act 1993"))

    assert decision.recommended_status == "out_of_scope"
    assert decision.unblock is None


def test_classify_extracted_act_fragment_as_out_of_scope() -> None:
    decision = classify_row(row(instrument_name="Act and the Western Australian Development Corporation Act 1983"))

    assert decision.recommended_status == "out_of_scope"
    assert decision.unblock is None
