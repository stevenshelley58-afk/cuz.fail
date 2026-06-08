from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from draftcheck_core.database import SessionLocal, init_database
from draftcheck_core.evals import GoldenEvalService
from draftcheck_shared.schemas import GoldenEvalRunRequest

try:
    from scripts.seed_golden_evals import DEFAULT_MANIFEST_DIR, load_case_payloads, seed_golden_eval_cases
except ModuleNotFoundError:
    from seed_golden_evals import DEFAULT_MANIFEST_DIR, load_case_payloads, seed_golden_eval_cases


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run golden eval cases against the configured database.")
    parser.add_argument("--track", default=None, help="Optional eval track to run.")
    parser.add_argument("--commit-sha", default=None)
    parser.add_argument("--model-version", default=None)
    parser.add_argument("--run-by", default="ops")
    parser.add_argument(
        "--seed-manifest",
        default=str(DEFAULT_MANIFEST_DIR),
        help="Manifest JSON file or directory to upsert before running evals.",
    )
    parser.add_argument(
        "--skip-seed-manifest",
        action="store_true",
        help="Run only the already-stored database cases.",
    )
    args = parser.parse_args(argv)

    init_database()
    with SessionLocal() as db:
        if not args.skip_seed_manifest:
            payloads = load_case_payloads(Path(args.seed_manifest))
            if args.track:
                payloads = [payload for payload in payloads if payload.track == args.track]
            seed_golden_eval_cases(db, payloads)
        run = GoldenEvalService(db).run(
            GoldenEvalRunRequest(
                track=args.track,
                commit_sha=args.commit_sha,
                model_version=args.model_version,
                run_by=args.run_by,
            )
        )
        db.commit()

    payload: dict[str, Any] = run.model_dump(mode="json")
    print(json.dumps(payload, sort_keys=True))
    return _exit_code_for_run(payload)


def _exit_code_for_run(payload: dict[str, Any]) -> int:
    metrics = payload.get("metrics")
    if isinstance(metrics, dict) and metrics.get("release_gate_satisfied") is True:
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
