"""WP4b — legal graph: exceptions, carve-outs, cross-instrument links.

Implements docs/CORPUS_COMPLETENESS_PLAN.md Phase 4b items 1-2 on top of the
one mechanism from MASTER_REBUILD_PLAN §5.4: rules.rule_type + legal_edges
(no carve-out JSON blobs).  AI proposes, deterministic validators decide.

Runs INSIDE the api container (psycopg3 + LLM env present):

    docker exec draftcheck-wa-v3-api-1 python /app/scripts/wp4b_legal_graph.py \
        exceptions [--source-version <uuid>] [--limit N] [--enforce] \
        --report /app/reports/legal_graph.json

    docker exec draftcheck-wa-v3-api-1 python /app/scripts/wp4b_legal_graph.py \
        edges [--pair <sv_uuid>:<sv_uuid>] [--limit N] [--max-chars N] [--enforce] \
        --report /app/reports/legal_graph.json

Subcommands
-----------
exceptions
    Sweep clauses flagged with exception language (notwithstanding / despite /
    except where / unless — the wp6_extract sweep list, via
    draftcheck.checks.precedence.EXCEPTION_PHRASES).  For each, ensure a rules
    row with rule_type='exception' + structured condition_json + an
    'exception_to' legal_edges row to its base rule.  Base-rule location and
    quote validation are deterministic; only the structuring of condition_json
    uses a blind 2-model LLM pass with a mandatory verbatim quote anchor
    (whitespace-normalised containment in the clause text, and the quote must
    contain a phrase from the closed exception list).  Unstructurable →
    rule_candidates pending_review + review_items; approved base rules with an
    unresolved exception are reported as blocked (--enforce demotes them to
    pending_review).

edges
    For instrument pairs that already share 'cites' edges (Phase 3 output),
    run a blind 2-model long-context proposal pass for relations in
    {modifies, overrides, exception_to, applies_with,
    performance_alternative_to, depends_on}.  Every proposed edge REQUIRES a
    verbatim quote from the *from* document; the deterministic validator
    (draftcheck.checks.precedence.validate_edge_quote) confirms containment
    AND modification/exception language from the closed phrase list.
    No quote, no edge.  2/2 model agreement → review_status approved; 1/2 →
    pending_review.  Missing API keys → escalation logged, LLM pass skipped,
    deterministic parts (existing-edge quote audit) still run.

Writes the JSON report (counts, blocked approvals, quoteless rejections,
escalations) to --report (default reports/legal_graph.json).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

sys.path.insert(0, "/app/src")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

import psycopg  # noqa: E402
from psycopg.types.json import Json  # noqa: E402

from draftcheck.checks.precedence import (  # noqa: E402
    EDGE_RELATIONS,
    EXCEPTION_PHRASES,
    validate_edge_quote,
)
from draftcheck.extraction.normalize import whitespace_normalize  # noqa: E402

ORG_ID = "1d31c315-5087-47df-a8d4-ebfd08efad5d"  # DraftCheck WA (same as wp6_extract)
SKILL_VERSION = "wp4b-legal-graph-v1"


# ---------------------------------------------------------------------------
# LLM plumbing — same pattern as scripts/wp6_extract.py (env-keyed, urllib)
# ---------------------------------------------------------------------------


@dataclass
class LlmEndpoint:
    name: str
    model: str
    base_url: str
    api_key: str

    def complete(self, system: str, user: str, max_tokens: int = 4000) -> str:
        body = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0,
            "max_tokens": max_tokens,
        }
        req = urllib.request.Request(
            f"{self.base_url.rstrip('/')}/chat/completions",
            data=json.dumps(body).encode("utf-8"),
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        last_err: Exception | None = None
        for delay in (0.0, 2.0, 5.0):
            if delay:
                time.sleep(delay)
            try:
                with urllib.request.urlopen(req, timeout=300) as resp:
                    payload = json.loads(resp.read().decode("utf-8"))
                content = payload["choices"][0]["message"]["content"]
                if isinstance(content, list):
                    content = "".join(p.get("text", "") for p in content if isinstance(p, dict))
                return content or ""
            except (urllib.error.URLError, OSError, KeyError, json.JSONDecodeError) as exc:
                last_err = exc
        raise RuntimeError(f"{self.name} call failed after retries: {last_err}")


def build_blind_pair(escalations: list[str]) -> list[LlmEndpoint]:
    """Two endpoints from different model families for the blind 2-model pass.

    Missing keys never crash the run: log an escalation and return what we
    have (possibly an empty list — the deterministic parts still run).
    """
    endpoints: list[LlmEndpoint] = []
    minimax_key = os.environ.get("MINIMAX_API_KEY", "")
    minimax_base = os.environ.get("MINIMAX_BASE_URL", "https://api.minimaxi.chat/v1")
    openrouter_key = os.environ.get("OPENROUTER_API_KEY", "")
    openrouter_base = os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    openai_key = os.environ.get("OPENAI_API_KEY", "")

    if minimax_key:
        endpoints.append(
            LlmEndpoint("minimax", os.environ.get("MINIMAX_MODEL", "MiniMax-M2"),
                        minimax_base, minimax_key)
        )
    else:
        escalations.append(
            "MINIMAX_API_KEY missing — MiniMax leg of the blind 2-model pass skipped. "
            "Unblock: add MINIMAX_API_KEY to infra/v3 env."
        )

    if openrouter_key:
        endpoints.append(LlmEndpoint("openrouter", "openai/gpt-4o", openrouter_base, openrouter_key))
    elif openai_key:
        endpoints.append(LlmEndpoint("openai", "gpt-4o", "https://api.openai.com/v1", openai_key))
        escalations.append(
            "OPENROUTER_API_KEY missing; used direct OpenAI gpt-4o as the second model "
            "family. Unblock: add OPENROUTER_API_KEY to infra/v3 env."
        )
    else:
        escalations.append(
            "Neither OPENROUTER_API_KEY nor OPENAI_API_KEY present — second model family "
            "unavailable; proposals (if any) cannot reach 2/2 agreement and stay "
            "pending_review. Unblock: add OPENROUTER_API_KEY or OPENAI_API_KEY."
        )

    if not endpoints:
        escalations.append(
            "No LLM keys at all — LLM proposal passes skipped cleanly; deterministic "
            "sweeps and reporting still ran."
        )
    return endpoints


def parse_llm_json(raw: str) -> dict | None:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.DOTALL)
    try:
        out = json.loads(raw)
        return out if isinstance(out, dict) else None
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        if m:
            try:
                out = json.loads(m.group(0))
                return out if isinstance(out, dict) else None
            except json.JSONDecodeError:
                return None
    return None


def dsn_from_env() -> str:
    return os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://").replace(
        "postgresql+psycopg://", "postgresql://"
    )


# ---------------------------------------------------------------------------
# Shared DB helpers
# ---------------------------------------------------------------------------


def open_review_item(conn: psycopg.Connection, subject_type: str, subject_id: str | None,
                     reason: str, meta: dict) -> None:
    conn.execute(
        """
        INSERT INTO review_items (id, org_id, subject_type, subject_id, reason, status,
            priority, source_json, metadata_json, severity, created_at, updated_at)
        VALUES (gen_random_uuid(), %s, %s, %s, %s, 'open', 1, '{}', %s, 'medium', now(), now())
        """,
        (ORG_ID, subject_type, subject_id, reason, Json({"wp4b": True, **meta})),
    )


def insert_edge(
    conn: psycopg.Connection,
    from_type: str,
    from_ref: str,
    to_type: str,
    to_ref: str,
    relation: str,
    quote: str | None,
    confidence: float,
    review_status: str,
    meta: dict,
) -> bool:
    """Insert a legal_edges row; returns True when newly inserted."""
    row = conn.execute(
        """
        INSERT INTO legal_edges (id, from_type, from_ref, to_type, to_ref, relation,
            evidence_quote, confidence, review_status, metadata_json, created_at, updated_at)
        VALUES (gen_random_uuid(), %s, %s, %s, %s, %s, %s, %s, %s, %s, now(), now())
        ON CONFLICT (from_type, from_ref, to_type, to_ref, relation) DO NOTHING
        RETURNING id
        """,
        (from_type, from_ref, to_type, to_ref, relation, quote, confidence,
         review_status, Json({"wp4b": True, **meta})),
    ).fetchone()
    return row is not None


def exception_phrase_in(text: str) -> str | None:
    low = whitespace_normalize(text).lower()
    for phrase in EXCEPTION_PHRASES:
        if phrase in low:
            return phrase
    return None


# ---------------------------------------------------------------------------
# Subcommand: exceptions (Phase 4b item 1 — exceptions are atoms)
# ---------------------------------------------------------------------------

EXC_SYSTEM_PROMPT = (
    "You are a meticulous regulatory analyst for Western Australian planning "
    "instruments. You structure exception/carve-out clauses into machine-readable "
    "conditions. Rules: (1) Output ONLY a single JSON object, no prose, no markdown "
    "fences. (2) The quote MUST be an exact verbatim substring of the supplied clause "
    "text (character-for-character, including odd spacing or OCR artefacts) and must "
    "contain the exception language. (3) NEVER invent conditions not present in the "
    "text. (4) If the exception cannot be faithfully structured, return "
    '{"structurable": false, "reason": "<short reason>"}.'
)

EXC_SCHEMA = """{
  "structurable": true,
  "quote": "VERBATIM substring of the clause containing the exception language",
  "condition_json": {
    "trigger_phrase": "the exception phrase, e.g. except where / unless / despite",
    "applies_when": "<plain-language condition under which the exception operates>",
    "subject": "<what the exception applies to>",
    "negates": "base_requirement" | "part_of_base_requirement",
    "references": ["<clause/instrument references mentioned, verbatim>"]
  }
}"""


def exc_prompt(clause_path: str, clause_text: str, base_rules: list[dict]) -> str:
    base_desc = "\n".join(
        f"- rule_id={b['id']} rule_key={b['rule_key']} quote={b['quote'][:200]!r}"
        for b in base_rules
    ) or "- (no base rule located on this clause)"
    return (
        f"Clause reference: {clause_path}\n"
        f"--- CLAUSE TEXT START ---\n{clause_text}\n--- CLAUSE TEXT END ---\n\n"
        f"Base rule atoms already extracted from this clause family:\n{base_desc}\n\n"
        "The clause contains exception language. Structure the exception as a "
        "condition_json. Respond with ONLY a JSON object in this schema:\n"
        f"{EXC_SCHEMA}"
    )


def condition_signature(cond: dict) -> str:
    """Stable signature of a structured condition for 2-model agreement."""
    parts = [
        whitespace_normalize(str(cond.get("trigger_phrase", ""))).lower(),
        whitespace_normalize(str(cond.get("applies_when", ""))).lower(),
        whitespace_normalize(str(cond.get("negates", ""))).lower(),
    ]
    return hashlib.sha256("|".join(parts).encode()).hexdigest()


def validate_exception_proposal(payload: dict | None, clause_text: str) -> tuple[bool, str]:
    """Deterministic gate on one model's structuring proposal."""
    if not payload:
        return False, "unparseable JSON"
    if payload.get("structurable") is not True:
        return False, f"model declined: {payload.get('reason', 'unstructurable')}"
    quote = str(payload.get("quote", ""))
    cond = payload.get("condition_json")
    if not isinstance(cond, dict) or not cond.get("applies_when"):
        return False, "condition_json missing or has no applies_when"
    if whitespace_normalize(quote) and \
            whitespace_normalize(quote) in whitespace_normalize(clause_text):
        if exception_phrase_in(quote):
            return True, "ok"
        return False, "quote lacks exception language from the closed phrase list"
    return False, "quote not found verbatim (whitespace-normalised) in clause text"


