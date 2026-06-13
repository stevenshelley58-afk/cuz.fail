from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from scripts.parser_sample_evidence import check_evidence, load_evidence


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "parser_sample_evidence.py"
TEMPLATE = ROOT / "docs" / "parser-sample-evidence-template.json"


def test_parser_sample_evidence_passes_reviewed_sanitized_sample() -> None:
    check = check_evidence(_valid_evidence())

    assert check.status == "passed"
    assert check.errors == ()
    assert check.report["valid_sample_count"] == 1
    assert check.report["matched_fact_count"] == 2
    assert check.report["beta_status"] == "not_beta_ready"
    assert (
        "persistence-connected validation is DB-owned"
        in check.report["beta_blockers_remaining"][0]
    )


def test_parser_sample_evidence_template_is_valid() -> None:
    check = check_evidence(load_evidence(TEMPLATE))

    assert check.status == "passed"
    assert check.report["valid_sample_count"] == 1
    assert check.report["beta_status"] == "not_beta_ready"


def test_parser_sample_evidence_blocks_when_no_reviewed_samples() -> None:
    check = check_evidence({"schema_version": "parser_real_sample_evidence_v1", "samples": []})

    assert check.status == "blocked"
    assert any("at least 1 reviewed sample" in error for error in check.errors)
    assert check.report["valid_sample_count"] == 0


def test_parser_sample_evidence_rejects_raw_or_identifying_content() -> None:
    evidence = _valid_evidence()
    evidence["samples"][0]["source_text"] = "Front setback: 4.5 m"
    evidence["samples"][0]["document"]["original_filename"] = "client-42-site-plan.pdf"

    check = check_evidence(evidence)

    assert check.status == "blocked"
    assert any("source_text is not allowed" in error for error in check.errors)
    assert any("original_filename is not allowed" in error for error in check.errors)


def test_parser_sample_evidence_detects_mismatched_fact_values() -> None:
    evidence = _valid_evidence()
    evidence["samples"][0]["extracted_facts"][0]["numeric_value"] = 4.8

    check = check_evidence(evidence)

    assert check.status == "blocked"
    assert any("front_setback" in error and "delta" in error for error in check.errors)
    assert check.report["samples"][0]["mismatched_fact_count"] == 1


def test_parser_sample_evidence_blocks_false_positive_facts() -> None:
    evidence = _valid_evidence()
    evidence["samples"][0]["extracted_facts"].append(
        {
            "fact_key": "unreviewed_height",
            "fact_type": "building_height",
            "numeric_value": 8.4,
            "unit": "m",
            "confidence": 0.72,
            "review_status": "operator_reviewed",
            "measurement_compliance_ready": False,
        }
    )

    check = check_evidence(evidence)

    assert check.status == "blocked"
    assert any("unreviewed_height" in error and "no expected counterpart" in error for error in check.errors)
    assert check.report["samples"][0]["false_positive_count"] == 1


def test_parser_sample_evidence_cli_writes_report_and_returns_nonzero_for_blocked(
    tmp_path: Path,
) -> None:
    evidence_path = tmp_path / "evidence.json"
    report_path = tmp_path / "report.json"
    evidence = _valid_evidence()
    evidence["samples"][0]["sanitization"]["operator_reviewed"] = False
    evidence_path.write_text(json.dumps(evidence), encoding="utf-8")

    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            str(evidence_path),
            "--output",
            str(report_path),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=10,
    )

    assert completed.returncode == 2
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["status"] == "blocked"
    assert any("operator_reviewed must be true" in error for error in report["errors"])


def _valid_evidence() -> dict[str, object]:
    return {
        "schema_version": "parser_real_sample_evidence_v1",
        "samples": [
            {
                "sample_id": "operator-reviewed-pdf-001",
                "reviewed_by": "operator.fixture",
                "reviewed_at": "2026-06-13T03:00:00+00:00",
                "sanitization": {
                    "operator_reviewed": True,
                    "raw_source_retained": False,
                    "contains_personal_info": False,
                    "contains_client_identifiers": False,
                },
                "document": {
                    "media_type": "application/pdf",
                    "parser_name": "draftcheck.pdf_text_parser",
                    "parser_version": "v0.1",
                    "source_hash_sha256": "a" * 64,
                    "page_count": 2,
                },
                "expected_facts": [
                    {
                        "fact_key": "front_setback",
                        "fact_type": "setback",
                        "numeric_value": 4.5,
                        "unit": "m",
                        "tolerance": 0.001,
                    },
                    {
                        "fact_key": "lot_area",
                        "fact_type": "site_area",
                        "numeric_value": 450.0,
                        "unit": "m2",
                    },
                ],
                "extracted_facts": [
                    {
                        "fact_key": "front_setback",
                        "fact_type": "setback",
                        "numeric_value": 4.5,
                        "unit": "m",
                        "confidence": 0.91,
                        "review_status": "human_confirmed",
                        "measurement_compliance_ready": False,
                    },
                    {
                        "fact_key": "lot_area",
                        "fact_type": "site_area",
                        "numeric_value": 450.0,
                        "unit": "m2",
                        "confidence": 0.94,
                        "review_status": "operator_reviewed",
                        "measurement_compliance_ready": False,
                    },
                ],
            }
        ],
    }
