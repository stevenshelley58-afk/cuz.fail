"""Unit tests for scripts/corpus_gates.py (Phase 6 corpus closure gates).

All fixtures are synthetic and written to tmp_path -- nothing here reads or
writes the committed reports/ directory.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
_SPEC = importlib.util.spec_from_file_location(
    "corpus_gates", REPO_ROOT / "scripts" / "corpus_gates.py"
)
assert _SPEC is not None and _SPEC.loader is not None
cg = importlib.util.module_from_spec(_SPEC)
sys.modules["corpus_gates"] = cg  # dataclasses needs the module in sys.modules
_SPEC.loader.exec_module(cg)


# ---------------------------------------------------------------------------
# Fixture builders
# ---------------------------------------------------------------------------

def _write_json(reports_dir: Path, name: str, payload: object) -> None:
    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / name).write_text(json.dumps(payload), encoding="utf-8")


def _write_matrix_csv(reports_dir: Path, rows: list[list[str]]) -> None:
    reports_dir.mkdir(parents=True, exist_ok=True)
    text = "\n".join(",".join(row) for row in rows) + "\n"
    (reports_dir / "rule_matrix.csv").write_text(text, encoding="utf-8")


def write_green_reports(reports_dir: Path) -> None:
    """A fully passing reports/ directory."""
    _write_json(reports_dir, "manifest_closure.json", {"pending_count": 0, "orphan_count": 0})
    _write_json(
        reports_dir,
        "acquisition_report.json",
        {"acquired_count": 3, "parsed_ok_count": 3, "failures": []},
    )
    _write_json(
        reports_dir,
        "citation_closure.json",
        {"unresolved_count": 0, "fixpoint_reached": True},
    )
    _write_matrix_csv(
        reports_dir,
        [
            ["check_key", "R20", "R40"],
            ["setback_front", "6.0m", "4.0m"],
            ["site_coverage", "50%", "n/a"],
        ],
    )
    _write_json(
        reports_dir,
        "rule_matrix_gaps.json",
        {"gaps": [{"check": "site_coverage", "density_code": "R40",
                   "citation": "R-Codes Vol 1 Table 4 (no R40 coverage control)"}]},
    )
    _write_json(
        reports_dir,
        "per_doc_gates.json",
        {"documents": [{"source_version_id": "a", "pass": True},
                       {"source_version_id": "b", "pass": True}]},
    )
    _write_json(reports_dir, "conflict_sweep.json", {"conflicts": []})
    _write_json(
        reports_dir,
        "adversarial_closure.json",
        {"consecutive_clean_rounds": 2, "open_findings": []},
    )


def evaluate(reports_dir: Path, gate_name: str) -> object:
    gate = next(g for g in cg.GATES if g.name == gate_name)
    return cg.evaluate_gate(gate, reports_dir)


# ---------------------------------------------------------------------------
# Per-gate: passing / failing / missing
# ---------------------------------------------------------------------------

def test_manifest_closure_pass(tmp_path: Path) -> None:
    _write_json(tmp_path, "manifest_closure.json", {"pending_count": 0, "orphan_count": 0})
    assert evaluate(tmp_path, "manifest_closure").status == cg.PASS


def test_manifest_closure_fail_pending(tmp_path: Path) -> None:
    _write_json(tmp_path, "manifest_closure.json", {"pending_count": 87, "orphan_count": 0})
    result = evaluate(tmp_path, "manifest_closure")
    assert result.status == cg.FAIL
    assert "87 pending" in result.detail


def test_manifest_closure_fail_orphans(tmp_path: Path) -> None:
    _write_json(tmp_path, "manifest_closure.json", {"pending_count": 0, "orphan_count": 2})
    assert evaluate(tmp_path, "manifest_closure").status == cg.FAIL


def test_manifest_closure_totals_by_status_fallback(tmp_path: Path) -> None:
    _write_json(
        tmp_path,
        "manifest_closure.json",
        {"totals_by_status": {"pending": 0, "acquired": 5}, "orphan_count": 0},
    )
    assert evaluate(tmp_path, "manifest_closure").status == cg.PASS


def test_manifest_closure_missing(tmp_path: Path) -> None:
    result = evaluate(tmp_path, "manifest_closure")
    assert result.status == cg.MISSING
    assert "not yet generated" in result.detail


def test_acquisition_pass_counts(tmp_path: Path) -> None:
    _write_json(
        tmp_path,
        "acquisition_report.json",
        {"acquired_count": 10, "parsed_ok_count": 10, "failures": []},
    )
    assert evaluate(tmp_path, "acquisition").status == cg.PASS


def test_acquisition_pass_rows(tmp_path: Path) -> None:
    _write_json(
        tmp_path,
        "acquisition_report.json",
        {"rows": [{"id": "a", "parse_status": "ok"}, {"id": "b", "parse_status": "ok"}]},
    )
    assert evaluate(tmp_path, "acquisition").status == cg.PASS


def test_acquisition_fail_row_not_parsed(tmp_path: Path) -> None:
    _write_json(
        tmp_path,
        "acquisition_report.json",
        {"rows": [{"id": "a", "parse_status": "ok"}, {"id": "b", "parse_status": "failed"}]},
    )
    result = evaluate(tmp_path, "acquisition")
    assert result.status == cg.FAIL
    assert "1/2" in result.detail


def test_acquisition_fail_failure_list(tmp_path: Path) -> None:
    _write_json(
        tmp_path,
        "acquisition_report.json",
        {"acquired_count": 10, "parsed_ok_count": 9, "failures": [{"id": "x"}]},
    )
    assert evaluate(tmp_path, "acquisition").status == cg.FAIL


def test_acquisition_fail_unrecognized_schema(tmp_path: Path) -> None:
    _write_json(tmp_path, "acquisition_report.json", {"something_else": True})
    assert evaluate(tmp_path, "acquisition").status == cg.FAIL


def test_acquisition_missing(tmp_path: Path) -> None:
    assert evaluate(tmp_path, "acquisition").status == cg.MISSING


def test_citation_closure_pass(tmp_path: Path) -> None:
    _write_json(
        tmp_path,
        "citation_closure.json",
        {"unresolved_count": 0, "fixpoint_reached": True},
    )
    assert evaluate(tmp_path, "citation_closure").status == cg.PASS


def test_citation_closure_fail_unresolved(tmp_path: Path) -> None:
    _write_json(
        tmp_path,
        "citation_closure.json",
        {"unresolved_count": 3, "fixpoint_reached": True},
    )
    assert evaluate(tmp_path, "citation_closure").status == cg.FAIL


def test_citation_closure_fail_no_fixpoint(tmp_path: Path) -> None:
    _write_json(
        tmp_path,
        "citation_closure.json",
        {"unresolved_count": 0, "fixpoint_reached": False},
    )
    assert evaluate(tmp_path, "citation_closure").status == cg.FAIL


def test_citation_closure_unresolved_as_list(tmp_path: Path) -> None:
    _write_json(
        tmp_path,
        "citation_closure.json",
        {"unresolved_references": ["AS 3959"], "fixpoint_reached": True},
    )
    assert evaluate(tmp_path, "citation_closure").status == cg.FAIL


def test_citation_closure_missing(tmp_path: Path) -> None:
    assert evaluate(tmp_path, "citation_closure").status == cg.MISSING


def test_rule_matrix_pass_with_cited_na(tmp_path: Path) -> None:
    _write_matrix_csv(
        tmp_path,
        [["check_key", "R20"], ["setback_front", "6.0m"], ["site_coverage", "n/a"]],
    )
    _write_json(
        tmp_path,
        "rule_matrix_gaps.json",
        {"gaps": [{"check": "site_coverage", "citation": "R-Codes Table 4"}]},
    )
    assert evaluate(tmp_path, "rule_matrix").status == cg.PASS


def test_rule_matrix_fail_empty_cell(tmp_path: Path) -> None:
    _write_matrix_csv(tmp_path, [["check_key", "R20"], ["setback_front", ""]])
    _write_json(tmp_path, "rule_matrix_gaps.json", {"gaps": []})
    result = evaluate(tmp_path, "rule_matrix")
    assert result.status == cg.FAIL
    assert "1 empty" in result.detail


def test_rule_matrix_fail_uncited_gap(tmp_path: Path) -> None:
    _write_matrix_csv(tmp_path, [["check_key", "R20"], ["site_coverage", "n/a"]])
    _write_json(tmp_path, "rule_matrix_gaps.json", {"gaps": [{"check": "site_coverage"}]})
    assert evaluate(tmp_path, "rule_matrix").status == cg.FAIL


def test_rule_matrix_fail_no_data(tmp_path: Path) -> None:
    _write_matrix_csv(tmp_path, [["check_key", "R20"]])
    _write_json(tmp_path, "rule_matrix_gaps.json", {"gaps": []})
    assert evaluate(tmp_path, "rule_matrix").status == cg.FAIL


def test_rule_matrix_missing_either_file(tmp_path: Path) -> None:
    # CSV present, gaps json missing -> still MISSING.
    _write_matrix_csv(tmp_path, [["check_key", "R20"], ["setback_front", "6.0m"]])
    result = evaluate(tmp_path, "rule_matrix")
    assert result.status == cg.MISSING
    assert "rule_matrix_gaps.json" in result.detail


def test_per_doc_gates_pass(tmp_path: Path) -> None:
    _write_json(
        tmp_path,
        "per_doc_gates.json",
        {"documents": [{"id": "a", "pass": True}, {"id": "b", "status": "pass"}]},
    )
    assert evaluate(tmp_path, "per_doc_gates").status == cg.PASS


def test_per_doc_gates_pass_gate_dict(tmp_path: Path) -> None:
    _write_json(
        tmp_path,
        "per_doc_gates.json",
        {"documents": [{"id": "a", "gates": {"clause_dispositions": True,
                                             "no_orphan_numbers": True}}]},
    )
    assert evaluate(tmp_path, "per_doc_gates").status == cg.PASS


def test_per_doc_gates_fail_one_doc(tmp_path: Path) -> None:
    _write_json(
        tmp_path,
        "per_doc_gates.json",
        {"documents": [{"id": "a", "pass": True}, {"id": "b", "pass": False}]},
    )
    result = evaluate(tmp_path, "per_doc_gates")
    assert result.status == cg.FAIL
    assert "1/2" in result.detail


def test_per_doc_gates_fail_empty(tmp_path: Path) -> None:
    _write_json(tmp_path, "per_doc_gates.json", {"documents": []})
    assert evaluate(tmp_path, "per_doc_gates").status == cg.FAIL


def test_per_doc_gates_missing(tmp_path: Path) -> None:
    assert evaluate(tmp_path, "per_doc_gates").status == cg.MISSING


def test_conflict_sweep_pass(tmp_path: Path) -> None:
    _write_json(tmp_path, "conflict_sweep.json", {"conflicts": []})
    assert evaluate(tmp_path, "conflict_sweep").status == cg.PASS


def test_conflict_sweep_pass_bare_list(tmp_path: Path) -> None:
    _write_json(tmp_path, "conflict_sweep.json", [])
    assert evaluate(tmp_path, "conflict_sweep").status == cg.PASS


def test_conflict_sweep_fail(tmp_path: Path) -> None:
    _write_json(
        tmp_path,
        "conflict_sweep.json",
        {"conflicts": [{"rule_key": "setback_front", "rules": ["r1", "r2"]}]},
    )
    assert evaluate(tmp_path, "conflict_sweep").status == cg.FAIL


def test_conflict_sweep_missing(tmp_path: Path) -> None:
    assert evaluate(tmp_path, "conflict_sweep").status == cg.MISSING


def test_adversarial_closure_pass_declared(tmp_path: Path) -> None:
    _write_json(tmp_path, "adversarial_closure.json", {"consecutive_clean_rounds": 2})
    assert evaluate(tmp_path, "adversarial_closure").status == cg.PASS


def test_adversarial_closure_pass_computed_from_rounds(tmp_path: Path) -> None:
    _write_json(
        tmp_path,
        "adversarial_closure.json",
        {"rounds": [{"round": 1, "confirmed_findings": 4},
                    {"round": 2, "confirmed_findings": 0},
                    {"round": 3, "confirmed_findings": 0}]},
    )
    assert evaluate(tmp_path, "adversarial_closure").status == cg.PASS


def test_adversarial_closure_fail_one_clean_round(tmp_path: Path) -> None:
    _write_json(
        tmp_path,
        "adversarial_closure.json",
        {"rounds": [{"round": 1, "confirmed_findings": 2},
                    {"round": 2, "confirmed_findings": 0}]},
    )
    result = evaluate(tmp_path, "adversarial_closure")
    assert result.status == cg.FAIL
    assert "1 consecutive clean" in result.detail


def test_adversarial_closure_missing(tmp_path: Path) -> None:
    assert evaluate(tmp_path, "adversarial_closure").status == cg.MISSING


def test_findings_age_pass_empty(tmp_path: Path) -> None:
    _write_json(
        tmp_path,
        "adversarial_closure.json",
        {"consecutive_clean_rounds": 2, "open_findings": []},
    )
    assert evaluate(tmp_path, "adversarial_findings_age").status == cg.PASS


def test_findings_age_pass_recent_open_finding(tmp_path: Path) -> None:
    recent = (datetime.now(timezone.utc) - timedelta(days=3)).isoformat()
    _write_json(
        tmp_path,
        "adversarial_closure.json",
        {"open_findings": [{"id": 1, "opened_at": recent}]},
    )
    assert evaluate(tmp_path, "adversarial_findings_age").status == cg.PASS


def test_findings_age_fail_stale_open_finding(tmp_path: Path) -> None:
    stale = (datetime.now(timezone.utc) - timedelta(days=20)).isoformat()
    _write_json(
        tmp_path,
        "adversarial_closure.json",
        {"open_findings": [{"id": 1, "opened_at": stale}]},
    )
    result = evaluate(tmp_path, "adversarial_findings_age")
    assert result.status == cg.FAIL
    assert "1 older than 14 days" in result.detail


def test_findings_age_fail_unknown_age(tmp_path: Path) -> None:
    _write_json(
        tmp_path,
        "adversarial_closure.json",
        {"open_findings": [{"id": 1}]},
    )
    assert evaluate(tmp_path, "adversarial_findings_age").status == cg.FAIL


def test_findings_age_declared_stale_count(tmp_path: Path) -> None:
    _write_json(
        tmp_path,
        "adversarial_closure.json",
        {"open_findings_older_than_14_days": 0},
    )
    assert evaluate(tmp_path, "adversarial_findings_age").status == cg.PASS


def test_findings_age_missing(tmp_path: Path) -> None:
    assert evaluate(tmp_path, "adversarial_findings_age").status == cg.MISSING


# ---------------------------------------------------------------------------
# Corrupt report -> ERROR (never a crash)
# ---------------------------------------------------------------------------

def test_corrupt_json_is_error_not_crash(tmp_path: Path) -> None:
    (tmp_path / "conflict_sweep.json").write_text("{not json", encoding="utf-8")
    result = evaluate(tmp_path, "conflict_sweep")
    assert result.status == cg.ERROR


# ---------------------------------------------------------------------------
# CLI behaviour: advisory always exits 0, strict gates the exit code
# ---------------------------------------------------------------------------

def test_advisory_exits_zero_with_no_reports(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    reports = tmp_path / "reports"
    reports.mkdir()
    assert cg.main(["--reports-dir", str(reports)]) == 0
    out = capsys.readouterr().out
    assert "not yet generated" in out


def test_strict_exits_one_with_missing_reports(tmp_path: Path) -> None:
    reports = tmp_path / "reports"
    reports.mkdir()
    assert cg.main(["--reports-dir", str(reports), "--strict"]) == 1


def test_strict_exits_zero_when_all_green(tmp_path: Path) -> None:
    reports = tmp_path / "reports"
    write_green_reports(reports)
    assert cg.main(["--reports-dir", str(reports), "--strict"]) == 0


def test_strict_exits_one_on_single_failing_gate(tmp_path: Path) -> None:
    reports = tmp_path / "reports"
    write_green_reports(reports)
    _write_json(reports, "conflict_sweep.json", {"conflicts": [{"rule_key": "x"}]})
    assert cg.main(["--reports-dir", str(reports), "--strict"]) == 1


def test_json_summary_written(tmp_path: Path) -> None:
    reports = tmp_path / "reports"
    write_green_reports(reports)
    out_path = tmp_path / "out" / "corpus_gates.json"
    assert cg.main(["--reports-dir", str(reports), "--json", str(out_path)]) == 0
    summary = json.loads(out_path.read_text(encoding="utf-8"))
    assert summary["all_pass"] is True
    assert summary["mode"] == "advisory"
    assert {g["name"] for g in summary["gates"]} == {g.name for g in cg.GATES}
    assert all(g["status"] == cg.PASS for g in summary["gates"])


def test_json_summary_counts_missing(tmp_path: Path) -> None:
    reports = tmp_path / "reports"
    reports.mkdir()
    out_path = tmp_path / "corpus_gates.json"
    cg.main(["--reports-dir", str(reports), "--json", str(out_path)])
    summary = json.loads(out_path.read_text(encoding="utf-8"))
    assert summary["all_pass"] is False
    assert summary["counts"][cg.MISSING] == len(cg.GATES)


def test_gate_registry_covers_all_plan_reports() -> None:
    files = {name for gate in cg.GATES for name in gate.files}
    assert files == {
        "manifest_closure.json",
        "acquisition_report.json",
        "citation_closure.json",
        "rule_matrix.csv",
        "rule_matrix_gaps.json",
        "per_doc_gates.json",
        "conflict_sweep.json",
        "adversarial_closure.json",
    }
