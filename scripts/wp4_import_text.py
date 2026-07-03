"""Import an operator-supplied text transcription for a blocked manifest row.

Companion to wp4_fetch_via_exa.py for documents whose PDFs have no text layer
(scans) or are drawings: a vision model transcribes the document to text, and
this script imports that text through the normal single-insertion path with a
``fetched_via: vision_transcription`` audit trail, then marks the row acquired.

    docker exec -e DRAFTCHECK_EMBEDDING_PROVIDER=deferred draftcheck-wa-v3-api-1 \
      python /app/scripts/wp4_import_text.py \
      --instrument "City of Fremantle 9-15 McCabe Street Local Structure Plan" \
      --text-file /tmp/mccabe_transcription.txt
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, "/app/src")

from sqlalchemy import create_engine, text  # noqa: E402

from draftcheck.domain.identity.roles import IdentityRole  # noqa: E402
from draftcheck.domain.identity.sqlalchemy_store import SqlAlchemyIdentityStore  # noqa: E402
from draftcheck.domain.sources.models import LicenceStatus, SourceReviewStatus  # noqa: E402
from draftcheck.domain.sources.sqlalchemy_store import SqlAlchemySourceLibrary  # noqa: E402

MIN_CHARS = 300  # LDP sheets are short; still refuse empty transcriptions

OPERATOR_EMAIL = os.environ.get("WP4_OPERATOR_EMAIL", "ops@lotfile.app")
ORG_SLUG = os.environ.get("WP4_ORG_SLUG", "draftcheck-wa")
ORG_NAME = os.environ.get("WP4_ORG_NAME", "DraftCheck WA")


def _local_government_for(issuing_authority: str | None) -> str | None:
    authority = str(issuing_authority or "").strip()
    if authority.lower().startswith(("city of ", "town of ", "shire of ")):
        return authority
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--instrument", required=True, help="exact target_manifest.instrument_name")
    ap.add_argument("--text-file", required=True)
    args = ap.parse_args()

    with open(args.text_file, encoding="utf-8") as fh:
        content = fh.read()
    if len(content.strip()) < MIN_CHARS:
        print(f"ERROR: transcription too short ({len(content.strip())} chars)", file=sys.stderr)
        return 2

    database_url = os.environ["DATABASE_URL"].replace(
        "postgresql+asyncpg://", "postgresql+psycopg://"
    )
    engine = create_engine(database_url)
    with engine.begin() as conn:
        row = conn.execute(
            text(
                "SELECT id, category, issuing_authority, canonical_url FROM target_manifest "
                "WHERE instrument_name = :n"
            ),
            {"n": args.instrument},
        ).fetchone()
    if row is None:
        print(f"ERROR: no manifest row named {args.instrument!r}", file=sys.stderr)
        return 2
    row_id, category, authority, url = row

    store = SqlAlchemyIdentityStore.from_database_url(database_url)
    org = store.get_or_create_org(slug=ORG_SLUG, name=ORG_NAME)
    store.get_or_create_user(org=org, email=OPERATOR_EMAIL, role=IdentityRole.OWNER)
    library = SqlAlchemySourceLibrary.from_database_url(database_url)

    result = library.import_source(
        title=args.instrument,
        content=content,
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
        version_label="vision-transcription",
        source_metadata={"wp4": True, "target_manifest_id": str(row_id),
                         "fetched_via": "vision_transcription"},
        version_metadata={"fetched_via": "vision_transcription", "source_url": url,
                          "transcription_note": "text produced by a vision model from the "
                                                "source PDF; verify against the original "
                                                "before any contested use"},
    )
    with engine.begin() as conn:
        conn.execute(
            text(
                "UPDATE target_manifest SET status='acquired', source_document_id=:doc, "
                "notes=:n, last_checked_at=now(), updated_at=now() WHERE id=:id"
            ),
            {"doc": str(result.source.id), "id": row_id,
             "n": f"Acquired via vision transcription ({len(result.chunks)} chunks)"},
        )
    print(f"acquired: {args.instrument} ({len(result.chunks)} chunks, "
          f"duplicate={result.duplicate})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