def find_base_rules(conn: psycopg.Connection, clause_id: str,
                    parent_clause_id: str | None) -> list[dict]:
    """Deterministic base-rule location: same clause, then parent clause."""
    rows = conn.execute(
        "SELECT id, rule_key, quote, lifecycle_status FROM rules "
        "WHERE clause_id = %s AND rule_type <> 'exception'",
        (clause_id,),
    ).fetchall()
    if not rows and parent_clause_id:
        rows = conn.execute(
            "SELECT id, rule_key, quote, lifecycle_status FROM rules "
            "WHERE clause_id = %s AND rule_type <> 'exception'",
            (parent_clause_id,),
        ).fetchall()
    return [
        {"id": str(r[0]), "rule_key": r[1], "quote": r[2] or "", "lifecycle_status": r[3]}
        for r in rows
    ]


def insert_exception_rule(
    conn: psycopg.Connection,
    sv_id: str,
    clause: dict,
    quote: str,
    cond: dict,
    lifecycle: str,
    models: list[str],
    confidence: float,
) -> str | None:
    rule_key = f"exception.{clause['clause_key']}"[:160]
    row = conn.execute(
        """
        INSERT INTO rules (id, org_id, source_version_id, clause_id, rule_key, rule_type,
            pathway, lifecycle_status, operator, value_json, unit, condition_json, quote,
            extractor_model, metadata_json, created_at, updated_at)
        VALUES (gen_random_uuid(), %s, %s, %s, %s, 'exception', 'none', %s, NULL, %s, NULL,
                %s, %s, %s, %s, now(), now())
        ON CONFLICT (source_version_id, rule_key) DO UPDATE
            SET condition_json = EXCLUDED.condition_json, quote = EXCLUDED.quote,
                updated_at = now()
        RETURNING id
        """,
        (
            ORG_ID, sv_id, clause["id"], rule_key, lifecycle,
            Json({}), Json(cond), quote, ",".join(models),
            Json({"wp4b": True, "skill_version": SKILL_VERSION, "confidence": confidence,
                  "adjudication": "blind_2_model"}),
        ),
    ).fetchone()
    return str(row[0]) if row else None


