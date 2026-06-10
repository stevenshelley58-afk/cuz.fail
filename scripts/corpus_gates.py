#!/usr/bin/env python3
"""Phase 6 corpus closure gates (docs/CORPUS_COMPLETENESS_PLAN.md).

Pure-file checker: reads ONLY the committed closure reports under ``reports/``
(no database, no network) and evaluates the Phase 6 CI assertions.

Modes:
    default        advisory -- evaluate every gate, print a table, always exit 0.
    --strict       exit 1 if any gate is not PASS. A missing report file is a
                   failing gate in strict mode ("not yet generated" in advisory).
    --json PATH    also write a machine-readable summary (CI uploads
                   reports/corpus_gates.json as an artifact; it is not committed).

Gates (see the gate registry at the bottom of this module):
    manifest_closure            0 pending manifest rows, 0 orphan sources
    acquisition                 every acquired row parsed ok
    citation_closure            0 unresolved external references, fixpoint reached
    rule_matrix                 matrix 100% filled (value or cited n/a)
    per_doc_gates               every per-document acceptance gate passes
    conflict_sweep              conflict sweep empty
    adversarial_closure         >= 2 consecutive clean adversarial rounds
    adversarial_findings_age    0 open adversarial findings older than 14 days
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_REPORTS_DIR = REPO_ROOT / "reports"

PASS = "PASS"
FAIL = "FAIL"
MISSING = "MISSING"
ERROR = "ERROR"

NA_VALUES = {"n/a", "na", "not applicable"}
STALE_FINDING_DAYS = 14
REQUIRED_CLEAN_ROUNDS = 2


# --------------------------------------------------------------------------
# Tolerant extraction helpers (sibling jobs generate the reports; accept the
# obvious key spellings rather than coupling to one writer).
# --------------------------------------------------------------------------

def _first(data: Any, *keys: str) -> Any:
    """Return the first present key in a dict (None if absent / not a dict)."""
    if not isinstance(data, dict):
        return None
    for key in keys:
        if key in data:
            return data[key]
    return None


def _as_int(value: Any) -> int | None:
    """Coerce ints/floats/numeric strings to int; a list counts its length."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, list):
        return len(value)
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return None
    return None


def _as_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "yes", "reached", "closed"}:
            return True
        if lowered in {"false", "no", "not reached", "open"}:
            return False
    return None


def _parse_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


# --------------------------------------------------------------------------
# Gate checks. Each takes the loaded payloads (filename -> parsed content)
# and returns (ok, detail).
# --------------------------------------------------------------------------

def gate_manifest_closure(payloads: dict[str, Any]) -> tuple[bool, str]:
    """0 manifest rows pending and 0 orphan source flags."""
    data = payloads["manifest_closure.json"]
    pending = _as_int(_first(data, "pending_count", "pending"))
    if pending is None:
        pending = _as_int(_first(_first(data, "totals_by_status"), "pending"))
    orphans = _as_int(_first(data, "orphan_count", "orphan_sources", "orphans"))
    if pending is None:
        return False, "cannot read pending count from manifest_closure.json"
    if orphans is None:
        return False, "cannot read orphan count from manifest_closure.json"
    ok = pending == 0 and orphans == 0
    return ok, f"{pending} pending manifest rows, {orphans} orphan sources"


def gate_acquisition(payloads: dict[str, Any]) -> tuple[bool, str]:
    """Every acquired manifest row has parse_status=ok."""
    data = payloads["acquisition_report.json"]
    rows = _first(data, "rows", "documents", "sources", "acquired_rows")
    if isinstance(rows, list) and rows:
        bad = [
            row for row in rows
            if str(_first(row, "parse_status", "status") or "").lower() != "ok"
        ]
        return not bad, f"{len(rows) - len(bad)}/{len(rows)} acquired rows parsed ok"
    failures = _as_int(
        _first(data, "failures", "parse_failures", "failed", "failed_count", "unparsed_count")
    )
    acquired = _as_int(_first(data, "acquired_count", "acquired_total", "acquired"))
    parsed = _as_int(_first(data, "parsed_ok_count", "parsed_ok", "parse_ok_count"))
    if failures is not None:
        counts_agree = acquired is None or parsed is None or parsed == acquired
        return failures == 0 and counts_agree, f"{failures} acquired rows failed parsing"
    if acquired is not None and parsed is not None:
        return parsed == acquired, f"{parsed}/{acquired} acquired rows parsed ok"
    return False, "unrecognized acquisition_report.json schema"


