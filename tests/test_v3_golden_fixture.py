from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = ROOT / "tests" / "fixtures" / "golden"
MANIFEST_PATH = FIXTURE_DIR / "manifest.json"

REQUIRED_MANIFEST_FILES = {
    "org_user",
    "project",
    "address_resolution",
    "property_facts",
    "proposal",
    "approved_sources",
    "document_facts",
    "expected_compliance",
}
CONSERVATIVE_STATUSES = {"needs_more_info", "missing_information", "not_assessed"}
PROVEN_STATUSES = {"likely_pass", "likely_fail"}
REGULATORY_PROPERTY_FACT_TYPES = {
    "council",
    "zone",
    "r_code",
    "overlay",
    "bushfire",
    "heritage",
    "lot_area",
    "frontage",
    "primary_street",
    "secondary_street",
}
BANNED_FINAL_CLAIM_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in [
        r"\bis compliant\b",
        r"\bcomplies\b",
        r"\bnon-compliant\b",
        r"\bcertified\b",
        r"\bcertification\b",
        r"\bsubmission[- ]ready\b",
        r"\bapproval granted\b",
        r"\bplanning approval\b",
        r"\bbuilding approval\b",
        r"\bmeets all requirements\b",
        r"\bpasses all checks\b",
        r"\bfinal legal\b",
    ]
]


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_manifest() -> dict[str, Any]:
    return load_json(MANIFEST_PATH)


def load_fixture_files() -> dict[str, Any]:
    manifest = load_manifest()
    return {
        key: load_json(FIXTURE_DIR / relative_path)
        for key, relative_path in manifest["files"].items()
    }


def iter_string_values(value: Any) -> Any:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for child in value.values():
            yield from iter_string_values(child)
    elif isinstance(value, list):
        for child in value:
            yield from iter_string_values(child)


def collect_values_for_keys(value: Any, key_names: set[str]) -> set[str]:
    found: set[str] = set()
    if isinstance(value, dict):
        for key, child in value.items():
            if key in key_names:
                if isinstance(child, str):
                    found.add(child)
                elif isinstance(child, list):
                    found.update(item for item in child if isinstance(item, str))
            found.update(collect_values_for_keys(child, key_names))
    elif isinstance(value, list):
        for child in value:
            found.update(collect_values_for_keys(child, key_names))
    return found


def source_versions_by_id(fixtures: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        version["id"]: version
        for version in fixtures["approved_sources"]["source_versions"]
    }


def citations_by_id(fixtures: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        citation["id"]: citation
        for citation in fixtures["approved_sources"]["citations"]
    }


def promoted_measurements_by_id(fixtures: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        measurement["id"]: measurement
        for measurement in fixtures["document_facts"]["promoted_measurements"]
    }