def cmd_exceptions(conn: psycopg.Connection, args: argparse.Namespace,
                   report: dict[str, Any]) -> None:
    escalations: list[str] = report.setdefault("escalations", [])
    endpoints = build_blind_pair(escalations)
    stats = {
        "exception_clauses_found": 0,
        "exceptions_already_structured": 0,
        "exception_rules_created": 0,
        "exception_edges_created": 0,
        "pending_review": 0,
        "no_base_rule": 0,
        "llm_skipped_no_keys": 0,
        "llm_errors": [],
    }

    where = "WHERE c.disposition IN ('rule_bearing', 'manual_review')"
    params: list[Any] = []
    if args.source_version:
        where += " AND c.source_version_id = %s"
        params.append(args.source_version)
    clauses = conn.execute(
        f"SELECT c.id, c.source_version_id, c.parent_clause_id, c.clause_key, "
        f"c.clause_path, c.text FROM clauses c {where} ORDER BY c.clause_key",
        params,
    ).fetchall()

    flagged = []
    for cid, sv, parent, ckey, cpath, text in clauses:
        if exception_phrase_in(text or ""):
            flagged.append({
                "id": str(cid), "sv": str(sv),
                "parent": str(parent) if parent else None,
                "clause_key": ckey, "clause_path": cpath or ckey, "text": text,
            })
    if args.limit:
        flagged = flagged[: args.limit]
    stats["exception_clauses_found"] = len(flagged)

    unresolved_clause_ids: set[str] = set()

    for clause in flagged:
        base_rules = find_base_rules(conn, clause["id"], clause["parent"])

        existing = conn.execute(
            "SELECT id, lifecycle_status, quote FROM rules "
            "WHERE clause_id = %s AND rule_type = 'exception'",
            (clause["id"],),
        ).fetchall()
        if existing:
            exc_id, exc_status, exc_quote = str(existing[0][0]), existing[0][1], existing[0][2]
            # Deterministic: ensure the exception_to edge exists for each base rule.
            for base in base_rules:
                if insert_edge(conn, "rule", exc_id, "rule", base["id"], "exception_to",
                               exc_quote, 0.95,
                               "approved" if exc_status in ("approved", "auto_accepted")
                               else "pending_review",
                               {"clause_key": clause["clause_key"]}):
                    stats["exception_edges_created"] += 1
            stats["exceptions_already_structured"] += 1
            if exc_status not in ("approved", "auto_accepted"):
                unresolved_clause_ids.add(clause["id"])
            conn.commit()
            continue

        if not base_rules:
            stats["no_base_rule"] += 1
            unresolved_clause_ids.add(clause["id"])
            open_review_item(
                conn, "exception_clause", clause["id"],
                f"WP4b: exception language in clause {clause['clause_path']} but no base "
                "rule atom on the clause or its parent — extraction gap or carve-out "
                "without a quantitative base.",
                {"clause_key": clause["clause_key"]},
            )
            conn.commit()
            continue

        if not endpoints:
            stats["llm_skipped_no_keys"] += 1
            unresolved_clause_ids.add(clause["id"])
            continue

        # Blind 2-model structuring pass; deterministic quote validation per leg.
        prompt = exc_prompt(clause["clause_path"], clause["text"], base_rules)
        legs: list[tuple[str, dict]] = []  # (model_name, payload)
        for ep in endpoints:
            try:
                raw = ep.complete(EXC_SYSTEM_PROMPT, prompt)
            except RuntimeError as exc:
                stats["llm_errors"].append(f"{clause['clause_path']} {ep.name}: {exc}")
                continue
            payload = parse_llm_json(raw)
            ok, detail = validate_exception_proposal(payload, clause["text"])
            if ok:
                legs.append((f"{ep.name}:{ep.model}", payload))  # type: ignore[arg-type]
            else:
                stats["llm_errors"].append(
                    f"{clause['clause_path']} {ep.name}: proposal rejected — {detail}"
                )

        agreed = (
            len(legs) == 2
            and len(endpoints) == 2
            and condition_signature(legs[0][1]["condition_json"])
            == condition_signature(legs[1][1]["condition_json"])
        )
        if legs:
            model_names = [m for m, _ in legs]
            payload = legs[0][1]
            lifecycle = "approved" if agreed else "pending_review"
            confidence = 0.9 if agreed else 0.5
            exc_id = insert_exception_rule(
                conn, clause["sv"], clause, str(payload["quote"]),
                dict(payload["condition_json"]), lifecycle, model_names, confidence,
            )
            if exc_id:
                stats["exception_rules_created"] += 1
                for base in base_rules:
                    if insert_edge(conn, "rule", exc_id, "rule", base["id"], "exception_to",
                                   str(payload["quote"]), confidence,
                                   "approved" if agreed else "pending_review",
                                   {"clause_key": clause["clause_key"]}):
                        stats["exception_edges_created"] += 1
            if not agreed:
                stats["pending_review"] += 1
                unresolved_clause_ids.add(clause["id"])
                open_review_item(
                    conn, "exception_clause", clause["id"],
                    f"WP4b: exception in clause {clause['clause_path']} structured by only "
                    "one model leg or without 2/2 agreement — pending_review.",
                    {"clause_key": clause["clause_key"], "models": model_names},
                )
        else:
            stats["pending_review"] += 1
            unresolved_clause_ids.add(clause["id"])
            open_review_item(
                conn, "exception_clause", clause["id"],
                f"WP4b: exception in clause {clause['clause_path']} could not be "
                "structured with a verbatim quote anchor — unstructurable.",
                {"clause_key": clause["clause_key"]},
            )
        conn.commit()

    # Base rules blocked from approval: approved base rules on clauses whose
    # exception is unresolved (Phase 4b item 1 — base cannot stay approved).
    blocked: list[dict] = []
    for clause_id in sorted(unresolved_clause_ids):
        rows = conn.execute(
            "SELECT r.id, r.rule_key FROM rules r "
            "WHERE r.rule_type <> 'exception' AND r.lifecycle_status = 'approved' AND "
            "(r.clause_id = %s OR r.clause_id = (SELECT parent_clause_id FROM clauses "
            " WHERE id = %s))",
            (clause_id, clause_id),
        ).fetchall()
        for rid, rkey in rows:
            blocked.append({"rule_id": str(rid), "rule_key": rkey, "clause_id": clause_id})
    if blocked and args.enforce:
        conn.execute(
            "UPDATE rules SET lifecycle_status = 'pending_review', updated_at = now() "
            "WHERE id = ANY(%s::uuid[])",
            ([b["rule_id"] for b in blocked],),
        )
        conn.commit()
    stats["blocked_base_rules"] = len(blocked)
    report["exceptions"] = stats
    report["blocked_approvals"] = blocked
    report["enforced_demotions"] = len(blocked) if args.enforce else 0