def gate_citation_closure(payloads: dict[str, Any]) -> tuple[bool, str]:
    """0 unresolved external references and the resolution loop hit a fixpoint."""
    data = payloads["citation_closure.json"]
    unresolved = _as_int(
        _first(data, "unresolved_count", "unresolved_references", "unresolved")
    )
    fixpoint = _as_bool(
        _first(data, "fixpoint_reached", "fixpoint", "closure_reached", "closed")
    )
    if unresolved is None:
        return False, "cannot read unresolved reference count from citation_closure.json"
    if not fixpoint:
        return False, f"{unresolved} unresolved references; fixpoint not reached"
    return unresolved == 0, f"{unresolved} unresolved references; fixpoint reached"


def _gap_is_cited(gap: Any) -> bool:
    if not isinstance(gap, dict):
        return False
    citation = _first(gap, "citation", "cited_reason", "cite", "source", "reason")
    return isinstance(citation, str) and bool(citation.strip())


def gate_rule_matrix(payloads: dict[str, Any]) -> tuple[bool, str]:
    """Every checks x density-codes cell is a value or an n/a cited in the gaps report."""
    matrix: list[list[str]] = payloads["rule_matrix.csv"]
    gaps_data = payloads["rule_matrix_gaps.json"]
    if len(matrix) < 2 or len(matrix[0]) < 2:
        return False, "rule_matrix.csv has no data cells"
    empty = 0
    na_cells = 0
    total = 0
    for row in matrix[1:]:
        for cell in row[1:]:
            total += 1
            value = cell.strip()
            if not value:
                empty += 1
            elif value.lower() in NA_VALUES:
                na_cells += 1
    gaps = _first(gaps_data, "gaps", "cells", "entries")
    if gaps is None and isinstance(gaps_data, list):
        gaps = gaps_data
    if not isinstance(gaps, list):
        return False, "unrecognized rule_matrix_gaps.json schema"
    uncited = sum(1 for gap in gaps if not _gap_is_cited(gap))
    ok = empty == 0 and uncited == 0
    detail = (
        f"{total} cells: {empty} empty, {na_cells} n/a "
        f"({len(gaps)} gap records, {uncited} uncited)"
    )
    return ok, detail


def _doc_passes(doc: Any) -> bool:
    if isinstance(doc, bool):
        return doc
    if not isinstance(doc, dict):
        return False
    verdict = _first(doc, "pass", "passed", "all_pass", "ok")
    if verdict is not None:
        return bool(verdict)
    status = _first(doc, "status", "result")
    if status is not None:
        return str(status).lower() in {"pass", "passed", "ok", "green"}
    gates = _first(doc, "gates", "checks")
    if isinstance(gates, dict) and gates:
        return all(bool(value) for value in gates.values())
    return False


def gate_per_doc_gates(payloads: dict[str, Any]) -> tuple[bool, str]:
    """Every acquired rule-bearing source_version passes its acceptance gate."""
    data = payloads["per_doc_gates.json"]
    docs = _first(data, "documents", "docs", "per_doc", "results", "source_versions")
    if docs is None and isinstance(data, list):
        docs = data
    if isinstance(docs, dict):
        docs = list(docs.values())
    if not isinstance(docs, list):
        return False, "unrecognized per_doc_gates.json schema"
    if not docs:
        return False, "per_doc_gates.json contains no per-document results"
    failed = sum(1 for doc in docs if not _doc_passes(doc))
    return failed == 0, f"{len(docs) - failed}/{len(docs)} documents pass acceptance gates"


