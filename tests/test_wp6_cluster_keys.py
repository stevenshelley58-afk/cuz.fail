from scripts.wp6_apply_clustering import load_map
from scripts.wp6_cluster_keys import cluster_rule_keys, is_variant_of, normalize_rule_key


def test_is_variant_of_absorbs_rcode_and_minmax_qualifiers() -> None:
    # Clean variants — the member is the target plus R-code / min-max qualifiers.
    assert is_variant_of("r20_min_frontage", "min_frontage")
    assert is_variant_of("site_cover_max_r30", "site_cover")
    assert is_variant_of("outdoor_living_area_min_r25", "outdoor_living_area")
    assert is_variant_of("rear_setback_min_r2_5", "rear_setback")


def test_is_variant_of_rejects_cross_dimension_and_operator() -> None:
    # Dimension mismatch: length must NOT be absorbed into width.
    assert not is_variant_of("driveway_length_min", "driveway_width")
    # Operator/scope mismatch: a maximum lot area is not a per-dwelling minimum.
    assert not is_variant_of("max_lot_area", "min_lot_area_per_dwelling")
    # Different concept that merely shares a token.
    assert not is_variant_of("wall_height", "boundary_wall_length")
    # Conservative by design: a non-qualifier descriptor ("double") is NOT absorbed,
    # so we under-merge a borderline variant rather than risk a wrong merge.
    assert not is_variant_of("double_garage_width_max", "garage_width")


def test_normalize_rule_key_groups_simple_variants() -> None:
    assert normalize_rule_key("Primary Street Setbacks") == "primary_street_setback"
    assert normalize_rule_key("primary-street-setback") == "primary_street_setback"
    assert normalize_rule_key("primary_street_setback") == "primary_street_setback"


def test_cluster_rule_keys_uses_deterministic_canonical_key() -> None:
    clusters = cluster_rule_keys(
        [
            {"rule_key": "Primary Street Setbacks", "candidate_count": 2},
            {"rule_key": "primary-street-setback", "candidate_count": 1},
            {"rule_key": "site_cover_pct", "candidate_count": 3},
        ]
    )

    by_key = {cluster.normalized_key: cluster for cluster in clusters}

    assert by_key["primary_street_setback"].canonical_rule_key == "primary_street_setback"
    assert by_key["primary_street_setback"].total_candidates == 3
    assert by_key["site_cover_percent"].canonical_rule_key == "site_cover_percent"


def test_load_map_rejects_duplicate_rule_key(tmp_path) -> None:
    path = tmp_path / "map.csv"
    path.write_text(
        "rule_key,canonical_rule_key\n"
        "site_cover,site_cover\n"
        "site_cover,site_cover_percent\n",
        encoding="utf-8",
    )

    try:
        load_map(path)
    except ValueError as exc:
        assert "duplicate rule_key" in str(exc)
    else:
        raise AssertionError("expected duplicate map row to fail")