# ---------------------------------------------------------------------------
# Subcommand: edges (Phase 4b item 2 — blind 2-model long-context proposals)
# ---------------------------------------------------------------------------

EDGE_SYSTEM_PROMPT = (
    "You are a meticulous legal-graph analyst for Western Australian planning "
    "instruments. Given two instrument texts, you propose cross-instrument edges. "
    "Rules: (1) Output ONLY a single JSON object, no prose, no markdown fences. "
    "(2) relation must be one of: %s. (3) Every edge MUST carry a quote that is an "
    "exact verbatim substring of the FROM document (character-for-character) and the "
    "quote must itself contain the modification/exception language that evidences the "
    "relationship. (4) Propose nothing without such a quote. (5) direction 'a_to_b' "
    "means the edge goes FROM document A TO document B (quote from A); 'b_to_a' the "
    "reverse (quote from B)."
) % ", ".join(EDGE_RELATIONS)

EDGE_SCHEMA = """{
  "edges": [
    {
      "direction": "a_to_b" | "b_to_a",
      "relation": "one of the allowed relations",
      "from_clause": "<clause reference in the FROM document, e.g. 5.2.1, or empty>",
      "to_clause": "<clause reference in the TO document, or empty>",
      "quote": "VERBATIM substring of the FROM document evidencing the relationship"
    }
  ]
}"""


