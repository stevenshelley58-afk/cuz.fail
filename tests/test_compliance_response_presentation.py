from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

from draftcheck.api.compliance import _check_result_response
from draftcheck.db.models import Clause, Rule, Source, SourceVersion


def test_check_result_response_exposes_customer_facing_group_and_source() -> None:
    rule_id = uuid4()
    source_version_id = uuid4()
    source_id = uuid4()
    clause_id = uuid4()
    row = SimpleNamespace(
        id=uuid4(),
        check_key="site_cover",
        status="needs_more_info",
        requirement_json={
            "rule_id": str(rule_id),
            "threshold_value": 50,
            "threshold_unit": "%",
        },
        proposed_json={},
        decision_trace_json={
            "note": "missing_measurement_fact: proposed_site_cover_pct",
            "missing_info_reason": "missing_measurement_fact",
        },
        citations_json=[f"site_cover | source_version:{source_version_id}"],
        why_this_applies="Site coverage is not to exceed the table value.",
        drawing_evidence_json={},
        review_reason=None,
        human_override_json={},
        reviewed_by_user_id=None,
        reviewed_at=None,
    )
    rule = SimpleNamespace(
        source_version_id=source_version_id,
        clause_id=clause_id,
        check_type="numeric_threshold",
        pathway="deemed_to_comply",
        rule_logic_json={
            "what_it_means": "The building footprint may cover no more than the permitted share of the lot."
        },
    )
    version = SimpleNamespace(source_id=source_id, version_label="2026 edition")
    source = SimpleNamespace(
        title="Residential Design Codes Volume 1",
        canonical_url="https://example.test/r-codes-volume-1.pdf",
        authority="Western Australian Planning Commission",
    )
    clause = SimpleNamespace(section_ref="Clause 5.1.4", clause_path="5.1.4")
    db = Mock()

    def get(model, identifier):
        return {
            (Rule, rule_id): rule,
            (SourceVersion, source_version_id): version,
            (Source, source_id): source,
            (Clause, clause_id): clause,
        }.get((model, identifier))

    db.get.side_effect = get

    response = _check_result_response(row, db)

    assert response.category == "site_cover"
    assert response.what_it_means == (
        "The building footprint may cover no more than the permitted share of the lot."
    )
    assert response.modality == "deemed_to_comply"
    assert response.source is not None
    assert response.source.title == "Residential Design Codes Volume 1"
    assert response.source.url == "https://example.test/r-codes-volume-1.pdf"
    assert response.source.section == "Clause 5.1.4"
