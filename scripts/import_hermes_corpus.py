from __future__ import annotations

import argparse
import json
from pathlib import Path

from draftcheck_core.database import SessionLocal, init_database
from draftcheck_ingestion.service import SourceIngestionService


def main() -> None:
    args = _parse_args()
    inventory_path = Path(args.inventory_path).expanduser().resolve()
    inventory_jsonl = inventory_path.read_text(encoding="utf-8")
    corpus_root = Path(args.corpus_root).expanduser().resolve() if args.corpus_root else inventory_path.parent

    init_database()
    with SessionLocal() as db:
        result = SourceIngestionService(db).import_hermes_corpus(
            inventory_jsonl=inventory_jsonl,
            corpus_root=corpus_root,
            request_acceptance=args.request_acceptance,
        )
        db.commit()

    print(json.dumps(result.to_dict(), indent=2, default=str))


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import a Hermes corpus inventory JSONL file.")
    parser.add_argument("inventory_path", nargs="?", help="Path to the Hermes inventory JSONL file.")
    parser.add_argument("--inventory", dest="inventory_flag", help="Path to the Hermes inventory JSONL file.")
    parser.add_argument("--corpus-root", help="Optional root directory for corpus files.")
    parser.add_argument(
        "--request-acceptance",
        action="store_true",
        help="Request source acceptance through the governance gate; default imports remain pending review.",
    )
    args = parser.parse_args()
    args.inventory_path = args.inventory_path or args.inventory_flag
    if not args.inventory_path:
        parser.error("inventory_path or --inventory is required")
    return args


if __name__ == "__main__":
    main()