def edge_prompt(title_a: str, text_a: str, title_b: str, text_b: str) -> str:
    return (
        f"--- DOCUMENT A: {title_a} ---\n{text_a}\n--- END DOCUMENT A ---\n\n"
        f"--- DOCUMENT B: {title_b} ---\n{text_b}\n--- END DOCUMENT B ---\n\n"
        "Propose every cross-instrument edge between these documents (modifies, "
        "overrides, exception_to, applies_with, performance_alternative_to, "
        "depends_on). Respond with ONLY a JSON object in this schema:\n"
        f"{EDGE_SCHEMA}"
    )


def doc_text(conn: psycopg.Connection, sv_id: str, max_chars: int) -> str:
    row = conn.execute(
        "SELECT string_agg(text, E'\\n' ORDER BY chunk_index) FROM source_chunks "
        "WHERE source_version_id = %s",
        (sv_id,),
    ).fetchone()
    return (row[0] or "")[:max_chars]


def doc_title(conn: psycopg.Connection, sv_id: str) -> str:
    row = conn.execute(
        "SELECT sd.title FROM source_versions sv JOIN source_documents sd "
        "ON sd.id = sv.source_id WHERE sv.id = %s",
        (sv_id,),
    ).fetchone()
    return row[0] if row else sv_id