def test_manifest_references_complete_fixture_files() -> None:
    manifest = load_manifest()
    fixture_root = FIXTURE_DIR.resolve()

    assert set(manifest["files"]) == REQUIRED_MANIFEST_FILES
    for relative_path in manifest["files"].values():
        path = FIXTURE_DIR / relative_path
        assert path.exists(), relative_path
        assert path.suffix == ".json"
        load_json(path)
    for relative_path in manifest["artifacts"].values():
        path = (FIXTURE_DIR / relative_path).resolve()
        assert fixture_root in path.parents
        assert path.exists(), relative_path
        assert path.suffix == ".dxf"

    fixtures = load_fixture_files()
    dxf_artifact = (FIXTURE_DIR / manifest["artifacts"]["site_plan_dxf"]).resolve()
    artifact_hash = hashlib.sha256(dxf_artifact.read_bytes()).hexdigest()
    [document] = fixtures["document_facts"]["documents"]
    assert document["sha256"] == artifact_hash
    assert document["artifact"]["sha256"] == artifact_hash

    org = fixtures["org_user"]["org"]
    users = {user["id"]: user for user in fixtures["org_user"]["users"]}
    project = fixtures["project"]["project"]
    property_record = fixtures["project"]["property"]
    proposal = fixtures["proposal"]["proposal"]
    address_resolution = fixtures["address_resolution"]["address_resolution"]

    assert project["org_id"] == org["id"]
    assert project["created_by_user_id"] in users
    assert property_record["project_id"] == project["id"]
    assert property_record["address_resolution_id"] == address_resolution["id"]
    assert proposal["project_id"] == project["id"]
    assert address_resolution["project_id"] == project["id"]

    fact_types = {fact["fact_type"] for fact in fixtures["property_facts"]["property_facts"]}
    assert {"council", "zone", "r_code", "lot_area", "frontage", "primary_street"}.issubset(fact_types)

    measurement_types = {
        measurement["measurement_type"]
        for measurement in fixtures["document_facts"]["promoted_measurements"]
    }
    assert {
        "lot_area",
        "site_cover_area",
        "open_space_area",
        "primary_street_setback",
        "garage_width",
        "boundary_wall_length",
    }.issubset(measurement_types)

    expected_check_keys = {
        result["check_key"]
        for result in fixtures["expected_compliance"]["expected_results"]
    }
    assert set(manifest["canary_scope"]["tier_1_check_keys"]).issubset(expected_check_keys)


def test_golden_fixture_contains_no_banned_final_claims_or_paid_standard_text() -> None:
    fixtures = load_fixture_files()

    for fixture_name, payload in fixtures.items():
        for text in iter_string_values(payload):
            assert "Standards Australia" not in text, (fixture_name, text)
            for pattern in BANNED_FINAL_CLAIM_PATTERNS:
                assert not pattern.search(text), (fixture_name, pattern.pattern, text)

    source_versions = fixtures["approved_sources"]["source_versions"]
    assert source_versions
    assert all(version["paid_standard_text_stored"] is False for version in source_versions)


def test_regulatory_facts_and_evidence_resolve_to_approved_source_versions() -> None:
    fixtures = load_fixture_files()
    source_versions = source_versions_by_id(fixtures)
    citations = citations_by_id(fixtures)

    assert source_versions
    for source_version_id, version in source_versions.items():
        assert source_version_id.startswith("sv_artificial_")
        assert version["review_status"] == "approved"
        assert version["approval_scope"] == "M1 canary fixture only"
        assert version["licence_status"] == "approved_fixture_only"
        assert re.fullmatch(r"[0-9a-f]{64}", version["content_sha256"])

    assert citations
    for citation_id, citation in citations.items():
        assert citation_id.startswith("cit_artificial_")
        assert citation["source_version_id"] in source_versions
        assert source_versions[citation["source_version_id"]]["review_status"] == "approved"
        assert citation["statement_scope"] == "fixture_only"
        assert citation["quoted_text_stored"] is False
        assert citation["paraphrase"]
        assert citation["provenance"]

    for fact in fixtures["property_facts"]["property_facts"]:
        if fact["fact_type"] in REGULATORY_PROPERTY_FACT_TYPES:
            assert fact["source_version_id"] in source_versions, fact["id"]
            assert fact["citation_id"] in citations, fact["id"]
            assert citations[fact["citation_id"]]["source_version_id"] == fact["source_version_id"]
            assert fact["provenance"], fact["id"]
            assert fact["review_status"] == "human_confirmed"

    address_resolution = fixtures["address_resolution"]["address_resolution"]
    for resolved_record in [
        address_resolution["selected_address_point"],
        address_resolution["selected_parcel"],
    ]:
        assert resolved_record["source_version_id"] in source_versions
        assert resolved_record["citation_id"] in citations
        assert citations[resolved_record["citation_id"]]["source_version_id"] == resolved_record["source_version_id"]
        assert resolved_record["provenance"]

    proposal = fixtures["proposal"]["proposal"]
    assert proposal["classification_source_version_id"] in source_versions
    assert proposal["classification_citation_id"] in citations
    assert (
        citations[proposal["classification_citation_id"]]["source_version_id"]
        == proposal["classification_source_version_id"]
    )


