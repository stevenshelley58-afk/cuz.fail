from scripts.wp4_reconcile_aliases import ManifestRow, SourceDoc, classify_row, norm


def source(title: str) -> SourceDoc:
    return SourceDoc(id=f"00000000-0000-0000-0000-{abs(hash(title)) % 10**12:012d}", title=title, canonical_url=f"https://example.test/{title}")


def sources(*titles: str) -> dict[str, SourceDoc]:
    return {norm(title): source(title) for title in titles}


def row(name: str, category: str = "act") -> ManifestRow:
    return ManifestRow(id="11111111-1111-1111-1111-111111111111", instrument_name=name, category=category, status="blocked")


def test_title_variant_links_to_acquired_source() -> None:
    decision = classify_row(row("Western Australia Building Act 2011"), sources("Building Act 2011"))

    assert decision.recommended_status == "acquired"
    assert decision.source_title == "Building Act 2011"


def test_amendment_only_row_becomes_out_of_scope() -> None:
    decision = classify_row(row("Building Amendment Regulations 2024", "regulations"), sources("Building Regulations 2012"))

    assert decision.recommended_status == "out_of_scope"
    assert decision.source_title == "Building Regulations 2012"


def test_repealed_redevelopment_act_links_to_superseding_source_metadata() -> None:
    decision = classify_row(row("Armadale Redevelopment Act 2001"), sources("Metropolitan Redevelopment Authority Act 2011"))

    assert decision.recommended_status == "out_of_scope"
    assert decision.source_title == "Metropolitan Redevelopment Authority Act 2011"


def test_melville_lps6_alias_links_to_acquired_scheme_text() -> None:
    decision = classify_row(
        row("Local Planning Scheme No.6", "local_planning_scheme"),
        sources("City of Melville Local Planning Scheme No. 6 - Scheme Text"),
    )

    assert decision.recommended_status == "acquired"
    assert decision.source_title == "City of Melville Local Planning Scheme No. 6 - Scheme Text"


def test_doubled_title_artifact_links_to_acquired_source() -> None:
    decision = classify_row(row("Building Building Regulations 2012", "regulations"), sources("Building Regulations 2012"))

    assert decision.recommended_status == "acquired"
    assert decision.source_title == "Building Regulations 2012"
