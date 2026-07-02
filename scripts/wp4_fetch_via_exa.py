"""Recover blocked target_manifest rows by fetching page text via the Exa index.

Many council document pages are JS-rendered viewers that yield no text to our
fetcher (guard-blocked as landing pages), but Exa's crawler has the fully
rendered text. For each blocked row whose notes indicate a landing/low-text
block, pull text via Exa /contents; if substantial, import through the normal
single-insertion path (import_source) and mark the row acquired.

Reads EXA_API_KEY from env. Run inside the api container with deferred
embeddings:
    docker exec -e EXA_API_KEY=... -e DRAFTCHECK_EMBEDDING_PROVIDER=deferred \
      draftcheck-wa-v3-api-1 python /app/scripts/wp4_fetch_via_exa.py \
      --report /app/reports/wp4_exa_recovery.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
from typing import Any

sys.path.insert(0, "/app/src")

from sqlalchemy import create_engine, text  # noqa: E402

from draftcheck.domain.identity.roles import IdentityRole  # noqa: E402
from draftcheck.domain.identity.sqlalchemy_store import SqlAlchemyIdentityStore  # noqa: E402
from draftcheck.domain.sources.models import LicenceStatus, SourceReviewStatus  # noqa: E402
from draftcheck.domain.sources.sqlalchemy_store import SqlAlchemySourceLibrary  # noqa: E402

MIN_CHARS = 2000  # a real instrument text, not a nav shell

OPERATOR_EMAIL = os.environ.get("WP4_OPERATOR_EMAIL", "ops@lotfile.app")
ORG_SLUG = os.environ.get("WP4_ORG_SLUG", "draftcheck-wa")
ORG_NAME = os.environ.get("WP4_ORG_NAME", "DraftCheck WA")


def _local_government_for(issuing_authority: str | None) -> str | None:
    authority = str(issuing_authority or "").strip()
    if authority.lower().startswith(("city of ", "town of ", "shire of ")):
        return authority
    return None


def exa_contents(key: str, url: str) -> str:
    body = {"urls": [url], "text": {"maxCharacters": 200000}, "livecrawl": "fallback"}
    req = urllib.request.Request(
        "https://api.exa.ai/contents",
        data=json.dumps(body).encode("utf-8"),
        headers={"x-api-key": key, "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    results = payload.get("results") or []
    return (results[0].get("text") or "") if results else ""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=200)
    ap.add_argument("--report", required=True)
    args = ap.parse_args()

    key = os.environ.get("EXA_API_KEY", "")
    if not key:
        print("ERROR: EXA_API_KEY not set", file=sys.stderr)
        return 2

    database_url = os.environ["DATABASE_URL"].replace(
        "postgresql+asyncpg://", "postgresql+psycopg://"
    )
    engine = create_engine(database_url)
    store = SqlAlchemyIdentityStore.from_database_url(database_url)
    org = store.get_or_create_org(slug=ORG_SLUG, name=ORG_NAME)
    store.get_or_create_user(org=org, email=OPERATOR_EMAIL, role=IdentityRole.OWNER)
    library = SqlAlchemySourceLibrary.from_database_url(database_url)

    with engine.begin() as conn:
        rows = conn.execute(
            text(
                """
                SELECT id, instrument_name, category, issuing_authority, canonical_url
                FROM target_manifest
                WHERE status = 'blocked'
                  AND (notes ILIKE '%landing page%' OR notes ILIKE '%parseable text%')
                ORDER BY instrument_name LIMIT :lim
                """
            ),
            {"lim": args.limit},
        ).fetchall()

    items: list[dict[str, Any]] = []
    recovered = still_blocked = 0
    for row in rows:
        row_id, name, category, authority, url = row
        try:
            page_text = exa_contents(key, url)
        except Exception as exc:  # noqa: BLE001
            items.append({"instrument": name, "status": "exa_error", "notes": str(exc)[:150]})
            still_blocked += 1
            continue
        if len(page_text.strip()) < MIN_CHARS:
            items.append({"instrument": name, "status": "still_blocked",
                          "notes": f"exa returned {len(page_text.strip())} chars (<{MIN_CHARS})"})
            still_blocked += 1
            continue
        try:
            result = library.import_source(
                title=str(name),
                content=page_text,
                uri=url,
                publisher=str(authority or ""),
                licence_status=LicenceStatus.PENDING_REVIEW,
                review_status=SourceReviewStatus.PENDING_REVIEW,
                media_type="text/plain",
                metadata_only=False,
                jurisdiction="WA",
                authority=str(authority or ""),
                local_government=_local_government_for(authority),
                source_type=str(category),
                access_type="public",
                licence_notes="",
                version_label="exa-index-fetch",
                source_metadata={"wp4": True, "target_manifest_id": str(row_id),
                                 "fetched_via": "exa_contents"},
                version_metadata={"fetched_via": "exa_contents", "source_url": url},
            )
            with engine.begin() as conn:
                conn.execute(
                    text(
                        "UPDATE target_manifest SET status='acquired', "
                        "source_document_id=:doc, notes=:n, last_checked_at=now(), "
                        "updated_at=now() WHERE id=:id"
                    ),
                    {"doc": str(result.source.id), "id": row_id,
                     "n": f"Recovered via Exa index fetch ({len(result.chunks)} chunks)"},
                )
            recovered += 1
            items.append({"instrument": name, "status": "acquired",
                          "notes": f"{len(result.chunks)} chunks via exa"})
        except Exception as exc:  # noqa: BLE001
            items.append({"instrument": name, "status": "import_error", "notes": str(exc)[:200]})
            still_blocked += 1

    out = {"wp": "wp4-exa-recovery", "processed": len(rows),
           "summary": {"recovered": recovered, "still_blocked": still_blocked},
           "items": items}
    os.makedirs(os.path.dirname(args.report), exist_ok=True)
    with open(args.report, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1)
    print(json.dumps(out["summary"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