def test_all_source_and_evidence_id_references_resolve() -> None:
    fixtures = load_fixture_files()
    source_versions = source_versions_by_id(fixtures)
    citations = citations_by_id(fixtures)

    source_reference_keys = {
        "source_version_id",
        "source_version_ids",
        "approved_source_version_ids",
        "classification_source_version_id",
    }
    citation_reference_keys = {
        "citation_id",
        "classification_citation_id",
        "rule_evidence_ids",
        "official_citation_ids",
    }

    for fixture_name, payload in fixtures.items():
        source_refs = collect_values_for_keys(payload, source_reference_keys)
        citation_refs = collect_values_for_keys(payload, citation_reference_keys)
        assert source_refs <= set(source_versions), (fixture_name, source_refs - set(source_versions))
        assert citation_refs <= set(citations), (fixture_name, citation_refs - set(citations))


def test_promoted_measurements_have_human_confirmation_and_provenance() -> None:
    fixtures = load_fixture_files()
    source_fact_ids = {
        fact["id"]
        for fact in fixtures["document_facts"]["document_facts"]
    }
    documents = {
        document["id"]: document
        for document in fixtures["document_facts"]["documents"]
    }
    citations = citations_by_id(fixtures)

    for measurement in fixtures["document_facts"]["promoted_measurements"]:
        assert measurement["promotion_status"] == "human_confirmed", measurement["id"]
        assert measurement["human_confirmation"]["confirmed"] is True, measurement["id"]
        assert measurement["human_confirmation"]["confirmed_by_user_id"], measurement["id"]
        assert measurement["human_confirmation"]["confirmed_at"], measurement["id"]
        assert measurement["source_fact_ids"], measurement["id"]
        assert set(measurement["source_fact_ids"]) <= source_fact_ids, measurement["id"]
        assert measurement["citation_id"] in citations, measurement["id"]

        provenance = measurement["provenance"]
        assert provenance["source_document_id"] in documents, measurement["id"]
        assert provenance["method"], measurement["id"]
        assert provenance["calibration"], measurement["id"]

        document = documents[provenance["source_document_id"]]
        if document["media_type"] == "application/pdf" or document["media_type"].startswith("image/"):
            assert provenance["calibration"].get("required") is True, measurement["id"]
            assert provenance["calibration"].get("status") == "human_confirmed", measurement["id"]


def test_expected_results_are_conservative_unless_fully_proven() -> None:
    fixtures = load_fixture_files()
    citations = citations_by_id(fixtures)
    source_versions = source_versions_by_id(fixtures)
    measurements = promoted_measurements_by_id(fixtures)

    allowed_statuses = CONSERVATIVE_STATUSES | PROVEN_STATUSES
    for result in fixtures["expected_compliance"]["expected_results"]:
        assert result["status"] in allowed_statuses, result["id"]
        assert set(result["rule_evidence_ids"]) <= set(citations), result["id"]
        assert set(result["source_version_ids"]) <= set(source_versions), result["id"]
        assert set(result["measurement_ids"]) <= set(measurements), result["id"]
        assert result["decision_trace"]["final_verdict"] is False, result["id"]

        if result["status"] in CONSERVATIVE_STATUSES:
            continue

        trace = result["decision_trace"]
        assert trace["approved_rule_id"], result["id"]
        assert trace["approved_source_version_ids"], result["id"]
        assert trace["official_citation_ids"], result["id"]
        assert trace["promoted_measurement_ids"], result["id"]
        assert trace["calculation_trace_id"], result["id"]
        assert trace["not_excluded_by_precedence"] is True, result["id"]
        assert trace["needs_verification"] is False, result["id"]