def sv_for_ref(conn: psycopg.Connection, ref_type: str, ref: str) -> str | None:
    """Resolve a legal_edges ref to a source_version id (None if external)."""
    if ref_type == "source_version":
        return ref
    if ref_type == "clause":
        row = conn.execute(
            "SELECT source_version_id FROM clauses WHERE id::text = %s OR clause_key = %s "
            "LIMIT 1",
            (ref, ref),
        ).fetchone()
        return str(row[0]) if row else None
    if ref_type == "rule":
        row = conn.execute(
            "SELECT source_version_id FROM rules WHERE id::text = %s LIMIT 1", (ref,)
        ).fetchone()
        return str(row[0]) if row else None
    return None


def cited_pairs(conn: psycopg.Connection) -> list[tuple[str, str]]:
    """Instrument pairs (source_version ids) linked by existing 'cites' edges."""
    rows = conn.execute(
        "SELECT from_type, from_ref, to_type, to_ref FROM legal_edges WHERE relation = 'cites'"
    ).fetchall()
    pairs: set[tuple[str, str]] = set()
    for ft, fr, tt, tr in rows:
        sa = sv_for_ref(conn, ft, fr)
        sb = sv_for_ref(conn, tt, tr)
        if sa and sb and sa != sb:
            pairs.add(tuple(sorted((sa, sb))))  # type: ignore[arg-type]
    return sorted(pairs)


