"""Post-process Sonnet extraction output into validated rule_candidates SQL.

Pipeline:
  1. Read extractions JSON produced by the Workflow run.
  2. Reload the clause text from the slim batches file so validators can anchor quotes.
  3. Run the same deterministic validators as scripts/wp6_extract.py:
     - quote anchor, normative language, no-orphan numbers, unit normalization,
       rule_key vocabulary, R-code sanity, range priors, operator/pathway vocab.
  4. Bundle validator results per atom and produce an idempotent SQL UPSERT for
     rule_candidates (one row per atom). The extraction_group_id is derived from
     (clause_id, extractor_model) — re-runs replace prior anthropic-family
     candidates for the same clause group rather than piling duplicates.

Outputs:
  data/extraction/cockburn/pilot_validated.json — atoms + validator results.
  data/extraction/cockburn/pilot_candidates.sql — idempotent SQL to apply on the VPS.

No DB access. Pure post-processing.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import uuid
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from draftcheck.extraction.normalize import normalize_unit  # noqa: E402
from draftcheck.extraction.validators import run_all_validators  # noqa: E402
from draftcheck.extraction.vocabulary import OPERATORS  # noqa: E402

ORG_ID = "1d31c315-5087-47df-a8d4-ebfd08efad5d"
ANTHROPIC_NAMESPACE = uuid.UUID("00000000-0000-5000-a000-000000000001")
SKILL_VERSION_ID = "wp6_sonnet_v1"

PATHWAYS = {"deemed_to_comply", "design_principle", "none"}
VALID_R_CODES = {
    f"R{n}".replace(".0", "")
    for n in (5, 10, 12.5, 15, 17.5, 20, 25, 30, 35, 40, 50, 60, 80)
} | {"R12.5", "R17.5", "R100", "R160", "R-AC", "R100-SL"}

# Same priors as scripts/wp6_extract.py:76 — keep in sync.
RANGE_PRIORS: dict[str, tuple[float, float, set]] = {
    "primary_street_setback": (0.0, 20.0, {"m"}),
    "secondary_street_setback": (0.0, 20.0, {"m"}),
    "side_setback": (0.0, 20.0, {"m"}),
    "rear_setback": (0.0, 20.0, {"m"}),
    "site_cover": (10.0, 100.0, {"%"}),
    "open_space": (10.0, 100.0, {"%"}),
    "site_area": (50.0, 10000.0, {"m2"}),
    "outdoor_living_area": (4.0, 200.0, {"m2", "m"}),
    "boundary_wall_length": (1.0, 50.0, {"m"}),
    "building_height": (2.0, 30.0, {"m"}),
    "building_storeys": (1.0, 10.0, {"storeys", None}),
    "garage_width": (1.0, 20.0, {"m"}),
    "garage_dominance": (10.0, 100.0, {"%"}),
    "soft_landscaping": (0.0, 100.0, {"%"}),
    "lot_width": (4.0, 100.0, {"m"}),
    "lot_depth": (10.0, 300.0, {"m"}),
    "minimum_frontage": (4.0, 50.0, {"m"}),
    "wall_height": (2.0, 25.0, {"m"}),
    "ground_floor_height": (0.0, 4.0, {"m"}),
    "ceiling_height": (2.0, 6.0, {"m"}),
    "plot_ratio": (0.1, 15.0, {None}),
    "fence_height_front": (0.3, 4.0, {"m"}),
    "fence_height_side": (0.5, 4.0, {"m"}),
    "retaining_wall_height": (0.1, 6.0, {"m"}),
    "parking_bays_per_dwelling": (0.0, 5.0, {None}),
    "visitor_parking_per_dwelling": (0.0, 2.0, {None}),
    "car_bay_width": (2.0, 5.0, {"m"}),
    "driveway_width": (2.0, 12.0, {"m"}),
    "private_open_space": (4.0, 500.0, {"m2", "m"}),
    "communal_open_space": (10.0, 2000.0, {"m2", "m", "%"}),
    "parking_bays_per_single_house": (0.0, 4.0, {None}),
    "parking_bays_per_grouped_dwelling": (0.0, 4.0, {None}),
    "parking_bays_per_multiple_dwelling": (0.0, 4.0, {None}),
    "bicycle_parking_per_dwelling": (0.0, 4.0, {None}),
    "balcony_area": (1.0, 100.0, {"m2"}),
    "balcony_depth": (0.5, 6.0, {"m"}),
    "building_separation": (0.5, 30.0, {"m"}),
    "eave_width": (0.0, 2.0, {"m"}),
    "awning_depth": (0.5, 5.0, {"m"}),
    "dwelling_area_minimum": (20.0, 500.0, {"m2"}),
    "dwelling_area_average": (40.0, 500.0, {"m2"}),
    "ancillary_dwelling_area": (10.0, 200.0, {"m2"}),
    "ancillary_dwelling_height": (2.0, 10.0, {"m"}),
    "crossover_width": (2.0, 12.0, {"m"}),
    "footpath_setback": (0.0, 10.0, {"m"}),
    "sign_height_max": (0.5, 30.0, {"m"}),
    "sign_area_max": (0.5, 200.0, {"m2"}),
    "lot_orientation_angle": (0.0, 360.0, {None}),
    "noise_attenuation_distance": (1.0, 500.0, {"m"}),
    "building_envelope_height": (2.0, 30.0, {"m"}),
}


def load_clause_index(batches_path: Path) -> dict[str, dict]:
    """clause_id -> {text, title, clause_path, source_version_id}"""
    payload = json.loads(batches_path.read_text(encoding="utf-8"))
    index: dict[str, dict] = {}
    for batch in payload["batches"]:
        for clause in batch:
            index[clause["clause_id"]] = clause
    return index


def normalize_atom(atom: dict) -> dict:
    """Mirror wp6_extract.parse_atoms: normalize_unit on (value, unit)."""
    try:
        value = float(atom.get("value"))
    except (TypeError, ValueError):
        return atom
    value, unit = normalize_unit(value, atom.get("unit"))
    out = dict(atom)
    out["value"] = value
    out["unit"] = unit
    return out


def validate_atom(atom: dict, clause_text: str) -> tuple[dict, bool]:
    """Run the wp6 validator pack; return (results, passed_all)."""
    rule_key = atom.get("rule_key", "")
    operator = atom.get("operator", "")
    pathway = atom.get("pathway", "")
    unit = atom.get("unit")
    value = float(atom.get("value", 0))
    quote = atom.get("quote", "")
    applicability = atom.get("applicability") or {}

    results = run_all_validators(
        quote=quote,
        clause_text=clause_text,
        disposition="rule_bearing",
        value_json={"value": value},
        unit=unit,
        rule_key=rule_key,
    )

    results["operator_vocab"] = {
        "pass": operator in OPERATORS,
        "detail": f"operator {operator!r}",
    }
    results["pathway_mandatory"] = {
        "pass": pathway in PATHWAYS,
        "detail": f"pathway {pathway!r}",
    }
    prior = RANGE_PRIORS.get(rule_key)
    if prior:
        lo, hi, units = prior
        ok = lo <= value <= hi and unit in units
        results["range_prior"] = {
            "pass": ok,
            "detail": f"value {value} {unit} vs prior [{lo},{hi}] {sorted(str(u) for u in units)}",
        }
    codes = applicability.get("density_codes") or []
    bad = [c for c in codes if str(c).upper().replace(" ", "") not in VALID_R_CODES]
    results["r_code_sanity"] = {
        "pass": not bad,
        "detail": f"invalid density codes: {bad}" if bad else "density codes ok",
    }
    passed_all = all(v["pass"] for v in results.values())
    return results, passed_all


def group_id_for(clause_id: str, extractor_model: str) -> str:
    """Idempotent extraction_group_id: same (clause, model) -> same group uuid."""
    return str(uuid.uuid5(ANTHROPIC_NAMESPACE, f"{clause_id}|{extractor_model}"))


def candidate_id_for(group: str, atom_index: int, signature: str) -> str:
    """Idempotent candidate id so a re-run upserts the same row."""
    return str(uuid.uuid5(ANTHROPIC_NAMESPACE, f"{group}|{atom_index}|{signature}"))


def atom_signature(atom: dict) -> str:
    applicability = atom.get("applicability") or {}
    codes = ",".join(sorted(str(c) for c in (applicability.get("density_codes") or [])))
    return "|".join(
        str(part)
        for part in (
            atom.get("rule_key"),
            atom.get("operator"),
            round(float(atom.get("value", 0)), 4),
            atom.get("unit"),
            codes,
            atom.get("pathway"),
            applicability.get("dwelling_type") or "any",
        )
    )


def sql_escape(text: str) -> str:
    return text.replace("'", "''")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--extractions", required=True, help="JSON file with workflow extractions output")
    parser.add_argument("--batches", required=True, help="Slim batches JSON used as the workflow input")
    parser.add_argument(
        "--extractor-model",
        default="anthropic:claude-sonnet-4-6",
        help="extractor_model column value (family is the first ':'-segment)",
    )
    parser.add_argument(
        "--validated-out",
        required=True,
        help="Where to write the validated extractions JSON",
    )
    parser.add_argument(
        "--sql-out",
        required=True,
        help="Where to write the rule_candidates INSERT/UPSERT SQL",
    )
    args = parser.parse_args()

    extractions = json.loads(Path(args.extractions).read_text(encoding="utf-8"))
    clauses = load_clause_index(Path(args.batches))

    counters: Counter[str] = Counter()
    summary: dict[str, int] = {
        "clauses_seen": 0,
        "clauses_no_atoms": 0,
        "atoms_emitted": 0,
        "atoms_validators_passed": 0,
        "atoms_validator_failed": 0,
        "atoms_missing_clause_context": 0,
    }

    validated_atoms: list[dict] = []
    sql_lines: list[str] = []
    sql_lines.append("BEGIN;\n")
    sql_lines.append("-- WP6 Sonnet (3rd-family) candidate slice. Idempotent: re-run safe (PK is uuid5'd).\n\n")

    for entry in extractions.get("extractions", []):
        clause_id = entry.get("clause_id")
        atoms = entry.get("atoms") or []
        summary["clauses_seen"] += 1
        if not atoms:
            summary["clauses_no_atoms"] += 1
            continue
        clause_info = clauses.get(clause_id)
        if not clause_info:
            summary["atoms_missing_clause_context"] += len(atoms)
            counters["clause_id_unknown"] += 1
            continue
        clause_text = clause_info["text"]
        sv_id = clause_info["source_version_id"]
        group = group_id_for(clause_id, args.extractor_model)

        for atom_index, raw_atom in enumerate(atoms):
            atom = normalize_atom(raw_atom)
            validator_results, passed = validate_atom(atom, clause_text)
            summary["atoms_emitted"] += 1
            review_status = "validators_passed" if passed else "validator_failed"
            if passed:
                summary["atoms_validators_passed"] += 1
            else:
                summary["atoms_validator_failed"] += 1
                for k, v in validator_results.items():
                    if not v["pass"]:
                        counters[f"fail_{k}"] += 1

            signature = atom_signature(atom)
            cid = candidate_id_for(group, atom_index, signature)
            prompt_hash = hashlib.sha256(f"{clause_id}|{atom_index}|{args.extractor_model}".encode()).hexdigest()
            value_json = {"value": atom["value"]}
            condition_json = atom.get("applicability") or {}
            metadata = {
                "wp6": True,
                "sonnet_pilot": True,
                "skill_version_id": SKILL_VERSION_ID,
            }

            validated_atoms.append(
                {
                    "candidate_id": cid,
                    "clause_id": clause_id,
                    "source_version_id": sv_id,
                    "rule_key": atom.get("rule_key"),
                    "rule_type": atom.get("rule_type"),
                    "pathway": atom.get("pathway"),
                    "operator": atom.get("operator"),
                    "value": atom["value"],
                    "unit": atom["unit"],
                    "condition_json": condition_json,
                    "quote": atom.get("quote"),
                    "validators": validator_results,
                    "passed_all": passed,
                    "extraction_group_id": group,
                    "extraction_pass": 1,
                    "review_status": review_status,
                    "extractor_model": args.extractor_model,
                    "prompt_hash": prompt_hash,
                    "metadata_json": metadata,
                }
            )

            sql_lines.append(
                "INSERT INTO rule_candidates (\n"
                "  id, org_id, source_version_id, clause_id,\n"
                "  rule_key, rule_type, pathway, operator, value_json, unit,\n"
                "  condition_json, quote, extractor_model, skill_version_id, prompt_hash,\n"
                "  confidence, review_status, metadata_json, extraction_group_id, extraction_pass,\n"
                "  validator_results_json, created_at, updated_at\n"
                ") VALUES (\n"
                f"  '{cid}', '{ORG_ID}', '{sv_id}', '{clause_id}',\n"
                f"  {sql_str(atom.get('rule_key'))}, {sql_str(atom.get('rule_type'))},"
                f" {sql_str(atom.get('pathway'))}, {sql_str(atom.get('operator'))},"
                f" '{json.dumps(value_json)}'::jsonb, {sql_str(atom['unit'])},\n"
                f"  '{sql_escape(json.dumps(condition_json))}'::jsonb,"
                f" {sql_str(atom.get('quote'))},"
                f" {sql_str(args.extractor_model)}, {sql_str(SKILL_VERSION_ID)},"
                f" {sql_str(prompt_hash)},\n"
                f"  NULL, {sql_str(review_status)},"
                f" '{sql_escape(json.dumps(metadata))}'::jsonb,"
                f" '{group}', 1,\n"
                f"  '{sql_escape(json.dumps(validator_results))}'::jsonb, now(), now()\n"
                ")\n"
                "ON CONFLICT (id) DO UPDATE SET\n"
                "  review_status = EXCLUDED.review_status,\n"
                "  validator_results_json = EXCLUDED.validator_results_json,\n"
                "  metadata_json = rule_candidates.metadata_json || EXCLUDED.metadata_json,\n"
                "  updated_at = now();\n"
            )

    sql_lines.append("\nCOMMIT;\n")
    sql_lines.append("\n-- Summary (this slice):\n")
    sql_lines.append(f"-- {json.dumps(summary)}\n")

    Path(args.validated_out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.validated_out).write_text(
        json.dumps(
            {
                "summary": summary,
                "failure_counts": dict(counters),
                "atoms": validated_atoms,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    Path(args.sql_out).write_text("".join(sql_lines), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    if counters:
        print("Validator failure counts:")
        for k, v in counters.most_common():
            print(f"  {k}: {v}")
    return 0


def sql_str(value) -> str:
    if value is None:
        return "NULL"
    return "'" + sql_escape(str(value)) + "'"


if __name__ == "__main__":
    raise SystemExit(main())