def gate_conflict_sweep(payloads: dict[str, Any]) -> tuple[bool, str]:
    """The deterministic conflict sweep found zero unresolved conflicts."""
    data = payloads["conflict_sweep.json"]
    conflicts = _first(data, "conflicts", "findings", "hits", "results")
    if conflicts is None and isinstance(data, list):
        conflicts = data
    count = _as_int(conflicts)
    if count is None:
        count = _as_int(_first(data, "conflict_count", "count", "total"))
    if count is None:
        return False, "unrecognized conflict_sweep.json schema"
    return count == 0, f"{count} conflicts"


def _clean_rounds(data: Any) -> int | None:
    declared = _as_int(
        _first(data, "consecutive_clean_rounds", "clean_consecutive_rounds", "clean_rounds")
    )
    if declared is not None:
        return declared
    rounds = _first(data, "rounds", "round_history")
    if not isinstance(rounds, list):
        return None
    clean = 0
    for rnd in reversed(rounds):
        confirmed = _as_int(
            _first(rnd, "confirmed_findings", "confirmed", "new_gaps", "findings")
        )
        if confirmed == 0:
            clean += 1
        else:
            break
    return clean


def gate_adversarial_closure(payloads: dict[str, Any]) -> tuple[bool, str]:
    """Adversarial rounds ran until >= 2 consecutive rounds with zero confirmed findings."""
    data = payloads["adversarial_closure.json"]
    clean = _clean_rounds(data)
    if clean is None:
        reached = _as_bool(_first(data, "closure_reached", "closed", "closure"))
        if reached is None:
            return False, "unrecognized adversarial_closure.json schema"
        return reached, f"closure_reached={reached}"
    ok = clean >= REQUIRED_CLEAN_ROUNDS
    return ok, f"{clean} consecutive clean rounds (need {REQUIRED_CLEAN_ROUNDS})"


def gate_adversarial_findings_age(payloads: dict[str, Any]) -> tuple[bool, str]:
    """No adversarial finding has sat open for more than 14 days."""
    data = payloads["adversarial_closure.json"]
    stale_declared = _as_int(
        _first(data, "open_findings_older_than_14_days", "stale_open_findings")
    )
    if stale_declared is not None:
        return stale_declared == 0, f"{stale_declared} open findings older than 14 days"
    open_findings = _first(data, "open_findings", "findings_open")
    if isinstance(open_findings, list):
        cutoff = datetime.now(timezone.utc) - timedelta(days=STALE_FINDING_DAYS)
        stale = 0
        unknown_age = 0
        for finding in open_findings:
            opened = _parse_timestamp(
                _first(finding, "opened_at", "created_at", "date", "timestamp")
            )
            if opened is None:
                unknown_age += 1
            elif opened < cutoff:
                stale += 1
        ok = stale == 0 and unknown_age == 0
        return ok, (
            f"{len(open_findings)} open findings: "
            f"{stale} older than 14 days, {unknown_age} with unknown age"
        )
    open_count = _as_int(open_findings)
    if open_count is not None:
        # Count only, no timestamps: 0 passes; otherwise ages are unknown -> fail.
        return open_count == 0, f"{open_count} open findings (ages not reported)"
    return False, "unrecognized open-findings data in adversarial_closure.json"


# --------------------------------------------------------------------------
# Gate registry and runner.
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class Gate:
    name: str
    description: str
    files: tuple[str, ...]
    check: Callable[[dict[str, Any]], tuple[bool, str]]


@dataclass(frozen=True)
class GateResult:
    name: str
    description: str
    status: str
    detail: str
    files: tuple[str, ...]