def resolve_clause_ref(conn: psycopg.Connection, sv_id: str, ref: str) -> str | None:
    if not ref:
        return None
    row = conn.execute(
        "SELECT id FROM clauses WHERE source_version_id = %s "
        "AND (clause_path = %s OR clause_key = %s) LIMIT 1",
        (sv_id, ref, ref),
    ).fetchone()
    return str(row[0]) if row else None


def parse_edge_proposals(payload: dict | None) -> list[dict]:
    if not payload or not isinstance(payload.get("edges"), list):
        return []
    out = []
    for e in payload["edges"]:
        if not isinstance(e, dict):
            continue
        relation = str(e.get("relation", "")).strip()
        direction = str(e.get("direction", "")).strip()
        if relation not in EDGE_RELATIONS or direction not in ("a_to_b", "b_to_a"):
            continue
        out.append({
            "direction": direction,
            "relation": relation,
            "from_clause": whitespace_normalize(str(e.get("from_clause", "") or "")),
            "to_clause": whitespace_normalize(str(e.get("to_clause", "") or "")),
            "quote": str(e.get("quote", "") or ""),
        })
    return out


def proposal_key(p: dict) -> tuple:
    return (p["direction"], p["relation"], p["from_clause"].lower(), p["to_clause"].lower())


def audit_existing_edges(conn: psycopg.Connection, enforce: bool) -> dict:
    """Deterministic sweep: every non-cites graph edge must carry a valid quote."""
    rows = conn.execute(
        "SELECT id, from_type, from_ref, relation, evidence_quote, review_status "
        "FROM legal_edges WHERE relation = ANY(%s)",
        (list(EDGE_RELATIONS),),
    ).fetchall()
    violations = []
    for eid, ft, fr, relation, quote, status in rows:
        detail = None
        if not quote or not quote.strip():
            detail = "edge has no evidence_quote"
        else:
            sv = sv_for_ref(conn, ft, fr)
            if sv:
                source_text = doc_text(conn, sv, 2_000_000)
                v = validate_edge_quote(quote, source_text)
                if not v.ok:
                    detail = v.detail
        if detail:
            violations.append({"edge_id": str(eid), "relation": relation,
                               "review_status": status, "detail": detail})
    if violations and enforce:
        conn.execute(
            "UPDATE legal_edges SET review_status = 'rejected', updated_at = now() "
            "WHERE id = ANY(%s::uuid[])",
            ([v["edge_id"] for v in violations],),
        )
        conn.commit()
    return {"existing_edges_checked": len(rows), "quoteless_existing_edges": violations}


