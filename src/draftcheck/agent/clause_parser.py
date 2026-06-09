"""Parse source_version text into clauses table rows."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


CLAUSE_PATTERN = re.compile(r"^(\d+\.(?:\d+\.)*\d*)\s+(.+)$", re.MULTILINE)

RULE_BEARING_KEYWORDS = frozenset(
    {
        "must",
        "shall",
        "not exceed",
        "at least",
        "minimum",
        "maximum",
        "required",
        "permitted",
        "shall not",
        "must not",
        "prohibited",
    }
)

_SLUG_RE = re.compile(r"[^\w]+")


@dataclass
class ClauseParseResult:
    clauses_created: int
    clauses_updated: int


def _slugify(heading: str) -> str:
    """Convert '5.1.1 Front Setback' → '5_1_1_front_setback'."""
    normalized = heading.lower().replace(".", "_")
    return _SLUG_RE.sub("_", normalized).strip("_")


def _determine_disposition(heading: str, body: str) -> str:
    """Classify a clause into one of the five valid dispositions."""
    combined = (heading + " " + body).lower()
    if any(kw in combined for kw in RULE_BEARING_KEYWORDS):
        return "rule_bearing"
    stripped = body.lstrip()
    if stripped.startswith('"') or combined.startswith("means ") or " means " in combined[:80]:
        return "definitional"
    heading_lower = heading.lower()
    if any(w in heading_lower for w in ("application", "lodgement", "lodgment", "procedure")):
        return "procedural"
    return "informational"


class ClauseParser:
    """Stateless parser: converts raw source text into Clause ORM rows."""

    async def parse_source_version(
        self, source_version_id: str, session: AsyncSession
    ) -> ClauseParseResult:
        """Parse the text artifact for *source_version_id* and upsert clause rows.

        Expects an artifact row with kind='parsed_text' linked to the source version.
        Falls back gracefully if no artifact is found (returns 0/0).
        """
        # Load the parsed_text artifact for this source version
        result = await session.execute(
            text(
                """
                SELECT a.content
                FROM artifacts a
                WHERE a.subject_id = :sv_id
                  AND a.kind = 'parsed_text'
                ORDER BY a.created_at DESC
                LIMIT 1
                """
            ),
            {"sv_id": source_version_id},
        )
        row = result.fetchone()
        if row is None:
            return ClauseParseResult(clauses_created=0, clauses_updated=0)

        raw_text: str = row[0] or ""
        matches = list(CLAUSE_PATTERN.finditer(raw_text))

        created = 0
        updated = 0
        now = datetime.now(UTC)

        for i, match in enumerate(matches):
            number = match.group(1)  # e.g. "5.1.1"
            heading = match.group(2).strip()  # e.g. "Front Setback"

            # Body is everything between this match and the next (or end of text)
            body_start = match.end()
            body_end = matches[i + 1].start() if i + 1 < len(matches) else len(raw_text)
            body = raw_text[body_start:body_end].strip()

            clause_key = _slugify(f"{number} {heading}")
            disposition = _determine_disposition(heading, body)

            # Check if clause already exists
            existing = await session.execute(
                text(
                    """
                    SELECT id FROM clauses
                    WHERE source_version_id = :sv_id AND clause_key = :key
                    """
                ),
                {"sv_id": source_version_id, "key": clause_key},
            )
            existing_row = existing.fetchone()

            if existing_row is None:
                await session.execute(
                    text(
                        """
                        INSERT INTO clauses
                            (id, source_version_id, clause_key, heading, body,
                             disposition, created_at, updated_at)
                        VALUES
                            (:id, :sv_id, :key, :heading, :body,
                             :disposition, :now, :now)
                        """
                    ),
                    {
                        "id": str(uuid4()),
                        "sv_id": source_version_id,
                        "key": clause_key,
                        "heading": heading,
                        "body": body,
                        "disposition": disposition,
                        "now": now,
                    },
                )
                created += 1
            else:
                await session.execute(
                    text(
                        """
                        UPDATE clauses
                        SET heading = :heading,
                            body = :body,
                            disposition = :disposition,
                            updated_at = :now
                        WHERE id = :id
                        """
                    ),
                    {
                        "heading": heading,
                        "body": body,
                        "disposition": disposition,
                        "now": now,
                        "id": str(existing_row[0]),
                    },
                )
                updated += 1

        await session.commit()
        return ClauseParseResult(clauses_created=created, clauses_updated=updated)
