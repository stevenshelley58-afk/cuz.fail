from __future__ import annotations

import argparse
from typing import Any


def main() -> int:
    parser = argparse.ArgumentParser(description="Record an infrastructure audit event.")
    parser.add_argument("--action", required=True)
    parser.add_argument("--target-id", required=True)
    parser.add_argument("--actor-id", default="infra-ops")
    parser.add_argument("--target-type", default="infrastructure")
    parser.add_argument("--metadata", action="append", default=[])
    args = parser.parse_args()

    metadata = _metadata_from_pairs(args.metadata)

    from draftcheck_core.audit import record_audit
    from draftcheck_core.database import SessionLocal, init_database

    init_database()
    with SessionLocal() as db:
        event = record_audit(
            db,
            action=args.action,
            target_type=args.target_type,
            target_id=args.target_id,
            actor_id=args.actor_id,
            metadata=metadata,
        )
        db.commit()
        print(event.id)
    return 0


def _metadata_from_pairs(pairs: list[str]) -> dict[str, Any]:
    metadata: dict[str, Any] = {}
    for pair in pairs:
        key, separator, value = pair.partition("=")
        if not separator or not key:
            raise ValueError(f"Metadata must use key=value form: {pair}")
        metadata[key] = _coerce_metadata_value(value)
    return metadata


def _coerce_metadata_value(value: str) -> Any:
    lowered = value.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        return value


if __name__ == "__main__":
    raise SystemExit(main())
