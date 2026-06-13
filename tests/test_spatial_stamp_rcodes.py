from scripts.spatial_stamp_rcodes import (
    build_report,
    normalize_r_code,
    parse_r_code,
)


def test_normalize_standard_r_code_tokens() -> None:
    assert normalize_r_code("R20") == "R20"
    assert normalize_r_code("r 30") == "R30"
    assert normalize_r_code("R-40") is None


def test_parse_rr_token_from_label() -> None:
    stamp = parse_r_code(label="Rural Residential RR")

    assert stamp is not None
    assert stamp.r_code == "RR"
    assert stamp.density_code == "RR"


def test_parse_rac_variants() -> None:
    assert parse_r_code(code="R-AC0").r_code == "R-AC0"  # type: ignore[union-attr]
    assert parse_r_code(code="R AC3").r_code == "R-AC3"  # type: ignore[union-attr]
    assert parse_r_code(code="RAC4").r_code == "R-AC4"  # type: ignore[union-attr]


def test_parse_numeric_trusted_metadata_rcode_no() -> None:
    stamp = parse_r_code(metadata={"rcode_no": 60, "zone": "Residential"})

    assert stamp is not None
    assert stamp.r_code == "R60"


def test_parse_ignores_untrusted_bare_number() -> None:
    assert parse_r_code(label="Residential", metadata={"zone_no": 20}) is None


def test_parse_rejects_conflicting_tokens() -> None:
    assert parse_r_code(code="R20", label="Residential R30") is None


def test_build_report_dry_run_counts_would_update_without_db() -> None:
    rows = [
        {"id": "1", "code": "R20", "label": "Residential", "metadata_json": {}},
        {"id": "2", "code": None, "label": "Commercial", "metadata_json": {}},
        {
            "id": "3",
            "code": "R30",
            "label": "Residential",
            "metadata_json": {"r_code": "R30", "density_code": "R30"},
        },
    ]

    report = build_report(rows, apply=False)

    assert report["considered"] == 3
    assert report["matched"] == 2
    assert report["updated"] == 0
    assert report["would_update"] == 1
    assert report["unchanged"] == 1
    assert report["unmatched"] == 1