def cmd_edges(conn: psycopg.Connection, args: argparse.Namespace, report: dict[str, Any]) -> None:
    escalations: list[str] = report.setdefault("escalations", [])
    endpoints = build_blind_pair(escalations)
    stats = {
        "pairs_considered": 0,
        "edges_proposed": 0,
        "edges_inserted_approved": 0,
        "edges_inserted_pending": 0,
        "edges_already_present": 0,
        "quoteless_rejections": 0,
        "llm_errors": [],
    }

    # Deterministic part runs regardless of LLM availability.
    report["edge_quote_audit"] = audit_existing_edges(conn, args.enforce)

    if args.pair:
        a, b = args.pair.split(":", 1)
        pairs = [tuple(sorted((a.strip(), b.strip())))]
    else:
        pairs = cited_pairs(conn)
    if args.limit:
        pairs = pairs[: args.limit]
    stats["pairs_considered"] = len(pairs)

    if not endpoints:
        report["edges"] = stats
        return

    for sv_a, sv_b in pairs:
        text_a = doc_text(conn, sv_a, args.max_chars)
        text_b = doc_text(conn, sv_b, args.max_chars)
        if not text_a or not text_b:
            continue
        title_a, title_b = doc_title(conn, sv_a), doc_title(conn, sv_b)
        prompt = edge_prompt(title_a, text_a, title_b, text_b)

        proposals_by_model: list[list[dict]] = []
        for ep in endpoints:
            try:
                raw = ep.complete(EDGE_SYSTEM_PROMPT, prompt, max_tokens=6000)
            except RuntimeError as exc:
                stats["llm_errors"].append(f"{title_a}<->{title_b} {ep.name}: {exc}")
                proposals_by_model.append([])
                continue
            proposals_by_model.append(parse_edge_proposals(parse_llm_json(raw)))

        keys_by_model = [{proposal_key(p) for p in plist} for plist in proposals_by_model]
        seen: dict[tuple, dict] = {}
        for plist in proposals_by_model:
            for p in plist:
                seen.setdefault(proposal_key(p), p)

        for key, p in sorted(seen.items()):
            stats["edges_proposed"] += 1
            if p["direction"] == "a_to_b":
                from_sv, to_sv, from_text = sv_a, sv_b, text_a
            else:
                from_sv, to_sv, from_text = sv_b, sv_a, text_b
            # Deterministic validator: verbatim quote from the FROM document
            # containing closed-list modification language. No quote, no edge.
            v = validate_edge_quote(p["quote"], from_text)
            if not v.ok:
                stats["quoteless_rejections"] += 1
                continue
            votes = sum(1 for ks in keys_by_model if key in ks)
            status = "approved" if (votes >= 2 and len(endpoints) == 2) else "pending_review"
            confidence = 0.9 if status == "approved" else 0.5

            from_clause = resolve_clause_ref(conn, from_sv, p["from_clause"])
            to_clause = resolve_clause_ref(conn, to_sv, p["to_clause"])
            from_type, from_ref = ("clause", from_clause) if from_clause else \
                ("source_version", from_sv)
            to_type, to_ref = ("clause", to_clause) if to_clause else \
                ("source_version", to_sv)
            meta = {
                "pair": [sv_a, sv_b],
                "direction": p["direction"],
                "votes": votes,
                "proposed_from_clause": p["from_clause"],
                "proposed_to_clause": p["to_clause"],
                "validator": v.detail,
            }
            if insert_edge(conn, from_type, from_ref, to_type, to_ref, p["relation"],
                           p["quote"], confidence, status, meta):
                if status == "approved":
                    stats["edges_inserted_approved"] += 1
                else:
                    stats["edges_inserted_pending"] += 1
            else:
                stats["edges_already_present"] += 1
        conn.commit()

    report["edges"] = stats


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="command", required=True)

    p_exc = sub.add_parser("exceptions", help="structure exception clauses into rule atoms")
    p_exc.add_argument("--source-version", default="", help="limit to one source_version uuid")
    p_exc.add_argument("--limit", type=int, default=0, help="cap exception clauses processed")
    p_exc.add_argument("--enforce", action="store_true",
                       help="demote approved base rules with unresolved exceptions")
    p_exc.add_argument("--report", default="reports/legal_graph.json")

    p_edges = sub.add_parser("edges", help="blind 2-model cross-instrument edge proposals")
    p_edges.add_argument("--pair", default="", help="<sv_uuid>:<sv_uuid> override")
    p_edges.add_argument("--limit", type=int, default=0, help="cap instrument pairs processed")
    p_edges.add_argument("--max-chars", type=int, default=150_000,
                         help="per-document context cap")
    p_edges.add_argument("--enforce", action="store_true",
                         help="reject existing graph edges that fail the quote validator")
    p_edges.add_argument("--report", default="reports/legal_graph.json")

    args = ap.parse_args()
    report: dict[str, Any] = {
        "skill_version": SKILL_VERSION,
        "command": args.command,
        "escalations": [],
    }

    with psycopg.connect(dsn_from_env()) as conn:
        if args.command == "exceptions":
            cmd_exceptions(conn, args, report)
        else:
            cmd_edges(conn, args, report)

    out = json.dumps(report, indent=2, default=str)
    if args.report:
        os.makedirs(os.path.dirname(args.report) or ".", exist_ok=True)
        with open(args.report, "w", encoding="utf-8") as fh:
            fh.write(out)
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
