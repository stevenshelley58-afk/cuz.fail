from scripts.wp5_citations import (
    AliasTarget,
    ManifestTarget,
    alias_candidates,
    extract_references,
    resolve_reference,
    sentence_for_match,
)


def test_extract_references_returns_verbatim_sentence_quotes() -> None:
    text = (
        "This policy should be read with State Planning Policy 7.3. "
        "The NCC also applies where building work is proposed."
    )

    hits = extract_references(text)

    assert [hit.reference for hit in hits] == ["State Planning Policy 7.3", "NCC"]
    assert hits[0].quote == "This policy should be read with State Planning Policy 7.3."
    assert hits[1].quote == "The NCC also applies where building work is proposed."


def test_sentence_for_match_falls_back_to_chunk_without_terminal_punctuation() -> None:
    text = "Refer to AS/NZS 3500 for plumbing provisions"
    start = text.index("AS/NZS")

    assert sentence_for_match(text, start, start + len("AS/NZS 3500")) == text


def test_extract_references_keeps_multi_word_act_titles() -> None:
    text = (
        "Clearing may require approval under the Environmental Protection Act 1986. "
        "Subdivision is governed by the Planning and Development Act 2005."
    )

    hits = extract_references(text)

    assert [hit.reference for hit in hits] == [
        "Environmental Protection Act 1986",
        "Planning and Development Act 2005",
    ]


def test_extract_references_strips_abbreviation_prefixes() -> None:
    text = (
        "Legislation and policies BC Act Biodiversity Conservation Act 2016 "
        "EP Act Environmental Protection Act 1986"
    )

    hits = extract_references(text)

    assert [hit.reference for hit in hits] == [
        "Biodiversity Conservation Act 2016",
        "Environmental Protection Act 1986",
    ]


def test_resolve_reference_prefers_manifest_name_then_alias() -> None:
    r_codes = ManifestTarget("m1", "State Planning Policy 7.3 - Residential Design Codes Volume 1")
    ncc = ManifestTarget("m2", "National Construction Code 2025 Volume One")
    aliases = [
        AliasTarget("SPP 7.3", "exact", r_codes),
        AliasTarget("NCC", "exact", ncc),
    ]

    assert resolve_reference("State Planning Policy 7.3", [r_codes, ncc], aliases) == r_codes
    assert resolve_reference("NCC", [r_codes, ncc], aliases) == ncc


def test_alias_candidates_include_abbreviated_policy_forms() -> None:
    assert "SPP 7.3" in alias_candidates("State Planning Policy 7.3")
    assert "DC 2.2" in alias_candidates("Development Control Policy 2.2")
    assert "BCA" in alias_candidates("Building Code of Australia")
