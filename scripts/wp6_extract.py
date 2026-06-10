"""WP6 — rule-extraction harness (structure pass + 3-pass blind ensemble).

Runs INSIDE the api container (psycopg3 + LLM env present):

    docker exec draftcheck-wa-v3-api-1 python /app/scripts/wp6_extract.py \
        --source-version <uuid> [--structure-only] [--limit N] \
        --report /app/reports/wp6_bootstrap.json

Pipeline (docs/CORPUS_COMPLETENESS_PLAN.md Phase 4 / DB_BUILDOUT_AGENT_PLAN WP6):
  1. Structure pass: split source_chunks into clauses rows (idempotent on
     (source_version_id, clause_key)).
  2. For each Tier-1-relevant rule-bearing clause: 3 blind extraction passes,
     temperature 0, strict JSON, mandatory verbatim quote anchor per atom.
     Pass 1+2 = MiniMax, pass 3 = OpenAI (different model family) when
     OPENAI_API_KEY is set, else MiniMax for all three (escalation logged).
  3. Deterministic validators (draftcheck.extraction.validators) plus range
     priors, R-code sanity (R5..R80 + RAC/R-AC excluded), mandatory pathway.
  4. Adjudication: 3/3 -> rules (lifecycle approved, confidence 0.95);
     2/3 -> one challenge round; else rule_candidates + review_items.
  5. Per-doc acceptance audit JSON (orphan numbers, exception language,
     pending_review counts).

Never guesses numbers: an atom whose quote anchor does not appear verbatim
(whitespace-normalised) in the clause text is rejected by validators.
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
import uuid
from dataclasses import dataclass, field
from typing import Any

sys.path.insert(0, "/app/src")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

import psycopg  # noqa: E402
from psycopg.types.json import Json  # noqa: E402

from draftcheck.extraction.normalize import normalize_unit, whitespace_normalize  # noqa: E402
from draftcheck.extraction.validators import run_all_validators  # noqa: E402
from draftcheck.extraction.vocabulary import OPERATORS, RULE_KEYS  # noqa: E402

ORG_ID = "1d31c315-5087-47df-a8d4-ebfd08efad5d"  # DraftCheck WA
SKILL_VERSION_ID = "wp6-extractor-v1"
PATHWAYS = {"deemed_to_comply", "design_principle", "none"}
VALID_R_CODES = {f"R{n}" for n in (5, 10, 12.5, 15, 17.5, 20, 25, 30, 35, 40, 50, 60, 80)}
VALID_R_CODES = {c.replace(".0", "") for c in VALID_R_CODES} | {"R12.5", "R17.5", "R100", "R160", "R-AC", "R100-SL"}

# Numeric sanity priors per rule_key: (min, max, allowed units)
RANGE_PRIORS: dict[str, tuple[float, float, set[str | None]]] = {
    "primary_street_setback": (0.0, 20.0, {"m"}),
    "secondary_street_setback": (0.0, 20.0, {"m"}),
    "side_setback": (0.0, 20.0, {"m"}),
    "rear_setback": (0.0, 20.0, {"m"}),
    "site_cover": (10.0, 100.0, {"%"}),
    "open_space": (10.0, 100.0, {"%"}),
    "site_area": (50.0, 10000.0, {"m2"}),
    "outdoor_living_area": (4.0, 200.0, {"m2", "m"}),
    "boundary_wall_length": (1.0, 50.0, {"m"}),
    "building_height": (2.0, 30.0, {"m"}),
    "building_storeys": (1.0, 10.0, {"storeys", None}),
    "garage_width": (1.0, 20.0, {"m"}),
    "garage_dominance": (10.0, 100.0, {"%"}),
    "soft_landscaping": (0.0, 100.0, {"%"}),
}

TIER1_TOPIC_RE = re.compile(
    r"setback|site\s*cover|open\s*space|site\s*area|boundary\s*wall|garage|carport|"
    r"building\s*height|wall\s*height|roof\s*height|storeys|outdoor\s*living|street\s*setback",
    re.IGNORECASE,
)

RULE_BEARING_WORDS = (
    "must", "shall", "not exceed", "at least", "minimum", "maximum",
    "required", "permitted", "no more than", "no less than", "deemed-to-comply",
)
EXCEPTION_WORDS = ("notwithstanding", "despite", "except where", "unless", "other than where")

CLAUSE_MARKER_RE = re.compile(r"(?m)^\s*((?:C|P)\d+(?:\.\d+)+|\d+\.\d+(?:\.\d+)?)\s+")

JSON_SCHEMA_TEXT = """{
  "atoms": [
    {
      "rule_key": "one of: %s",
      "rule_type": "one of: standard, exception, deemed_to_comply, design_principle",
      "pathway": "one of: deemed_to_comply, design_principle, none",
      "operator": "one of: %s",
      "value": <number>,
      "unit": "m" | "m2" | "%%" | "storeys" | null,
      "applicability": {"density_codes": ["R30", ...] or [] if not density-specific,
                         "dwelling_type": "single_house|grouped_dwelling|multiple_dwelling|any",
                         "condition": "<short free text condition, or empty string>"},
      "quote": "VERBATIM substring of the clause text containing the number(s)"
    }
  ],
  "no_rules": false
}""" % (", ".join(sorted(RULE_KEYS)), ", ".join(sorted(OPERATORS)))

SYSTEM_PROMPT = (
    "You are a meticulous regulatory data extractor for the Western Australian "
    "Residential Design Codes. You extract quantitative rule atoms from clause text. "
    "Rules: (1) Output ONLY a single JSON object matching the schema, no prose, no markdown fences. "
    "(2) Every atom MUST include a quote that is an exact verbatim substring of the supplied clause "
    "text (copy it character-for-character, including any odd spacing or OCR artefacts) and the "
    "quote must contain the extracted number. (3) NEVER guess or infer numbers not present in the "
    "text. If table columns are ambiguous (more values than headers or vice versa), skip that atom. "
    "(4) If the clause contains no extractable quantitative rule, return {\"atoms\": [], \"no_rules\": true}. "
    "(5) pathway is deemed_to_comply for C-clauses / deemed-to-comply requirements, design_principle "
    "for P-clauses, none otherwise."
)


# ---------------------------------------------------------------------------
# LLM plumbing (temperature 0, OpenAI-compatible chat completions)
# ---------------------------------------------------------------------------


@dataclass
class LlmEndpoint:
    name: str
    model: str
    base_url: str
    api_key: str

    def complete(self, system: str, user: str, max_tokens: int = 3000) -> str:
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
                with urllib.request.urlopen(req, timeout=180) as resp:
                    payload = json.loads(resp.read().decode("utf-8"))
                content = payload["choices"][0]["message"]["content"]
                if isinstance(content, list):
                    content = "".join(p.get("text", "") for p in content if isinstance(p, dict))
                return content or ""
            except (urllib.error.URLError, OSError, KeyError, json.JSONDecodeError) as exc:
                last_err = exc
        raise RuntimeError(f"{self.name} call failed after retries: {last_err}")


def build_endpoints() -> tuple[list[LlmEndpoint], list[str]]:
    """Return ([pass1, pass2, pass3] endpoints, escalations)."""
    escalations: list[str] = []
    minimax_key = os.environ.get("MINIMAX_API_KEY", "")
    minimax_base = os.environ.get("MINIMAX_BASE_URL", "https://api.minimaxi.chat/v1")
    openrouter_key = os.environ.get("OPENROUTER_API_KEY", "")
    openrouter_base = os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    openai_key = os.environ.get("OPENAI_API_KEY", "")

    if not minimax_key:
        raise RuntimeError("MINIMAX_API_KEY missing — cannot run ensemble")
    mm = LlmEndpoint("minimax", os.environ.get("MINIMAX_MODEL", "MiniMax-M2"), minimax_base, minimax_key)

    if openrouter_key:
        other = LlmEndpoint("openrouter", "openai/gpt-4o", openrouter_base, openrouter_key)
    elif openai_key:
        other = LlmEndpoint("openai", "gpt-4o", "https://api.openai.com/v1", openai_key)
        escalations.append(
            "OPENROUTER_API_KEY missing on VPS; used direct OpenAI gpt-4o as the second "
            "model family for pass 3. Unblock: add OPENROUTER_API_KEY to infra/v3 env."
        )
    else:
        other = mm
        escalations.append(
            "Neither OPENROUTER_API_KEY nor OPENAI_API_KEY present — all 3 passes ran on "
            "MiniMax (independent calls). 'Different model family' requirement NOT met."
        )
    return [mm, mm, other], escalations


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


# ---------------------------------------------------------------------------
# Structure pass
# ---------------------------------------------------------------------------


def disposition_for(text: str) -> str:
    low = text.lower()
    if any(w in low for w in RULE_BEARING_WORDS):
        return "rule_bearing"
    if re.search(r"\bmeans\b|\bis defined\b", low[:200]):
        return "definition"
    if any(w in low for w in ("application", "lodgement", "procedure", "process")):
        return "procedural"
    return "informational"


def structure_pass(conn: psycopg.Connection, sv_id: str) -> dict[str, int]:
    """Split each source_chunk into clause segments on clause markers; idempotent."""
    created = updated = 0
    rows = conn.execute(
        "SELECT id, chunk_index, text FROM source_chunks "
        "WHERE source_version_id = %s ORDER BY chunk_index",
        (sv_id,),
    ).fetchall()
    for chunk_id, idx, text in rows:
        segments: list[tuple[str, str, str]] = []  # (clause_path, key, body)
        markers = list(CLAUSE_MARKER_RE.finditer(text))
        if not markers:
            segments.append((f"chunk-{idx}", f"chunk_{idx:03d}_full", text))
        else:
            if markers[0].start() > 0:
                segments.append((f"chunk-{idx}", f"chunk_{idx:03d}_intro", text[: markers[0].start()]))
            for j, m in enumerate(markers):
                end = markers[j + 1].start() if j + 1 < len(markers) else len(text)
                path = m.group(1)
                key = f"chunk_{idx:03d}_{re.sub(r'[^A-Za-z0-9]+', '_', path)}"
                segments.append((path, key, text[m.start():end]))
        for path, key, body in segments:
            body = body.strip()
            if len(whitespace_normalize(body)) < 30:
                continue
            disp = disposition_for(body)
            cur = conn.execute(
                """
                INSERT INTO clauses (id, source_version_id, source_chunk_id, clause_key,
                    clause_path, clause_type, disposition, text, parser_name, parser_version,
                    metadata_json, created_at, updated_at)
                VALUES (gen_random_uuid(), %s, %s, %s, %s, 'clause', %s, %s,
                        'wp6_extract', 'v1', %s, now(), now())
                ON CONFLICT (source_version_id, clause_key) DO UPDATE
                    SET text = EXCLUDED.text, disposition = EXCLUDED.disposition,
                        updated_at = now()
                RETURNING (xmax = 0)
                """,
                (sv_id, chunk_id, key, path, disp, body, Json({"chunk_index": idx})),
            )
            if cur.fetchone()[0]:
                created += 1
            else:
                updated += 1
    conn.commit()
    return {"clauses_created": created, "clauses_updated": updated}


# ---------------------------------------------------------------------------
# Extraction + validation + adjudication
# ---------------------------------------------------------------------------


@dataclass
class Atom:
    rule_key: str
    rule_type: str
    pathway: str
    operator: str
    value: float
    unit: str | None
    applicability: dict
    quote: str
    extraction_pass: int
    model: str
    validators: dict = field(default_factory=dict)
    valid: bool = False

    def signature(self) -> tuple:
        codes = tuple(sorted(self.applicability.get("density_codes") or []))
        return (
            self.rule_key,
            self.operator,
            round(self.value, 4),
            self.unit,
            codes,
            self.pathway,
            self.applicability.get("dwelling_type") or "any",
        )


def parse_atoms(payload: dict | None, pass_no: int, model: str) -> list[Atom]:
    if not payload or not isinstance(payload.get("atoms"), list):
        return []
    atoms: list[Atom] = []
    for a in payload["atoms"]:
        if not isinstance(a, dict):
            continue
        try:
            value = float(a["value"])
        except (KeyError, TypeError, ValueError):
            continue
        unit_raw = a.get("unit")
        value, unit = normalize_unit(value, unit_raw if unit_raw else None)
        appl = a.get("applicability") or {}
        if not isinstance(appl, dict):
            appl = {}
        atoms.append(
            Atom(
                rule_key=str(a.get("rule_key", "")),
                rule_type=str(a.get("rule_type", "standard")),
                pathway=str(a.get("pathway", "")),
                operator=str(a.get("operator", "")),
                value=value,
                unit=unit,
                applicability=appl,
                quote=str(a.get("quote", "")),
                extraction_pass=pass_no,
                model=model,
            )
        )
    return atoms


def validate_atom(atom: Atom, clause_text: str) -> None:
    results = run_all_validators(
        quote=atom.quote,
        clause_text=clause_text,
        disposition="rule_bearing",
        value_json={"value": atom.value},
        unit=atom.unit,
        rule_key=atom.rule_key,
    )
    # Extra deterministic checks
    extra: dict[str, dict] = {}
    extra["operator_vocab"] = {
        "pass": atom.operator in OPERATORS,
        "detail": f"operator {atom.operator!r}",
    }
    extra["pathway_mandatory"] = {
        "pass": atom.pathway in PATHWAYS,
        "detail": f"pathway {atom.pathway!r} (must be one of {sorted(PATHWAYS)})",
    }
    prior = RANGE_PRIORS.get(atom.rule_key)
    if prior:
        lo, hi, units = prior
        ok = lo <= atom.value <= hi and atom.unit in units
        extra["range_prior"] = {
            "pass": ok,
            "detail": f"value {atom.value} {atom.unit} vs prior [{lo},{hi}] {sorted(str(u) for u in units)}",
        }
    codes = atom.applicability.get("density_codes") or []
    bad = [c for c in codes if str(c).upper().replace(" ", "") not in VALID_R_CODES]
    extra["r_code_sanity"] = {
        "pass": not bad,
        "detail": f"invalid density codes: {bad}" if bad else "density codes ok",
    }
    results.update(extra)
    atom.validators = results
    atom.valid = all(v["pass"] for v in results.values())


def prompt_for_clause(clause_path: str, clause_text: str) -> str:
    return (
        f"Clause reference: {clause_path}\n"
        f"--- CLAUSE TEXT START ---\n{clause_text}\n--- CLAUSE TEXT END ---\n\n"
        f"Extract every quantitative rule atom from the clause text above.\n"
        f"Respond with ONLY a JSON object in this schema:\n{JSON_SCHEMA_TEXT}"
    )


def challenge_prompt(clause_path: str, clause_text: str, variants: list[tuple]) -> str:
    lines = []
    for sig in variants:
        lines.append(
            f"- rule_key={sig[0]} operator={sig[1]} value={sig[2]} unit={sig[3]} "
            f"density_codes={list(sig[4])} pathway={sig[5]} dwelling_type={sig[6]}"
        )
    return (
        "Independent extractions of the same clause disagree:\n" + "\n".join(lines) +
        "\n\nRe-read the clause carefully and produce your own corrected extraction. "
        "Do not assume any variant above is right; only the clause text decides.\n\n"
        + prompt_for_clause(clause_path, clause_text)
    )


def insert_candidate(
    conn: psycopg.Connection,
    sv_id: str,
    clause_id: str,
    chunk_id: str | None,
    atom: Atom,
    group_id: str,
    review_status: str,
    confidence: float | None,
    prompt_text: str,
) -> str:
    cid = str(uuid.uuid4())
    conn.execute(
        """
        INSERT INTO rule_candidates (id, org_id, source_version_id, clause_id, source_chunk_id,
            rule_key, rule_type, pathway, operator, value_json, unit, condition_json, quote,
            extractor_model, skill_version_id, prompt_hash, confidence, review_status,
            metadata_json, extraction_group_id, extraction_pass, validator_results_json,
            created_at, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NULL, %s, %s, %s,
                %s, %s, %s, %s, now(), now())
        """,
        (
            cid, ORG_ID, sv_id, clause_id, chunk_id,
            atom.rule_key, atom.rule_type, atom.pathway, atom.operator,
            Json({"value": atom.value}), atom.unit, Json(atom.applicability), atom.quote,
            atom.model, hashlib.sha256(prompt_text.encode()).hexdigest(),
            confidence, review_status,
            Json({"wp6": True}), group_id, atom.extraction_pass, Json(atom.validators),
        ),
    )
    return cid


def promote_rule(
    conn: psycopg.Connection,
    sv_id: str,
    clause_id: str,
    candidate_id: str,
    atom: Atom,
    confidence: float,
) -> str | None:
    codes = sorted(atom.applicability.get("density_codes") or [])
    suffix = "_".join(c.replace("-", "").replace(".", "p") for c in codes) or "all"
    dw = atom.applicability.get("dwelling_type") or "any"
    rule_key = f"{atom.rule_key}.{suffix}" + ("" if dw == "any" else f".{dw}")
    row = conn.execute(
        """
        INSERT INTO rules (id, org_id, source_version_id, clause_id, candidate_id, rule_key,
            rule_type, pathway, lifecycle_status, operator, value_json, unit, condition_json,
            quote, extractor_model, metadata_json, applicable_r_codes, created_at, updated_at)
        VALUES (gen_random_uuid(), %s, %s, %s, %s, %s, %s, %s, 'approved', %s, %s, %s, %s, %s,
                %s, %s, %s, now(), now())
        ON CONFLICT (source_version_id, rule_key) DO UPDATE
            SET value_json = EXCLUDED.value_json, operator = EXCLUDED.operator,
                unit = EXCLUDED.unit, quote = EXCLUDED.quote, updated_at = now()
        RETURNING id
        """,
        (
            ORG_ID, sv_id, clause_id, candidate_id, rule_key, atom.rule_type, atom.pathway,
            atom.operator, Json({"value": atom.value, "applicability": atom.applicability,
                                 "confidence": confidence, "base_rule_key": atom.rule_key}),
            atom.unit, Json(atom.applicability), atom.quote, atom.model,
            Json({"wp6": True, "adjudication": "ensemble", "confidence": confidence}),
            Json(codes) if codes else None,
        ),
    ).fetchone()
    rule_id = str(row[0]) if row else None
    if rule_id:
        conn.execute(
            """
            INSERT INTO rule_clause_links (id, rule_id, clause_id, source_version_id, link_type,
                quote, confidence, metadata_json, created_at, updated_at)
            VALUES (gen_random_uuid(), %s, %s, %s, 'primary', %s, %s, '{}', now(), now())
            ON CONFLICT (rule_id, clause_id, link_type) DO NOTHING
            """,
            (rule_id, clause_id, sv_id, atom.quote, confidence),
        )
    return rule_id


def open_review_item(conn: psycopg.Connection, clause_id: str, reason: str) -> None:
    conn.execute(
        """
        INSERT INTO review_items (id, org_id, subject_type, subject_id, reason, status,
            priority, source_json, metadata_json, severity, created_at, updated_at)
        VALUES (gen_random_uuid(), %s, 'clause_extraction', %s, %s, 'open', 1, '{}',
                %s, 'medium', now(), now())
        """,
        (ORG_ID, clause_id, reason, Json({"wp6": True})),
    )


def extract_for_clause(
    conn: psycopg.Connection,
    endpoints: list[LlmEndpoint],
    sv_id: str,
    clause_id: str,
    chunk_id: str | None,
    clause_path: str,
    clause_text: str,
    stats: dict,
) -> None:
    group_id = str(uuid.uuid4())
    prompt = prompt_for_clause(clause_path, clause_text)
    pass_atoms: list[list[Atom]] = []
    for i, ep in enumerate(endpoints, start=1):
        try:
            raw = ep.complete(SYSTEM_PROMPT, prompt)
        except RuntimeError as exc:
            stats["llm_errors"].append(f"{clause_path} pass{i}: {exc}")
            pass_atoms.append([])
            continue
        atoms = parse_atoms(parse_llm_json(raw), i, f"{ep.name}:{ep.model}")
        for atom in atoms:
            validate_atom(atom, clause_text)
            if not atom.valid:
                stats["validator_rejects"] += 1
            insert_candidate(
                conn, sv_id, clause_id, chunk_id, atom, group_id,
                "validator_failed" if not atom.valid else "validators_passed",
                None, prompt,
            )
        pass_atoms.append([a for a in atoms if a.valid])
    conn.commit()

    # Adjudication per signature
    sig_by_pass: list[set] = [{a.signature() for a in p} for p in pass_atoms]
    all_sigs = set().union(*sig_by_pass) if sig_by_pass else set()
    atom_by_sig: dict[tuple, Atom] = {}
    for p in pass_atoms:
        for a in p:
            atom_by_sig.setdefault(a.signature(), a)

    pending_signatures: list[tuple] = []
    for sig in sorted(all_sigs):
        votes = sum(1 for s in sig_by_pass if sig in s)
        atom = atom_by_sig[sig]
        if votes == 3:
            cid = insert_candidate(conn, sv_id, clause_id, chunk_id, atom, group_id,
                                   "auto_promoted", 0.95, prompt)
            promote_rule(conn, sv_id, clause_id, cid, atom, 0.95)
            stats["atoms_auto_accepted"] += 1
        elif votes == 2:
            # one challenge round against the dissenting pass's endpoint
            dissent_idx = next(i for i, s in enumerate(sig_by_pass) if sig not in s)
            ep = endpoints[dissent_idx]
            disagreeing = [s for s in all_sigs if s[0] == sig[0]]
            ch_prompt = challenge_prompt(clause_path, clause_text, disagreeing)
            agreed = False
            try:
                raw = ep.complete(SYSTEM_PROMPT, ch_prompt)
                re_atoms = parse_atoms(parse_llm_json(raw), dissent_idx + 1, f"{ep.name}:{ep.model}:challenge")
                for a in re_atoms:
                    validate_atom(a, clause_text)
                agreed = any(a.valid and a.signature() == sig for a in re_atoms)
            except RuntimeError as exc:
                stats["llm_errors"].append(f"{clause_path} challenge: {exc}")
            if agreed:
                cid = insert_candidate(conn, sv_id, clause_id, chunk_id, atom, group_id,
                                       "auto_promoted", 0.9, prompt)
                promote_rule(conn, sv_id, clause_id, cid, atom, 0.9)
                stats["atoms_challenge_accepted"] += 1
            else:
                insert_candidate(conn, sv_id, clause_id, chunk_id, atom, group_id,
                                 "pending_review", 0.6, prompt)
                pending_signatures.append(sig)
                stats["atoms_pending_review"] += 1
        else:
            insert_candidate(conn, sv_id, clause_id, chunk_id, atom, group_id,
                             "pending_review", 0.3, prompt)
            pending_signatures.append(sig)
            stats["atoms_pending_review"] += 1

    if pending_signatures:
        open_review_item(
            conn, clause_id,
            f"WP6 ensemble disagreement on clause {clause_path}: "
            f"{len(pending_signatures)} atom(s) without majority/challenge agreement",
        )
    conn.commit()


# ---------------------------------------------------------------------------
# Audit
# ---------------------------------------------------------------------------


def audit(conn: psycopg.Connection, sv_id: str) -> dict:
    total, dispositioned = conn.execute(
        "SELECT count(*), count(*) FILTER (WHERE disposition <> 'manual_review') "
        "FROM clauses WHERE source_version_id = %s",
        (sv_id,),
    ).fetchone()
    by_status = dict(conn.execute(
        "SELECT review_status, count(*) FROM rule_candidates "
        "WHERE source_version_id = %s GROUP BY review_status",
        (sv_id,),
    ).fetchall())
    rules_count = conn.execute(
        "SELECT count(*) FROM rules WHERE source_version_id = %s AND metadata_json->>'wp6' = 'true'",
        (sv_id,),
    ).fetchone()[0]
    review_open = conn.execute(
        "SELECT count(*) FROM review_items WHERE subject_type='clause_extraction' AND status='open'",
    ).fetchone()[0]

    # Orphan-number sweep over Tier-1 rule-bearing clauses
    clauses = conn.execute(
        "SELECT id, clause_path, text FROM clauses "
        "WHERE source_version_id = %s AND disposition = 'rule_bearing'",
        (sv_id,),
    ).fetchall()
    quotes = [q[0] for q in conn.execute(
        "SELECT quote FROM rule_candidates WHERE source_version_id = %s "
        "AND review_status = 'auto_promoted'",
        (sv_id,),
    ).fetchall()]
    claimed = whitespace_normalize(" ".join(quotes))
    num_re = re.compile(r"\d+(?:\.\d+)?")
    orphan_clauses = []
    total_numbers = claimed_numbers = 0
    for _cid, path, text in clauses:
        if not TIER1_TOPIC_RE.search(text):
            continue
        nums = set(num_re.findall(whitespace_normalize(text)))
        nums = {n for n in nums if float(n) not in (0,) and not re.fullmatch(r"(19|20)\d\d", n)}
        if not nums:
            continue
        total_numbers += len(nums)
        missing = [n for n in nums if n not in claimed]
        claimed_numbers += len(nums) - len(missing)
        if missing:
            orphan_clauses.append({"clause_path": path, "orphan_numbers": sorted(missing)[:20]})

    exception_clauses = [
        path for _cid, path, text in clauses
        if any(w in text.lower() for w in EXCEPTION_WORDS)
    ]

    return {
        "clauses_total": total,
        "clauses_dispositioned_pct": round(100.0 * dispositioned / total, 2) if total else 0,
        "rule_candidates_by_status": by_status,
        "rules_approved_wp6": rules_count,
        "review_items_open": review_open,
        "orphan_number_sweep": {
            "tier1_numeric_tokens": total_numbers,
            "claimed": claimed_numbers,
            "clauses_with_orphans": len(orphan_clauses),
            "detail": orphan_clauses[:25],
        },
        "exception_language_clauses": exception_clauses,
    }


def sample_atoms(conn: psycopg.Connection, sv_id: str, n: int = 5) -> list[dict]:
    rows = conn.execute(
        "SELECT rule_key, operator, value_json, unit, pathway, quote, condition_json, "
        "metadata_json->>'confidence' FROM rules "
        "WHERE source_version_id = %s AND metadata_json->>'wp6' = 'true' "
        "ORDER BY rule_key LIMIT %s",
        (sv_id, n),
    ).fetchall()
    return [
        {
            "rule_key": r[0], "operator": r[1], "value_json": r[2], "unit": r[3],
            "pathway": r[4], "quote_anchor": r[5], "applicability": r[6], "confidence": r[7],
        }
        for r in rows
    ]


# ---------------------------------------------------------------------------
# Legacy seed cross-check
# ---------------------------------------------------------------------------

LEGACY_EXPECTATIONS = [
    # (base rule_key here, density code, operator, value, unit) from evals/seeds/rule_rows.jsonl
    ("primary_street_setback", "R30", "gte", 4.0, "m"),
    ("site_cover", "R30", "lte", 60.0, "%"),
    ("open_space", "R30", "gte", 45.0, "%"),
    ("outdoor_living_area", "R30", "gte", 24.0, "m2"),
]


def cross_check(conn: psycopg.Connection, sv_id: str) -> list[dict]:
    out = []
    rows = conn.execute(
        "SELECT value_json->>'base_rule_key', operator, (value_json->>'value')::float, unit, "
        "applicable_r_codes FROM rules "
        "WHERE source_version_id = %s AND metadata_json->>'wp6' = 'true'",
        (sv_id,),
    ).fetchall()
    for key, code, op, val, unit in LEGACY_EXPECTATIONS:
        matches = [
            r for r in rows
            if r[0] == key and r[4] and code in r[4]
        ]
        if not matches:
            out.append({"expectation": [key, code, op, val, unit], "status": "not_extracted"})
            continue
        agree = any(r[1] == op and abs(r[2] - val) < 1e-6 and r[3] == unit for r in matches)
        out.append({
            "expectation": [key, code, op, val, unit],
            "status": "agree" if agree else "DISAGREE",
            "extracted": [[r[0], r[1], r[2], r[3]] for r in matches],
        })
    return out


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source-version", required=True)
    ap.add_argument("--structure-only", action="store_true")
    ap.add_argument("--limit", type=int, default=0, help="cap rule-bearing clauses processed")
    ap.add_argument("--report", default="")
    ap.add_argument("--workers", type=int, default=1, help="concurrent clause workers (each gets its own DB connection)")
    args = ap.parse_args()

    dsn = os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://").replace(
        "postgresql+psycopg://", "postgresql://"
    )
    sv_id = args.source_version
    report: dict[str, Any] = {"source_version_id": sv_id, "escalations": []}

    with psycopg.connect(dsn) as conn:
        report["structure_pass"] = structure_pass(conn, sv_id)
        print(f"structure: {report['structure_pass']}", flush=True)

        if not args.structure_only:
            endpoints, escalations = build_endpoints()
            report["escalations"].extend(escalations)
            report["ensemble_models"] = [f"{e.name}:{e.model}" for e in endpoints]

            stats = {
                "clauses_processed": 0,
                "atoms_auto_accepted": 0,
                "atoms_challenge_accepted": 0,
                "atoms_pending_review": 0,
                "validator_rejects": 0,
                "llm_errors": [],
            }
            clauses = conn.execute(
                "SELECT c.id, c.source_chunk_id, c.clause_path, c.text FROM clauses c "
                "WHERE c.source_version_id = %s AND c.disposition = 'rule_bearing' "
                "AND NOT EXISTS (SELECT 1 FROM rule_candidates rc WHERE rc.clause_id = c.id) "
                "ORDER BY c.clause_key",
                (sv_id,),
            ).fetchall()
            clauses = [c for c in clauses if TIER1_TOPIC_RE.search(c[3]) and re.search(r"\d", c[3])]
            if args.limit:
                clauses = clauses[: args.limit]
            print(f"rule-bearing tier1 clauses to process: {len(clauses)}", flush=True)
            if args.workers <= 1:
                for cid, chunk_id, path, text in clauses:
                    stats["clauses_processed"] += 1
                    print(f"[{stats['clauses_processed']}/{len(clauses)}] {path}", flush=True)
                    extract_for_clause(conn, endpoints, sv_id, str(cid), str(chunk_id) if chunk_id else None,
                                       path or "?", text, stats)
            else:
                import threading
                from concurrent.futures import ThreadPoolExecutor, as_completed

                lock = threading.Lock()
                tls = threading.local()

                def thread_conn() -> psycopg.Connection:
                    if getattr(tls, "conn", None) is None:
                        tls.conn = psycopg.connect(dsn)
                    return tls.conn

                def work(item: tuple) -> dict:
                    cid, chunk_id, path, text = item
                    local_stats = {
                        "clauses_processed": 1,
                        "atoms_auto_accepted": 0,
                        "atoms_challenge_accepted": 0,
                        "atoms_pending_review": 0,
                        "validator_rejects": 0,
                        "llm_errors": [],
                    }
                    extract_for_clause(thread_conn(), endpoints, sv_id, str(cid),
                                       str(chunk_id) if chunk_id else None,
                                       path or "?", text, local_stats)
                    return local_stats

                with ThreadPoolExecutor(max_workers=args.workers) as pool:
                    futures = {pool.submit(work, item): item for item in clauses}
                    for fut in as_completed(futures):
                        item = futures[fut]
                        try:
                            local_stats = fut.result()
                        except Exception as exc:  # noqa: BLE001 — keep the run alive, record the failure
                            local_stats = {"clauses_processed": 1, "llm_errors": [f"{item[2]}: {exc}"]}
                        with lock:
                            for k, v in local_stats.items():
                                if k == "llm_errors":
                                    stats["llm_errors"].extend(v)
                                else:
                                    stats[k] = stats.get(k, 0) + v
                            print(f"[{stats['clauses_processed']}/{len(clauses)}] {item[2]}", flush=True)
            report["extraction_stats"] = stats

        report["audit"] = audit(conn, sv_id)
        report["sample_approved_atoms"] = sample_atoms(conn, sv_id)
        report["legacy_seed_cross_check"] = cross_check(conn, sv_id)
        for item in report["legacy_seed_cross_check"]:
            if item["status"] == "DISAGREE":
                report["escalations"].append(
                    f"Cross-check disagreement vs legacy seed: {item} — investigate before fan-out."
                )

    out = json.dumps(report, indent=2, default=str)
    if args.report:
        with open(args.report, "w", encoding="utf-8") as fh:
            fh.write(out)
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
