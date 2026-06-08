from __future__ import annotations

from draftcheck_core.bootstrap_sources import ensure_demo_source_library
from draftcheck_core.database import SessionLocal, init_database
from draftcheck_core.source_support import source_version_can_support_citable_retrieval


def main() -> None:
    init_database()
    with SessionLocal() as db:
        result = ensure_demo_source_library(db)
        db.commit()
        citable = source_version_can_support_citable_retrieval(db, result["source_version_id"])

    action = "created" if result["created"] else "updated"
    if not result["updated"] and not result["created"]:
        action = "already present"
    print(
        "Bootstrap source library "
        f"{action}; source_version_id={result['source_version_id']}; "
        f"rule_rows={len(result['rule_row_ids'])}; citable_retrieval={str(citable).lower()}"
    )


if __name__ == "__main__":
    main()
