from scripts.wp6_apply_clustering import load_map
from scripts.wp6_cluster_keys import cluster_rule_keys, normalize_rule_key


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
