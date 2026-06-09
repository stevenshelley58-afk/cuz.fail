"""Parse source_version text artifacts into clauses table rows."""
from __future__ import annotations
import hashlib
import json
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
_DEFINITION_RE = re.compile(r'^[""]|\bmeans\b|\bis defined\b', re.IGNORECASE)

# Dimension for stub zero-vector embeddings (must match SOURCE_CHUNK_EMBEDDING_DIMENSION)
_EMBEDDING_DIM = 1536


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


# Stub zero vector for source_chunks.embedding (pgvector, NOT NULL)
_ZERO_VECTOR = "[" + ",".join(["0"] * _EMBEDDING_DIM) + "]"


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
                continue

            # Generate a new clause id
            clause_id = str(uuid.uuid4())

            # Upsert a source_chunk aligned to this clause
            chunk_text_val = body
            chunk_sha = hashlib.sha256(chunk_text_val.encode()).hexdigest()
            chunk_index = i  # use match ordinal as chunk_index

            chunk_row = await session.execute(
                text("""
                    INSERT INTO source_chunks (
                        id, source_version_id, chunk_index, text,
                        token_count, embedding_provider, embedding_model,
                        embedding_dimension, embedding, metadata_json,
                        created_at, updated_at
                    )
                    VALUES (
                        gen_random_uuid(), :sv_id, :chunk_idx, :txt,
                        :token_count, 'stub', 'text-embedding-3-small', 1536,
                        :embedding::vector, :meta,
                        now(), now()
                    )
                    ON CONFLICT (source_version_id, chunk_index) DO UPDATE
                        SET text = EXCLUDED.text,
                            metadata_json = EXCLUDED.metadata_json,
                            updated_at = now()
                    RETURNING id
                """),
                {
                    "sv_id": source_version_id,
                    "chunk_idx": chunk_index,
                    "txt": chunk_text_val,
                    "token_count": len(chunk_text_val.split()),
                    "embedding": _ZERO_VECTOR,
                    "meta": json.dumps({"clause_key": key, "sha256": chunk_sha}),
                },
            )
            chunk_id = chunk_row.scalar()

            # Insert clause, linking to the source_chunk
            await session.execute(
                text(
                    "INSERT INTO clauses "
                    "(id, clause_key, clause_path, clause_type, disposition, "
                    "source_version_id, source_chunk_id, text, created_at, updated_at) "
                    "VALUES (:id, :ck, :cp, 'clause', :disp, :sv, :sc_id, :txt, now(), now())"
                ),
                {
                    "id": clause_id,
                    "ck": key,
                    "cp": number,
                    "disp": disp,
                    "sv": source_version_id,
                    "sc_id": str(chunk_id),
                    "txt": body,
                },
            )
            result_obj.clauses_created += 1

        # After all clauses are processed, populate legal_edges for definition cross-references
        def_rows = await session.execute(
            text(
                "SELECT clause_key FROM clauses "
                "WHERE source_version_id = :sv_id AND disposition = 'definition'"
            ),
            {"sv_id": source_version_id},
        )
        def_keys = {row[0] for row in def_rows.fetchall()}

        if def_keys:
            non_def_rows = await session.execute(
                text(
                    "SELECT id, clause_key, text FROM clauses "
                    "WHERE source_version_id = :sv_id AND disposition != 'definition'"
                ),
                {"sv_id": source_version_id},
            )
            for clause_row in non_def_rows.fetchall():
                _clause_id_val, clause_key_val, clause_text_val = clause_row
                if not clause_text_val:
                    continue
                for def_key in def_keys:
                    # Extract a searchable term from the definition clause key
                    # clause_key format: "{number}_{slug}", e.g. "1_2_setback"
                    parts = def_key.split("_", 2)
                    term = parts[-1].replace("_", " ") if len(parts) >= 1 else ""
                    if not term or len(term) <= 3:
                        continue
                    if term.lower() in clause_text_val.lower():
                        await session.execute(
                            text("""
                                INSERT INTO legal_edges (
                                    id, from_type, from_ref, to_type, to_ref,
                                    relation, confidence, review_status,
                                    metadata_json, created_at, updated_at
                                )
                                VALUES (
                                    gen_random_uuid(), 'clause', :from_ref,
                                    'clause', :to_ref,
                                    'references_definition', 0.7, 'pending_review',
                                    '{}', now(), now()
                                )
                                ON CONFLICT (from_type, from_ref, to_type, to_ref, relation)
                                DO NOTHING
                            """),
                            {"from_ref": clause_key_val, "to_ref": def_key},
                        )

        await session.commit()
        return result_obj
