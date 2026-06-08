from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from draftcheck_core.database import SessionLocal, init_database
from draftcheck_core.json_utils import to_json
from draftcheck_core.models import GoldenEvalCase
from draftcheck_shared.schemas import GoldenEvalCaseCreate


DEFAULT_MANIFEST_DIR = Path("tests/gold")


def load_case_payloads(path: Path) -> list[GoldenEvalCaseCreate]:
    paths = sorted(path.rglob("*.json")) if path.is_dir() else [path]
    payloads: list[GoldenEvalCaseCreate] = []
    for manifest_path in paths:
        raw = json.loads(manifest_path.read_text(encoding="utf-8"))
        cases = raw.get("cases", raw if isinstance(raw, list) else [])
        if not isinstance(cases, list):
            raise ValueError(f"{manifest_path} must contain a list or a cases list")
        for item in cases:
            if not isinstance(item, dict):
                raise ValueError(f"{manifest_path} contains a non-object case entry")
            payloads.append(GoldenEvalCaseCreate(**item))
    return payloads


def seed_golden_eval_cases(db: Session, payloads: list[GoldenEvalCaseCreate]) -> dict[str, int]:
    created = 0
    updated = 0
    for payload in payloads:
        input_json = to_json(payload.input)
        existing = db.scalar(
            select(GoldenEvalCase).where(
                GoldenEvalCase.track == payload.track,
                GoldenEvalCase.name == payload.name,
            )
        )
        if not existing:
            existing = db.scalar(
                select(GoldenEvalCase)
                .where(
                    GoldenEvalCase.track == payload.track,
                    GoldenEvalCase.input_json == input_json,
                )
                .order_by(GoldenEvalCase.created_at.desc(), GoldenEvalCase.id.desc())
            )
        if existing:
            existing.name = payload.name
            existing.input_json = input_json
            existing.expected_json = to_json(payload.expected)
            existing.source_version_ids_json = to_json(payload.source_version_ids)
            existing.is_active = payload.is_active
            existing.created_by = payload.created_by
            existing.notes = payload.notes
            updated += 1
        else:
            db.add(
                GoldenEvalCase(
                    track=payload.track,
                    name=payload.name,
                    input_json=input_json,
                    expected_json=to_json(payload.expected),
                    source_version_ids_json=to_json(payload.source_version_ids),
                    is_active=payload.is_active,
                    created_by=payload.created_by,
                    notes=payload.notes,
                )
            )
            created += 1
    db.flush()
    return {"created": created, "updated": updated, "total": len(payloads)}


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Seed versioned golden eval cases.")
    parser.add_argument(
        "path",
        nargs="?",
        default=str(DEFAULT_MANIFEST_DIR),
        help="Manifest JSON file or directory of JSON manifests.",
    )
    args = parser.parse_args(argv)

    init_database()
    payloads = load_case_payloads(Path(args.path))
    with SessionLocal() as db:
        result: dict[str, Any] = seed_golden_eval_cases(db, payloads)
        db.commit()
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
