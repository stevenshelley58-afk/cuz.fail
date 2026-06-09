"""Parse source_version text artifacts into clauses table rows."""
from __future__ import annotations
import re
import logging
import uuid
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

_CLAUSE_RE = re.compile(r"^(\d+(?:\.\d+)*)\s+(.+)$", re.MULTILINE)
_RULE_BEARING = frozenset(
    [
        "must",
        "shall",
        "not exceed",
        "at least",
        "minimum",
        "maximum",
        "required",
        "permitted",
        "no more than",
        "no less than",
    ]
)
_DEFINITION_RE = re.compile(r'^["“]|\bmeans\b|\bis defined\b', re.IGNORECASE)


@dataclass
class ClauseParseResult:
    clauses_created: int = 0
    clauses_updated: int = 0
    errors: list[str] = field(default_factory=list)


def _disposition(heading: str, body: str) -> str:
    text = (heading + " " + body).lower()
    if any(kw in text for kw in _RULE_BEARING):
        return "rule_bearing"
    if _DEFINITION_RE.search(body[:120]):
        return "definition"
    if any(
        w in heading.lower()
        for w in ("application", "lodgement", "procedure", "process")
    ):
        return "procedural"
    return "informational"


def _clause_key(number: str, heading: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", heading.lower()).strip("_")[:40]
    return f"{number.replace('.', '_')}_{slug}"


class ClauseParser:
    async def parse_source_version(
        self, source_version_id: str, session
    ) -> ClauseParseResult:
        from sqlalchemy import text

        result_obj = ClauseParseResult()

        r = await session.execute(
            text(
                "SELECT id, storage_path FROM artifacts "
                "WHERE subject_id = :sv_id AND kind = 'parsed_text' "
                "ORDER BY created_at DESC LIMIT 1"
            ),
            {"sv_id": source_version_id},
        )
        artifact = r.fetchone()
        if not artifact:
            logger.warning(
                "No parsed_text artifact for source_version %s", source_version_id
            )
            return result_obj

        try:
            import pathlib

            text_content = pathlib.Path(artifact[1]).read_text(encoding="utf-8")
        except Exception as exc:
            result_obj.errors.append(str(exc))
            return result_obj

        matches = list(_CLAUSE_RE.finditer(text_content))
        for i, m in enumerate(matches):
            number = m.group(1)
            heading = m.group(2).strip()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text_content)
            body = text_content[m.end() : end].strip()
            key = _clause_key(number, heading)
            disp = _disposition(heading, body)

            existing = await session.execute(
                text(
                    "SELECT id FROM clauses "
                    "WHERE clause_key = :ck AND source_version_id = :sv"
                ),
                {"ck": key, "sv": source_version_id},
            )
            if existing.fetchone():
                result_obj.clauses_updated += 1
            else:
                await session.execute(
                    text(
                        "INSERT INTO clauses "
                        "(id, clause_key, clause_path, clause_type, disposition, "
                        "source_version_id, created_at, updated_at) "
                        "VALUES (:id, :ck, :cp, 'clause', :disp, :sv, now(), now())"
                    ),
                    {
                        "id": str(uuid.uuid4()),
                        "ck": key,
                        "cp": number,
                        "disp": disp,
                        "sv": source_version_id,
                    },
                )
                result_obj.clauses_created += 1

        await session.commit()
        return result_obj