GATES: tuple[Gate, ...] = (
    Gate(
        "manifest_closure",
        "0 pending manifest rows, 0 orphan sources",
        ("manifest_closure.json",),
        gate_manifest_closure,
    ),
    Gate(
        "acquisition",
        "every acquired row parsed ok",
        ("acquisition_report.json",),
        gate_acquisition,
    ),
    Gate(
        "citation_closure",
        "0 unresolved references, fixpoint reached",
        ("citation_closure.json",),
        gate_citation_closure,
    ),
    Gate(
        "rule_matrix",
        "matrix 100% filled (value or cited n/a)",
        ("rule_matrix.csv", "rule_matrix_gaps.json"),
        gate_rule_matrix,
    ),
    Gate(
        "per_doc_gates",
        "all per-document acceptance gates pass",
        ("per_doc_gates.json",),
        gate_per_doc_gates,
    ),
    Gate(
        "conflict_sweep",
        "conflict sweep empty",
        ("conflict_sweep.json",),
        gate_conflict_sweep,
    ),
    Gate(
        "adversarial_closure",
        f"{REQUIRED_CLEAN_ROUNDS} consecutive clean adversarial rounds",
        ("adversarial_closure.json",),
        gate_adversarial_closure,
    ),
    Gate(
        "adversarial_findings_age",
        f"0 open findings older than {STALE_FINDING_DAYS} days",
        ("adversarial_closure.json",),
        gate_adversarial_findings_age,
    ),
)


def _load_report(path: Path) -> Any:
    if path.suffix == ".csv":
        with path.open(newline="", encoding="utf-8") as handle:
            return list(csv.reader(handle))
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def evaluate_gate(gate: Gate, reports_dir: Path) -> GateResult:
    missing = [name for name in gate.files if not (reports_dir / name).exists()]
    if missing:
        return GateResult(
            gate.name, gate.description, MISSING,
            f"not yet generated: {', '.join(missing)}", gate.files,
        )
    payloads: dict[str, Any] = {}
    for name in gate.files:
        try:
            payloads[name] = _load_report(reports_dir / name)
        except (OSError, json.JSONDecodeError, csv.Error, UnicodeDecodeError) as exc:
            return GateResult(
                gate.name, gate.description, ERROR, f"cannot read {name}: {exc}", gate.files,
            )
    try:
        ok, detail = gate.check(payloads)
    except Exception as exc:  # defensive: a malformed report must not crash CI
        return GateResult(
            gate.name, gate.description, ERROR, f"gate check raised: {exc}", gate.files,
        )
    return GateResult(gate.name, gate.description, PASS if ok else FAIL, detail, gate.files)


def evaluate_all(reports_dir: Path) -> list[GateResult]:
    return [evaluate_gate(gate, reports_dir) for gate in GATES]


def summarize(results: list[GateResult], strict: bool) -> dict[str, Any]:
    counts = {status: 0 for status in (PASS, FAIL, MISSING, ERROR)}
    for result in results:
        counts[result.status] += 1
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": "strict" if strict else "advisory",
        "all_pass": counts[PASS] == len(results),
        "counts": counts,
        "gates": [
            {
                "name": r.name,
                "description": r.description,
                "status": r.status,
                "detail": r.detail,
                "files": list(r.files),
            }
            for r in results
        ],
    }


def print_table(results: list[GateResult], strict: bool) -> None:
    name_width = max(len(r.name) for r in results)
    status_width = max(len(r.status) for r in results)
    mode = "strict" if strict else "advisory"
    print(f"Corpus closure gates ({mode}) -- docs/CORPUS_COMPLETENESS_PLAN.md Phase 6")
    print("-" * 100)
    for result in results:
        detail = result.detail
        if result.status == MISSING and not strict:
            detail = f"{detail} (advisory: not failing yet)"
        print(f"{result.name:<{name_width}}  {result.status:<{status_width}}  {detail}")
    print("-" * 100)
    passed = sum(1 for r in results if r.status == PASS)
    print(f"{passed}/{len(results)} gates pass")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--strict", action="store_true",
        help="exit 1 if any gate is not PASS (missing reports fail)",
    )
    parser.add_argument(
        "--json", type=Path, default=None, metavar="PATH",
        help="write a machine-readable summary to PATH",
    )
    parser.add_argument(
        "--reports-dir", type=Path, default=DEFAULT_REPORTS_DIR,
        help=f"directory containing the closure reports (default: {DEFAULT_REPORTS_DIR})",
    )
    args = parser.parse_args(argv)

    results = evaluate_all(args.reports_dir)
    print_table(results, strict=args.strict)
    summary = summarize(results, strict=args.strict)
    if args.json is not None:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        print(f"summary written to {args.json}")
    if args.strict and not summary["all_pass"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
