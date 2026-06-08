from __future__ import annotations

import argparse
import json

from draftcheck_core.database import SessionLocal, init_database
from draftcheck_core.embeddings import rebuild_source_chunk_embeddings


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Rebuild source chunk embeddings.")
    parser.add_argument("--source-version-id", help="Limit rebuild to one source version.")
    args = parser.parse_args(argv)

    init_database()
    with SessionLocal() as db:
        result = rebuild_source_chunk_embeddings(db, args.source_version_id)
        db.commit()
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
