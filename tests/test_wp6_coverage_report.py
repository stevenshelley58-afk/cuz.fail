from scripts.wp6_coverage_report import ClauseCoverage, build_report, classify_clause


def coverage(**overrides) -> ClauseCoverage:
    base = {
        "clause_id": "c1",
        "source_version_id": "sv1",
        "source_title": "Source",
        "clause_path": "1.1",
        "rules_count": 0,
        "candidates_count": 0,
        "decode_candidates_count": 0,
        "rejected_candidates_count": 0,
    }
    base.update(overrides)
    return ClauseCoverage(**base)


def test_classify_clause_coverage_states() -> None:
    assert classify_clause(coverage(rules_count=1)) == "covered"
    assert classify_clause(coverage(candidates_count=2, decode_candidates_count=1)) == "decode_not_promoted"
    assert classify_clause(coverage(candidates_count=1)) == "candidate_not_promoted"
    assert classify_clause(coverage()) == "no_candidate"


def test_build_report_groups_uncovered_by_source() -> None:
    report = build_report(
        [
            coverage(clause_id="c1", rules_count=1),
            coverage(clause_id="c2", source_version_id="sv2", source_title="B"),
            coverage(clause_id="c3", source_version_id="sv2", source_title="B"),
        ],
        sample_limit=10,
    )

    assert report["by_status"] == {"covered": 1, "no_candidate": 2}
    assert report["uncovered_total"] == 2
    assert report["source_shards"] == [{"source_version_id": "sv2", "source_title": "B", "uncovered": 2}]
