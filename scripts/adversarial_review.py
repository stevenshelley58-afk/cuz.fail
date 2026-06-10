"""Phase 5 — adversarial multi-agent review harness (docs/CORPUS_COMPLETENESS_PLAN.md).

Runs INSIDE the api container (psycopg3 + LLM env present), like wp6_extract.py:

    docker exec draftcheck-wa-v3-api-1 python /app/scripts/adversarial_review.py \
        <subcommand> --round N [--source-version <uuid>] [--limit N] \
        [--report /app/reports/adversarial_<role>.json]

Subcommands (one per agent role + lifecycle steps):

  re-extract          Re-extractor: blind re-extraction over a corpus slice. The prompt
                      contains RAW CLAUSE TEXT ONLY (never the existing rule atoms). The
                      fresh extraction is diffed against approved DB atoms; any mismatch
                      (value / unit / operator / condition / pathway) becomes a finding.
  prosecute           Prosecutor: generates realistic user questions from the DB ONLY
                      (atoms + chunks; per density code, per Tier-1 check, edge cases:
                      corner lots, battle-axe, granny flats, mixed pathways), answers
                      them from the DB, then a verifier pass WITH the raw source text
                      checks each answer. Wrong / uncitable answer = finding.
  gap-hunt            Gap hunter: re-scrapes the index URLs recorded in
                      target_manifest.index_source_url and flags WA instruments that are
                      not in the manifest (deterministic diff vs manifest + aliases).
  conflict-prosecute  Conflict prosecutor: generates concrete lot fact-patterns
                      (corner / battle-axe, each density code, mixed pathways) and
                      asserts each Tier-1 check resolves to exactly ONE winning rule or
                      an explicit cited needs_more_info. Two winners, zero winners, or a
                      never-firing / unlinked exception = finding. Deterministic.
  defend              Defense: claims every open finding (lease columns) and must either
                      propose a fix (status='fixed' + corrective action recorded in
                      resolution_note + a review_items row — rules are NEVER auto-mutated)
                      or reject it with a verbatim quote proving the DB right
                      (status='rejected', quote stored). Undecidable rows stay open.
  judge               Judge: deterministic resolution where possible (verbatim
                      quote-existence checks, manifest re-match, conflict re-resolution),
                      LLM otherwise; unresolved stays open (pending). Every CONFIRMED
                      (or fixed) finding also emits a golden eval_cases row so the same
                      failure can never silently return.
  closure             Computes the stopping rule (2 consecutive full rounds with zero
                      confirmed findings and zero still-open findings) from
                      adversarial_findings.round and writes reports/adversarial_closure.json.

Governance (CLAUDE.md): the LLM only proposes; deterministic checks decide. Every claim
carries a quote; quotes are validated verbatim (whitespace-normalised) against clause
text. Spend-conscious: --limit caps every slice and model usage is logged in the report.
Rounds are idempotent: a finding is keyed on (round, agent_role, target, claim) and is
never inserted twice.
"""

from __future__ import annotations

import argparse
import html as html_lib
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
sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
)

import psycopg  # noqa: E402
from psycopg.types.json import Json  # noqa: E402

from draftcheck.extraction.normalize import normalize_unit, whitespace_normalize  # noqa: E402
from draftcheck.extraction.vocabulary import OPERATORS, RULE_KEYS  # noqa: E402

ORG_ID_FALLBACK = "1d31c315-5087-47df-a8d4-ebfd08efad5d"  # DraftCheck WA (same as wp6)
EVAL_SUITE = "adversarial-regression"
PATHWAYS = ("deemed_to_comply", "design_principle", "none")
LOT_TYPES = ("standard", "corner", "battle_axe")
CANONICAL_R_CODES = (
    "R5", "R10", "R12.5", "R15", "R17.5", "R20", "R25", "R30",
    "R35", "R40", "R50", "R60", "R80",
)

# Tier-1 check key -> base rule keys produced by the wp6 extractor vocabulary.
CHECK_TO_BASE_RULE_KEYS: dict[str, tuple[str, ...]] = {
    "setback_front": ("primary_street_setback",),
    "setback_rear": ("rear_setback",),
    "setback_side_primary": ("side_setback",),
    "setback_side_secondary": ("side_setback", "secondary_street_setback"),
    "site_cover": ("site_cover",),
    "open_space": ("open_space",),
    "garage_width": ("garage_width",),
    "garage_dominance": ("garage_dominance",),
    "boundary_wall_length": ("boundary_wall_length",),
}

INSTRUMENT_RE = re.compile(
    r"state\s+planning\s+policy|\bSPP\s*\d|local\s+planning\s+policy|\bLPP\s*\d|"
    r"local\s+planning\s+scheme|town\s+planning\s+scheme|scheme\s+amendment|"
    r"practice\s+note|position\s+statement|residential\s+design\s+codes|r-?codes|"
    r"development\s+control\s+policy|planning\s+bulletin|structure\s+plan",
    re.IGNORECASE,
)
ANCHOR_RE = re.compile(
    r"<a\b[^>]*href=[\"']([^\"']+)[\"'][^>]*>(.*?)</a>", re.IGNORECASE | re.DOTALL
)
TAG_RE = re.compile(r"<[^>]+>")

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

REEXTRACT_SYSTEM_PROMPT = (
    "You are a meticulous regulatory data extractor for the Western Australian "
    "Residential Design Codes. You extract quantitative rule atoms from clause text. "
    "Rules: (1) Output ONLY a single JSON object matching the schema, no prose, no markdown "
    "fences. (2) Every atom MUST include a quote that is an exact verbatim substring of the "
    "supplied clause text and the quote must contain the extracted number. (3) NEVER guess or "
    "infer numbers not present in the text. (4) If the clause contains no extractable "
    "quantitative rule, return {\"atoms\": [], \"no_rules\": true}. (5) pathway is "
    "deemed_to_comply for C-clauses / deemed-to-comply requirements, design_principle for "
    "P-clauses, none otherwise."
)

VERIFIER_SYSTEM_PROMPT = (
    "You are a strict verifier for a WA planning-rules database. You receive a user "
    "question, the database's answer, and the raw source clause text the answer cites. "
    "Decide whether the answer is fully supported by the source text. Output ONLY a JSON "
    "object: {\"verdict\": \"supported\" | \"wrong\" | \"unsupported\", \"reason\": \"...\", "
    "\"quote\": \"verbatim substring of the source text backing your verdict\"}. "
    "Temperature is 0; never speculate beyond the supplied text."
)

JUDGE_SYSTEM_PROMPT = (
    "You are a deterministic-minded judge resolving a dispute between an adversarial "
    "attacker finding and a defense of a WA planning-rules database. You receive the "
    "finding claim, the attacker's evidence quote, the defense note, and the raw clause "
    "text. Output ONLY a JSON object: {\"verdict\": \"confirmed\" | \"rejected\", "
    "\"reason\": \"...\", \"quote\": \"verbatim substring of the clause text that decides it\"}. "
    "If the clause text cannot decide the dispute, use verdict \"rejected\" only when the "
    "attacker's claim is contradicted; otherwise prefer \"confirmed\"."
)


# ---------------------------------------------------------------------------
# LLM plumbing (copied pattern from scripts/wp6_extract.py; keys optional here)
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


def build_optional_endpoints() -> tuple[LlmEndpoint | None, LlmEndpoint | None, list[str]]:
    """Return (primary=different-family, fallback=minimax, escalations).

    Unlike wp6, missing keys do NOT abort: LLM-dependent steps are skipped with an
    escalation note and a one-command unblock, deterministic steps still run.
    """
    escalations: list[str] = []
    minimax_key = os.environ.get("MINIMAX_API_KEY", "")
    minimax_base = os.environ.get("MINIMAX_BASE_URL", "https://api.minimaxi.chat/v1")
    openrouter_key = os.environ.get("OPENROUTER_API_KEY", "")
    openrouter_base = os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    openai_key = os.environ.get("OPENAI_API_KEY", "")

    minimax = (
        LlmEndpoint("minimax", os.environ.get("MINIMAX_MODEL", "MiniMax-M2"),
                    minimax_base, minimax_key)
        if minimax_key
        else None
    )
    if openrouter_key:
        other: LlmEndpoint | None = LlmEndpoint(
            "openrouter", "openai/gpt-4o", openrouter_base, openrouter_key
        )
    elif openai_key:
        other = LlmEndpoint("openai", "gpt-4o", "https://api.openai.com/v1", openai_key)
    else:
        other = None

    if other is None and minimax is not None:
        escalations.append(
            "Neither OPENROUTER_API_KEY nor OPENAI_API_KEY present — re-extraction runs on "
            "MiniMax only; 'different model family' requirement NOT met. Unblock: add "
            "OPENROUTER_API_KEY to infra/v3 env and rerun."
        )
    if other is None and minimax is None:
        escalations.append(
            "No LLM keys present (MINIMAX_API_KEY / OPENROUTER_API_KEY / OPENAI_API_KEY) — "
            "all LLM-dependent passes skipped; deterministic checks still ran. Unblock: add "
            "MINIMAX_API_KEY to infra/v3 env and rerun this subcommand."
        )
    return other, minimax, escalations


def tracked_complete(
    ep: LlmEndpoint, usage: dict, system: str, user: str, max_tokens: int = 3000
) -> str:
    out = ep.complete(system, user, max_tokens=max_tokens)
    usage["calls"] = usage.get("calls", 0) + 1
    usage["prompt_chars"] = usage.get("prompt_chars", 0) + len(system) + len(user)
    usage["completion_chars"] = usage.get("completion_chars", 0) + len(out)
    by_model = usage.setdefault("by_model", {})
    key = f"{ep.name}:{ep.model}"
    by_model[key] = by_model.get(key, 0) + 1
    return out


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
# Pure helpers (unit-tested; no DB, no network)
# ---------------------------------------------------------------------------


def quote_exists(quote: str | None, text: str | None) -> bool:
    """Verbatim quote-existence check, whitespace-normalised. Deterministic decider."""
    if not quote or not text:
        return False
    nq = whitespace_normalize(quote)
    if len(nq) < 3:
        return False
    return nq in whitespace_normalize(text)


def canonical_claim(claim: dict) -> str:
    return json.dumps(claim, sort_keys=True, default=str)


def atom_match_key(atom: dict) -> tuple:
    """Identity for matching DB atoms vs re-extracted atoms within one clause."""
    codes = tuple(sorted(str(c).upper() for c in (atom.get("density_codes") or [])))
    return (atom.get("rule_key") or "", codes, atom.get("dwelling_type") or "any")


def diff_atom_sets(db_atoms: list[dict], fresh_atoms: list[dict]) -> list[dict]:
    """Diff DB atoms against a blind re-extraction of the same clause.

    Atom dicts carry: rule_key, operator, value, unit, pathway, condition,
    density_codes, dwelling_type, quote (and optionally rule_id).
    Returns mismatch dicts: kind in {missing_in_reextraction, missing_in_db,
    field_mismatch}; field in {value, unit, operator, pathway, condition}.
    """
    mismatches: list[dict] = []
    db_by_key: dict[tuple, dict] = {}
    for a in db_atoms:
        db_by_key.setdefault(atom_match_key(a), a)
    fresh_by_key: dict[tuple, dict] = {}
    for a in fresh_atoms:
        fresh_by_key.setdefault(atom_match_key(a), a)

    for key in sorted(set(db_by_key) - set(fresh_by_key)):
        a = db_by_key[key]
        mismatches.append({
            "kind": "missing_in_reextraction",
            "rule_key": a.get("rule_key"),
            "density_codes": list(key[1]),
            "db_value": a.get("value"),
            "db_quote": a.get("quote"),
            "rule_id": a.get("rule_id"),
        })
    for key in sorted(set(fresh_by_key) - set(db_by_key)):
        a = fresh_by_key[key]
        mismatches.append({
            "kind": "missing_in_db",
            "rule_key": a.get("rule_key"),
            "density_codes": list(key[1]),
            "fresh_value": a.get("value"),
            "fresh_quote": a.get("quote"),
        })
    for key in sorted(set(db_by_key) & set(fresh_by_key)):
        db_a, fr_a = db_by_key[key], fresh_by_key[key]
        for fld in ("value", "unit", "operator", "pathway", "condition"):
            dv, fv = db_a.get(fld), fr_a.get(fld)
            if fld == "value":
                try:
                    same = dv is not None and fv is not None and abs(float(dv) - float(fv)) < 1e-6
                except (TypeError, ValueError):
                    same = dv == fv
            elif fld == "condition":
                same = whitespace_normalize(str(dv or "")).lower() == \
                    whitespace_normalize(str(fv or "")).lower()
            else:
                same = (dv or None) == (fv or None)
            if not same:
                mismatches.append({
                    "kind": "field_mismatch",
                    "field": fld,
                    "rule_key": db_a.get("rule_key"),
                    "density_codes": list(key[1]),
                    "db_value": dv,
                    "fresh_value": fv,
                    "db_quote": db_a.get("quote"),
                    "fresh_quote": fr_a.get("quote"),
                    "rule_id": db_a.get("rule_id"),
                })
    return mismatches


def mismatch_severity(mismatch: dict) -> str:
    kind = mismatch.get("kind")
    if kind == "field_mismatch":
        return "critical" if mismatch.get("field") in ("value", "unit", "operator") else "major"
    if kind == "missing_in_db":
        return "major"
    return "minor"  # missing_in_reextraction: weakest signal (model may have skipped)


EDGE_SCENARIOS: tuple[tuple[str, str, str], ...] = (
    ("corner_lot", "setback_side_secondary",
     "My lot is a corner lot coded {code}. What secondary street setback applies under the "
     "deemed-to-comply pathway?"),
    ("battle_axe", "setback_front",
     "I have a battle-axe (rear) lot coded {code}. What front setback applies to the dwelling?"),
    ("granny_flat", "site_cover",
     "I want to add a granny flat (ancillary dwelling) on an {code} lot. What is the maximum "
     "site coverage?"),
    ("mixed_pathway", "open_space",
     "On an {code} lot, can I use the design-principles pathway for open space instead of the "
     "deemed-to-comply percentage, and what is that percentage?"),
)


def generate_prosecution_questions(
    check_keys: list[str], density_codes: list[str], include_edge_cases: bool = True
) -> list[dict]:
    """Deterministic question set: per density code x per Tier-1 check + edge cases.

    Built from DB contents only (check registry keys + density codes seen in atoms) —
    the Prosecutor never sees the raw PDFs at generation time.
    """
    questions: list[dict] = []
    for code in sorted(set(density_codes)):
        for ck in sorted(set(check_keys)):
            questions.append({
                "key": f"{ck}:{code}:standard",
                "check_key": ck,
                "density_code": code,
                "scenario": "standard",
                "question": (
                    f"What is the {ck.replace('_', ' ')} requirement for a single house on an "
                    f"{code}-coded lot under the deemed-to-comply pathway of the WA R-Codes?"
                ),
            })
        if include_edge_cases:
            for scenario, ck, template in EDGE_SCENARIOS:
                questions.append({
                    "key": f"{ck}:{code}:{scenario}",
                    "check_key": ck,
                    "density_code": code,
                    "scenario": scenario,
                    "question": template.format(code=code),
                })
    return questions


def generate_fact_patterns(density_codes: list[str]) -> list[dict]:
    """Deterministic lot fact-patterns: every density code x lot type x pathway mix."""
    patterns: list[dict] = []
    codes = sorted(set(density_codes))
    for code in codes:
        for lot_type in LOT_TYPES:
            patterns.append({
                "key": f"{code}|{lot_type}|deemed_to_comply",
                "density_code": code,
                "lot_type": lot_type,
                "pathway": "deemed_to_comply",
                "dwelling_type": "single_house",
            })
        # mixed-pathway probe + granny flat overlay on a standard lot
        patterns.append({
            "key": f"{code}|standard|design_principle",
            "density_code": code,
            "lot_type": "standard",
            "pathway": "design_principle",
            "dwelling_type": "single_house",
        })
        patterns.append({
            "key": f"{code}|standard|deemed_to_comply|granny_flat",
            "density_code": code,
            "lot_type": "standard",
            "pathway": "deemed_to_comply",
            "dwelling_type": "ancillary_dwelling",
        })
    return patterns


def exception_applies(exception_atom: dict, fact: dict) -> bool:
    """Deterministic keyword test: does the exception's condition match the fact pattern?"""
    cond = whitespace_normalize(str(exception_atom.get("condition") or "")).lower()
    if not cond:
        return False
    lot_type = fact.get("lot_type", "standard")
    dwelling = fact.get("dwelling_type", "single_house")
    if lot_type == "corner" and "corner" in cond:
        return True
    if lot_type == "battle_axe" and ("battle" in cond or "rear lot" in cond):
        return True
    if dwelling == "ancillary_dwelling" and ("ancillary" in cond or "granny" in cond):
        return True
    return False


def resolve_winner(candidates: list[dict], fact: dict) -> dict:
    """Deterministic single-winner resolution for one check x fact pattern.

    candidates: atom dicts (rule_key, rule_type, pathway, operator, value, unit,
    density_codes, condition, quote, rule_id). Returns outcome dict:
    outcome in {one_winner, zero_winners, multiple_winners}; plus dead_exceptions
    (exception atoms whose condition is empty so they can never fire).
    """
    code = str(fact.get("density_code", "")).upper()
    pathway = fact.get("pathway", "deemed_to_comply")

    def code_ok(atom: dict) -> bool:
        codes = atom.get("density_codes") or []
        return not codes or code in {str(c).upper() for c in codes}

    applicable = [c for c in candidates if code_ok(c)]
    path_ok = [c for c in applicable if (c.get("pathway") or "none") in (pathway, "none")]
    exceptions = [c for c in path_ok if c.get("rule_type") == "exception"]
    standards = [c for c in path_ok if c.get("rule_type") != "exception"]

    dead_exceptions = [
        e for e in exceptions
        if not whitespace_normalize(str(e.get("condition") or ""))
    ]
    fired = [e for e in exceptions if exception_applies(e, fact)]

    pool = fired if fired else standards
    # Distinct requirement signatures decide winner count (same value twice = one winner).
    distinct: dict[tuple, dict] = {}
    for c in pool:
        try:
            val = round(float(c.get("value")), 6)
        except (TypeError, ValueError):
            val = c.get("value")
        distinct.setdefault((c.get("operator"), val, c.get("unit")), c)

    if len(distinct) == 1:
        outcome = "one_winner"
    elif len(distinct) == 0:
        outcome = "zero_winners"
    else:
        outcome = "multiple_winners"
    return {
        "outcome": outcome,
        "winners": list(distinct.values()),
        "fired_exceptions": fired,
        "dead_exceptions": dead_exceptions,
        "candidates_considered": len(applicable),
    }


def judge_decide(
    evidence_quote: str | None, clause_text: str | None, db_quote: str | None
) -> str:
    """Deterministic judge core: verbatim quote-existence decides where it can.

    - attacker's evidence quote NOT verbatim in the source -> rejected (attack unanchored)
    - attacker anchored AND the DB's own quote is NOT anchored -> confirmed
    - both anchored (text supports both readings) -> pending (needs LLM/operator)
    """
    ev_ok = quote_exists(evidence_quote, clause_text)
    if not ev_ok:
        return "rejected"
    if not quote_exists(db_quote, clause_text):
        return "confirmed"
    return "pending"


def defense_decide(
    claim: dict, evidence_quote: str | None, clause_text: str | None, db_quote: str | None
) -> tuple[str, dict]:
    """Deterministic defense core. Returns (action, detail).

    action in {reject, fix, open}. 'reject' only when the DB quote anchors verbatim and
    the attacker's does not (verbatim quote proving the DB right). 'fix' when the DB
    position is unanchored — the proposed fix is recorded, never auto-applied.
    """
    db_ok = quote_exists(db_quote, clause_text)
    ev_ok = quote_exists(evidence_quote, clause_text)
    if db_ok and not ev_ok:
        return "reject", {
            "quote": db_quote,
            "basis": "DB quote anchors verbatim in the source clause; attacker quote does not",
        }
    if not db_ok and clause_text is not None:
        return "fix", {
            "proposed_fix": claim,
            "note": "DB quote does not anchor in the source clause; corrective action proposed. "
                    "Operator-gated — rules are not auto-mutated.",
        }
    if claim.get("kind") in ("missing_instrument", "zero_winners", "multiple_winners",
                             "dead_exception", "unlinked_exception", "unanswerable"):
        return "fix", {
            "proposed_fix": claim,
            "note": "Structural gap; corrective action proposed. Operator-gated — no auto-mutation.",
        }
    return "open", {"reason": "both quotes anchor (or no source text); needs judge/operator"}


def normalize_title(text: str) -> str:
    text = html_lib.unescape(text)
    text = re.sub(r"[^a-z0-9. ]+", " ", text.lower())
    return whitespace_normalize(text)


def extract_index_links(html_text: str) -> list[dict]:
    """Pull (href, text) anchors out of an index page. Deterministic, stdlib-only."""
    links: list[dict] = []
    for m in ANCHOR_RE.finditer(html_text):
        href = m.group(1).strip()
        text = whitespace_normalize(html_lib.unescape(TAG_RE.sub(" ", m.group(2))))
        if text:
            links.append({"href": href, "text": text})
    return links


def diff_index_entries(
    entries: list[dict],
    manifest_names: list[str],
    alias_exact: list[str],
    alias_regex: list[str],
) -> list[dict]:
    """Deterministic manifest-closure diff: index entries that look like WA planning
    instruments but match neither the manifest nor the alias table."""
    known = {normalize_title(n) for n in manifest_names if n}
    known |= {normalize_title(a) for a in alias_exact if a}
    regexes = []
    for pat in alias_regex:
        try:
            regexes.append(re.compile(pat, re.IGNORECASE))
        except re.error:
            continue
    unmatched: list[dict] = []
    seen: set[str] = set()
    for entry in entries:
        text = entry.get("text") or ""
        if not INSTRUMENT_RE.search(text):
            continue
        nt = normalize_title(text)
        if not nt or nt in seen:
            continue
        seen.add(nt)
        if nt in known:
            continue
        if any(k and (k in nt or nt in k) for k in known):
            continue
        if any(rx.search(text) for rx in regexes):
            continue
        unmatched.append(entry)
    return unmatched


def compute_closure(per_round: dict[int, dict]) -> dict:
    """Stopping rule: 2 consecutive trailing full rounds with zero confirmed (or fixed,
    i.e. real) findings and zero still-open findings.

    per_round: {round: {"confirmed": n, "open": m}} — 'confirmed' should count
    status in ('confirmed','fixed') since a fixed finding was a real defect.
    """
    rounds = sorted(per_round)
    trailing_clean = 0
    for r in reversed(rounds):
        row = per_round[r]
        if row.get("confirmed", 0) == 0 and row.get("open", 0) == 0:
            trailing_clean += 1
        else:
            break
    closed = len(rounds) >= 2 and trailing_clean >= 2
    return {
        "rounds_run": len(rounds),
        "trailing_clean_rounds": trailing_clean,
        "closed": closed,
        "stopping_rule": "2 consecutive full rounds with zero confirmed findings",
    }


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------


def get_dsn() -> str:
    return os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://").replace(
        "postgresql+psycopg://", "postgresql://"
    )


def get_org_id(conn: psycopg.Connection) -> str:
    row = conn.execute("SELECT id FROM orgs ORDER BY created_at LIMIT 1").fetchone()
    return str(row[0]) if row else ORG_ID_FALLBACK


def insert_finding(
    conn: psycopg.Connection,
    round_no: int,
    agent_role: str,
    target: str,
    claim: dict | str,
    evidence_quote: str | None,
    severity: str,
) -> bool:
    """Idempotent finding insert keyed on (round, agent_role, target, claim)."""
    claim_text = canonical_claim(claim) if isinstance(claim, dict) else str(claim)
    target = target[:300]
    exists = conn.execute(
        "SELECT 1 FROM adversarial_findings "
        "WHERE round = %s AND agent_role = %s AND target = %s AND claim = %s LIMIT 1",
        (round_no, agent_role, target, claim_text),
    ).fetchone()
    if exists:
        return False
    conn.execute(
        "INSERT INTO adversarial_findings (round, agent_role, target, claim, evidence_quote, "
        "severity, status) VALUES (%s, %s, %s, %s, %s, %s, 'open')",
        (round_no, agent_role, target, claim_text, evidence_quote, severity),
    )
    return True


def latest_round(conn: psycopg.Connection) -> int:
    row = conn.execute("SELECT COALESCE(max(round), 0) FROM adversarial_findings").fetchone()
    return int(row[0])


def fetch_clause_text(conn: psycopg.Connection, clause_id: str | None) -> str | None:
    if not clause_id:
        return None
    try:
        row = conn.execute("SELECT text FROM clauses WHERE id = %s", (clause_id,)).fetchone()
    except psycopg.Error:
        conn.rollback()
        return None
    return row[0] if row else None


def db_atoms_for_clause(conn: psycopg.Connection, clause_id: str) -> list[dict]:
    rows = conn.execute(
        "SELECT r.id, COALESCE(r.value_json->>'base_rule_key', r.rule_key), r.rule_type, "
        "r.operator, (r.value_json->>'value')::float, r.unit, r.pathway, r.condition_json, "
        "r.quote, r.applicable_r_codes "
        "FROM rules r WHERE r.clause_id = %s AND r.lifecycle_status = 'approved'",
        (clause_id,),
    ).fetchall()
    atoms = []
    for rid, rkey, rtype, op, val, unit, pathway, cond, quote, codes in rows:
        cond = cond if isinstance(cond, dict) else {}
        atoms.append({
            "rule_id": str(rid),
            "rule_key": rkey,
            "rule_type": rtype,
            "operator": op,
            "value": val,
            "unit": unit,
            "pathway": pathway,
            "condition": cond.get("condition") or cond.get("text") or "",
            "density_codes": list(codes) if codes else [],
            "dwelling_type": cond.get("dwelling_type") or "any",
            "quote": quote,
        })
    return atoms


def approved_density_codes(conn: psycopg.Connection) -> list[str]:
    rows = conn.execute(
        "SELECT DISTINCT jsonb_array_elements_text(applicable_r_codes) FROM rules "
        "WHERE lifecycle_status = 'approved' AND applicable_r_codes IS NOT NULL"
    ).fetchall()
    return sorted({r[0] for r in rows})


def approved_atoms_for_base_keys(
    conn: psycopg.Connection, base_keys: tuple[str, ...]
) -> list[dict]:
    rows = conn.execute(
        "SELECT r.id, COALESCE(r.value_json->>'base_rule_key', r.rule_key), r.rule_type, "
        "r.operator, (r.value_json->>'value')::float, r.unit, r.pathway, r.condition_json, "
        "r.quote, r.applicable_r_codes, r.clause_id "
        "FROM rules r WHERE r.lifecycle_status = 'approved' AND "
        "(r.value_json->>'base_rule_key' = ANY(%s) OR r.rule_key = ANY(%s))",
        (list(base_keys), list(base_keys)),
    ).fetchall()
    atoms = []
    for rid, rkey, rtype, op, val, unit, pathway, cond, quote, codes, clause_id in rows:
        cond = cond if isinstance(cond, dict) else {}
        atoms.append({
            "rule_id": str(rid),
            "rule_key": rkey,
            "rule_type": rtype,
            "operator": op,
            "value": val,
            "unit": unit,
            "pathway": pathway,
            "condition": cond.get("condition") or cond.get("text") or "",
            "density_codes": list(codes) if codes else [],
            "dwelling_type": cond.get("dwelling_type") or "any",
            "quote": quote,
            "clause_id": str(clause_id) if clause_id else None,
        })
    return atoms


def open_review_item(
    conn: psycopg.Connection, org_id: str, finding_id: str, reason: str, severity: str
) -> None:
    conn.execute(
        "INSERT INTO review_items (id, org_id, subject_type, subject_id, reason, status, "
        "priority, source_json, metadata_json, severity, created_at, updated_at) "
        "VALUES (gen_random_uuid(), %s, 'adversarial_finding', %s, %s, 'open', 1, '{}', %s, "
        "%s, now(), now())",
        (org_id, finding_id, reason, Json({"adversarial_review": True}),
         severity if severity in ("critical", "major", "minor") else "medium"),
    )


def emit_eval_case(conn: psycopg.Connection, finding: dict) -> bool:
    """Every confirmed/fixed finding becomes a golden eval case (regression lock)."""
    case_key = f"adv-r{finding['round']}-{finding['id']}"[:160]
    try:
        claim = json.loads(finding["claim"])
    except (json.JSONDecodeError, TypeError):
        claim = {"raw": finding["claim"]}
    cur = conn.execute(
        "INSERT INTO eval_cases (id, suite_name, case_key, skill_name, source_version_id, "
        "input_json, expected_json, status, metadata_json, created_at, updated_at) "
        "VALUES (gen_random_uuid(), %s, %s, %s, NULL, %s, %s, 'active', %s, now(), now()) "
        "ON CONFLICT (suite_name, case_key) DO NOTHING",
        (
            EVAL_SUITE,
            case_key,
            f"adversarial_{finding['agent_role']}",
            Json({
                "finding_id": finding["id"],
                "round": finding["round"],
                "agent_role": finding["agent_role"],
                "target": finding["target"],
                "claim": claim,
            }),
            Json({
                "finding_must_stay_resolved": True,
                "final_status": finding["status"],
                "evidence_quote": finding.get("evidence_quote"),
            }),
            Json({"created_by": "adversarial_review.py", "phase": "phase5"}),
        ),
    )
    return cur.rowcount > 0


# ---------------------------------------------------------------------------
# Subcommand: re-extract
# ---------------------------------------------------------------------------


def reextract_prompt(clause_path: str, clause_text: str) -> str:
    # INPUT DENIAL: raw clause text only — never the existing rule atoms.
    return (
        f"Clause reference: {clause_path}\n"
        f"--- CLAUSE TEXT START ---\n{clause_text}\n--- CLAUSE TEXT END ---\n\n"
        f"Extract every quantitative rule atom from the clause text above.\n"
        f"Respond with ONLY a JSON object in this schema:\n{JSON_SCHEMA_TEXT}"
    )


def parse_fresh_atoms(payload: dict | None, clause_text: str) -> list[dict]:
    if not payload or not isinstance(payload.get("atoms"), list):
        return []
    atoms: list[dict] = []
    for a in payload["atoms"]:
        if not isinstance(a, dict):
            continue
        try:
            value = float(a["value"])
        except (KeyError, TypeError, ValueError):
            continue
        unit_raw = a.get("unit")
        value, unit = normalize_unit(value, unit_raw if unit_raw else None)
        quote = str(a.get("quote", ""))
        if not quote_exists(quote, clause_text):
            continue  # deterministic gate: unanchored fresh atoms are discarded, never used
        appl = a.get("applicability") if isinstance(a.get("applicability"), dict) else {}
        atoms.append({
            "rule_key": str(a.get("rule_key", "")),
            "rule_type": str(a.get("rule_type", "standard")),
            "operator": str(a.get("operator", "")),
            "value": value,
            "unit": unit,
            "pathway": str(a.get("pathway", "")),
            "condition": str(appl.get("condition") or ""),
            "density_codes": [str(c) for c in (appl.get("density_codes") or [])],
            "dwelling_type": str(appl.get("dwelling_type") or "any"),
            "quote": quote,
        })
    return atoms


def cmd_reextract(conn: psycopg.Connection, args: argparse.Namespace) -> dict:
    report: dict[str, Any] = {"subcommand": "re-extract", "round": args.round, "escalations": []}
    other, minimax, escalations = build_optional_endpoints()
    report["escalations"].extend(escalations)
    endpoint = other or minimax
    if endpoint is None:
        report["clauses_processed"] = 0
        report["findings_inserted"] = 0
        return report
    report["model"] = f"{endpoint.name}:{endpoint.model}"

    clauses = conn.execute(
        "SELECT c.id, c.clause_path, c.text FROM clauses c "
        "WHERE c.source_version_id = %s AND EXISTS "
        "(SELECT 1 FROM rules r WHERE r.clause_id = c.id AND r.lifecycle_status = 'approved') "
        "ORDER BY c.clause_key",
        (args.source_version,),
    ).fetchall()
    if args.limit:
        clauses = clauses[: args.limit]

    usage: dict[str, Any] = {}
    inserted = 0
    errors: list[str] = []
    for clause_id, clause_path, text in clauses:
        clause_id = str(clause_id)
        try:
            raw = tracked_complete(
                endpoint, usage, REEXTRACT_SYSTEM_PROMPT, reextract_prompt(clause_path or "?", text)
            )
        except RuntimeError as exc:
            errors.append(f"{clause_path}: {exc}")
            continue
        fresh = parse_fresh_atoms(parse_llm_json(raw), text)
        db_atoms = db_atoms_for_clause(conn, clause_id)
        for mismatch in diff_atom_sets(db_atoms, fresh):
            claim = dict(mismatch)
            claim["clause_id"] = clause_id
            claim["clause_path"] = clause_path
            claim["db_quote"] = mismatch.get("db_quote")
            evidence = mismatch.get("fresh_quote") or mismatch.get("db_quote")
            if insert_finding(
                conn, args.round, "re_extractor", f"clause:{clause_id}",
                claim, evidence, mismatch_severity(mismatch),
            ):
                inserted += 1
        conn.commit()
    report.update({
        "clauses_processed": len(clauses),
        "findings_inserted": inserted,
        "llm_usage": usage,
        "llm_errors": errors,
    })
    return report


# ---------------------------------------------------------------------------
# Subcommand: prosecute
# ---------------------------------------------------------------------------


def answer_from_db(conn: psycopg.Connection, question: dict) -> dict:
    """Answer a generated question from the DB only (atoms + their stored quotes)."""
    base_keys = CHECK_TO_BASE_RULE_KEYS.get(question["check_key"], ())
    if not base_keys:
        return {"status": "unsupported", "reason": "no rule-key mapping for check"}
    atoms = approved_atoms_for_base_keys(conn, base_keys)
    code = question["density_code"].upper()
    matches = [
        a for a in atoms
        if not a["density_codes"] or code in {str(c).upper() for c in a["density_codes"]}
    ]
    matches = [a for a in matches if (a.get("pathway") or "none") in ("deemed_to_comply", "none")]
    if not matches:
        return {"status": "unsupported", "reason": "no approved atom covers this check x code"}
    distinct: dict[tuple, dict] = {}
    for a in matches:
        distinct.setdefault((a["operator"], a["value"], a["unit"]), a)
    best = sorted(
        distinct.values(),
        key=lambda a: (0 if a["density_codes"] else 1, a["rule_key"], str(a["rule_id"])),
    )[0]
    return {
        "status": "answered",
        "rule_id": best["rule_id"],
        "clause_id": best.get("clause_id"),
        "value": best["value"],
        "unit": best["unit"],
        "operator": best["operator"],
        "quote": best["quote"],
        "ambiguous": len(distinct) > 1,
        "distinct_answers": len(distinct),
    }


def cmd_prosecute(conn: psycopg.Connection, args: argparse.Namespace) -> dict:
    report: dict[str, Any] = {"subcommand": "prosecute", "round": args.round, "escalations": []}
    other, minimax, escalations = build_optional_endpoints()
    verifier = minimax or other
    if verifier is None:
        report["escalations"].extend(escalations)

    codes = approved_density_codes(conn) or list(CANONICAL_R_CODES)
    questions = generate_prosecution_questions(sorted(CHECK_TO_BASE_RULE_KEYS), codes)
    if args.limit:
        questions = questions[: args.limit]

    usage: dict[str, Any] = {}
    inserted = 0
    answered = uncitable = wrong = unanswerable = 0
    errors: list[str] = []
    for q in questions:
        answer = answer_from_db(conn, q)
        target = f"query:{q['key']}"
        if answer["status"] != "answered":
            unanswerable += 1
            claim = {"kind": "unanswerable", "question": q["question"],
                     "check_key": q["check_key"], "density_code": q["density_code"],
                     "scenario": q["scenario"], "reason": answer.get("reason")}
            if insert_finding(conn, args.round, "prosecutor", target, claim, None, "major"):
                inserted += 1
            continue
        answered += 1
        clause_text = fetch_clause_text(conn, answer.get("clause_id"))
        # Deterministic verifier leg: the cited quote must anchor verbatim in the source.
        if not quote_exists(answer.get("quote"), clause_text):
            uncitable += 1
            claim = {"kind": "uncitable_answer", "question": q["question"],
                     "check_key": q["check_key"], "density_code": q["density_code"],
                     "scenario": q["scenario"], "rule_id": answer["rule_id"],
                     "clause_id": answer.get("clause_id"), "db_quote": answer.get("quote"),
                     "answer": {"value": answer["value"], "unit": answer["unit"],
                                "operator": answer["operator"]}}
            if insert_finding(conn, args.round, "prosecutor", target, claim,
                              answer.get("quote"), "major"):
                inserted += 1
            conn.commit()
            continue
        if answer.get("ambiguous"):
            claim = {"kind": "ambiguous_answer", "question": q["question"],
                     "check_key": q["check_key"], "density_code": q["density_code"],
                     "scenario": q["scenario"], "rule_id": answer["rule_id"],
                     "clause_id": answer.get("clause_id"), "db_quote": answer.get("quote"),
                     "distinct_answers": answer["distinct_answers"]}
            if insert_finding(conn, args.round, "prosecutor", target, claim,
                              answer.get("quote"), "major"):
                inserted += 1
        # LLM verifier leg (only the verifier sees raw source text).
        if verifier is not None and clause_text:
            user = (
                f"QUESTION: {q['question']}\n\n"
                f"DATABASE ANSWER: {answer['operator']} {answer['value']} {answer['unit']} "
                f"(cited quote: {answer['quote']!r})\n\n"
                f"--- RAW SOURCE CLAUSE TEXT ---\n{clause_text}\n--- END ---"
            )
            try:
                verdict = parse_llm_json(
                    tracked_complete(verifier, usage, VERIFIER_SYSTEM_PROMPT, user, 800)
                ) or {}
            except RuntimeError as exc:
                errors.append(f"{q['key']}: {exc}")
                verdict = {}
            v = str(verdict.get("verdict", "")).lower()
            v_quote = str(verdict.get("quote", ""))
            # LLM proposes; deterministic check decides: verifier quote must itself anchor.
            if v in ("wrong", "unsupported") and quote_exists(v_quote, clause_text):
                wrong += 1
                claim = {"kind": "wrong_answer", "question": q["question"],
                         "check_key": q["check_key"], "density_code": q["density_code"],
                         "scenario": q["scenario"], "rule_id": answer["rule_id"],
                         "clause_id": answer.get("clause_id"), "db_quote": answer.get("quote"),
                         "verifier_reason": str(verdict.get("reason", ""))[:500]}
                if insert_finding(conn, args.round, "prosecutor", target, claim,
                                  v_quote, "critical"):
                    inserted += 1
        conn.commit()
    report.update({
        "questions_generated": len(questions),
        "answered": answered,
        "unanswerable": unanswerable,
        "uncitable": uncitable,
        "wrong_per_verifier": wrong,
        "findings_inserted": inserted,
        "llm_usage": usage,
        "llm_errors": errors,
    })
    return report


# ---------------------------------------------------------------------------
# Subcommand: gap-hunt
# ---------------------------------------------------------------------------


def fetch_url(url: str, timeout: int = 60) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "LotFile-GapHunter/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def cmd_gap_hunt(conn: psycopg.Connection, args: argparse.Namespace) -> dict:
    report: dict[str, Any] = {"subcommand": "gap-hunt", "round": args.round, "escalations": []}
    index_urls = [
        r[0] for r in conn.execute(
            "SELECT DISTINCT index_source_url FROM target_manifest "
            "WHERE index_source_url IS NOT NULL AND index_source_url <> '' "
            "ORDER BY index_source_url"
        ).fetchall()
    ]
    if args.limit:
        index_urls = index_urls[: args.limit]
    manifest_names = [
        r[0] for r in conn.execute("SELECT instrument_name FROM target_manifest").fetchall()
    ]
    alias_rows = conn.execute(
        "SELECT alias_text, match_kind FROM instrument_aliases"
    ).fetchall()
    alias_exact = [a for a, k in alias_rows if k == "exact"]
    alias_regex = [a for a, k in alias_rows if k == "regex"]

    inserted = 0
    fetched = 0
    errors: list[str] = []
    for url in index_urls:
        try:
            page = fetch_url(url)
        except (urllib.error.URLError, OSError, ValueError) as exc:
            errors.append(f"{url}: {exc}")
            continue
        fetched += 1
        unmatched = diff_index_entries(
            extract_index_links(page), manifest_names, alias_exact, alias_regex
        )
        for entry in unmatched:
            claim = {
                "kind": "missing_instrument",
                "index_source_url": url,
                "candidate_title": entry["text"][:300],
                "candidate_href": entry["href"][:500],
            }
            if insert_finding(conn, args.round, "gap_hunter",
                              f"manifest:{url}"[:300], claim, entry["text"][:500], "major"):
                inserted += 1
        conn.commit()
    report.update({
        "index_urls": len(index_urls),
        "index_urls_fetched": fetched,
        "fetch_errors": errors,
        "findings_inserted": inserted,
    })
    return report


# ---------------------------------------------------------------------------
# Subcommand: conflict-prosecute
# ---------------------------------------------------------------------------


def cmd_conflict_prosecute(conn: psycopg.Connection, args: argparse.Namespace) -> dict:
    report: dict[str, Any] = {"subcommand": "conflict-prosecute", "round": args.round}
    codes = approved_density_codes(conn)
    codes = sorted(set(codes) | set(CANONICAL_R_CODES)) if codes else list(CANONICAL_R_CODES)
    patterns = generate_fact_patterns(codes)
    if args.limit:
        patterns = patterns[: args.limit]

    atoms_by_check: dict[str, list[dict]] = {
        ck: approved_atoms_for_base_keys(conn, keys)
        for ck, keys in sorted(CHECK_TO_BASE_RULE_KEYS.items())
    }
    # Exceptions must be wired into the legal graph to ever fire in the engine.
    edge_rule_ids = {
        r[0] for r in conn.execute(
            "SELECT from_ref FROM legal_edges "
            "WHERE relation IN ('exception_to', 'overrides') AND from_type = 'rule'"
        ).fetchall()
    }

    inserted = 0
    outcomes = {"one_winner": 0, "zero_winners": 0, "multiple_winners": 0}
    flagged_dead: set[str] = set()
    for fact in patterns:
        for check_key, candidates in atoms_by_check.items():
            res = resolve_winner(candidates, fact)
            outcomes[res["outcome"]] += 1
            target = f"check:{check_key}|{fact['key']}"
            if res["outcome"] == "multiple_winners":
                claim = {
                    "kind": "multiple_winners", "check_key": check_key, **fact,
                    "winners": [
                        {"rule_id": w["rule_id"], "operator": w["operator"],
                         "value": w["value"], "unit": w["unit"], "quote": w["quote"]}
                        for w in res["winners"]
                    ],
                }
                ev = res["winners"][0].get("quote")
                if insert_finding(conn, args.round, "conflict_prosecutor", target,
                                  claim, ev, "critical"):
                    inserted += 1
            elif res["outcome"] == "zero_winners" and res["candidates_considered"] == 0:
                claim = {
                    "kind": "zero_winners", "check_key": check_key, **fact,
                    "note": "no approved atom and no explicit cited needs_more_info/n-a record",
                }
                if insert_finding(conn, args.round, "conflict_prosecutor", target,
                                  claim, None, "major"):
                    inserted += 1
            for dead in res["dead_exceptions"]:
                if dead["rule_id"] in flagged_dead:
                    continue
                flagged_dead.add(dead["rule_id"])
                claim = {"kind": "dead_exception", "check_key": check_key,
                         "rule_id": dead["rule_id"], "clause_id": dead.get("clause_id"),
                         "db_quote": dead.get("quote"),
                         "note": "exception atom has no structured condition; it can never fire"}
                if insert_finding(conn, args.round, "conflict_prosecutor",
                                  f"rule:{dead['rule_id']}", claim, dead.get("quote"), "major"):
                    inserted += 1
            for exc_atom in (c for c in candidates if c.get("rule_type") == "exception"):
                if exc_atom["rule_id"] in flagged_dead or exc_atom["rule_id"] in edge_rule_ids:
                    continue
                flagged_dead.add(exc_atom["rule_id"])
                claim = {"kind": "unlinked_exception", "check_key": check_key,
                         "rule_id": exc_atom["rule_id"], "clause_id": exc_atom.get("clause_id"),
                         "db_quote": exc_atom.get("quote"),
                         "note": "exception atom has no exception_to/overrides legal_edge; "
                                 "the engine cannot fire it against its base rule"}
                if insert_finding(conn, args.round, "conflict_prosecutor",
                                  f"rule:{exc_atom['rule_id']}", claim,
                                  exc_atom.get("quote"), "major"):
                    inserted += 1
        conn.commit()
    report.update({
        "fact_patterns": len(patterns),
        "checks": len(atoms_by_check),
        "outcomes": outcomes,
        "findings_inserted": inserted,
    })
    return report


# ---------------------------------------------------------------------------
# Subcommand: defend
# ---------------------------------------------------------------------------


def claim_open_findings(
    conn: psycopg.Connection, round_no: int, claimed_by: str, limit: int
) -> list[dict]:
    rows = conn.execute(
        "UPDATE adversarial_findings SET claimed_by = %s, "
        "lease_expires_at = now() + interval '30 minutes', updated_at = now() "
        "WHERE id IN (SELECT id FROM adversarial_findings WHERE status = 'open' "
        "  AND round <= %s AND (lease_expires_at IS NULL OR lease_expires_at < now()) "
        "  ORDER BY created_at LIMIT %s FOR UPDATE SKIP LOCKED) "
        "RETURNING id, round, agent_role, target, claim, evidence_quote, severity",
        (claimed_by, round_no, limit),
    ).fetchall()
    conn.commit()
    return [
        {"id": str(r[0]), "round": r[1], "agent_role": r[2], "target": r[3],
         "claim": r[4], "evidence_quote": r[5], "severity": r[6]}
        for r in rows
    ]


def cmd_defend(conn: psycopg.Connection, args: argparse.Namespace) -> dict:
    round_no = args.round or latest_round(conn)
    report: dict[str, Any] = {"subcommand": "defend", "round": round_no, "escalations": []}
    org_id = get_org_id(conn)
    claimed_by = args.claimed_by or f"defense-{os.getpid()}"
    findings = claim_open_findings(conn, round_no, claimed_by, args.limit or 10_000)

    rejected = fixed = left_open = 0
    for f in findings:
        try:
            claim = json.loads(f["claim"])
        except (json.JSONDecodeError, TypeError):
            claim = {"raw": f["claim"]}
        clause_text = fetch_clause_text(conn, claim.get("clause_id"))
        action, detail = defense_decide(claim, f["evidence_quote"], clause_text,
                                        claim.get("db_quote"))
        if action == "reject":
            conn.execute(
                "UPDATE adversarial_findings SET status = 'rejected', resolution_note = %s, "
                "updated_at = now() WHERE id = %s",
                (canonical_claim({"action": "rejected", **detail,
                                  "clause_id": claim.get("clause_id")}), f["id"]),
            )
            rejected += 1
        elif action == "fix":
            # DO NOT auto-mutate rules: record the proposed fix and open a review item
            # for the operator-gated lifecycle.
            conn.execute(
                "UPDATE adversarial_findings SET status = 'fixed', resolution_note = %s, "
                "updated_at = now() WHERE id = %s",
                (canonical_claim({"action": "proposed_fix", **detail}), f["id"]),
            )
            open_review_item(
                conn, org_id, f["id"],
                f"Adversarial finding (round {f['round']}, {f['agent_role']}) on "
                f"{f['target']}: proposed fix awaiting operator approval — "
                f"{str(claim.get('kind', 'unknown'))}",
                f["severity"],
            )
            fixed += 1
        else:
            # Undecidable: no third option taken — leave open (lease expires) and report.
            conn.execute(
                "UPDATE adversarial_findings SET lease_expires_at = now(), "
                "resolution_note = %s, updated_at = now() WHERE id = %s",
                (canonical_claim({"action": "undecided_by_defense", **detail}), f["id"]),
            )
            left_open += 1
        conn.commit()
    report.update({
        "findings_claimed": len(findings),
        "rejected_with_quote": rejected,
        "fixed_proposed": fixed,
        "left_open_for_judge": left_open,
    })
    return report


# ---------------------------------------------------------------------------
# Subcommand: judge
# ---------------------------------------------------------------------------


def judge_gap_finding(conn: psycopg.Connection, claim: dict) -> str:
    """Deterministic: re-match the candidate title against manifest + aliases."""
    title = claim.get("candidate_title") or ""
    manifest_names = [
        r[0] for r in conn.execute("SELECT instrument_name FROM target_manifest").fetchall()
    ]
    alias_rows = conn.execute("SELECT alias_text, match_kind FROM instrument_aliases").fetchall()
    unmatched = diff_index_entries(
        [{"href": claim.get("candidate_href", ""), "text": title}],
        manifest_names,
        [a for a, k in alias_rows if k == "exact"],
        [a for a, k in alias_rows if k == "regex"],
    )
    return "confirmed" if unmatched else "rejected"


def judge_conflict_finding(conn: psycopg.Connection, claim: dict) -> str:
    """Deterministic: re-run the winner resolution for the recorded fact pattern."""
    kind = claim.get("kind")
    check_key = claim.get("check_key", "")
    base_keys = CHECK_TO_BASE_RULE_KEYS.get(check_key, ())
    if not base_keys:
        return "pending"
    candidates = approved_atoms_for_base_keys(conn, base_keys)
    if kind in ("dead_exception", "unlinked_exception"):
        rule_id = claim.get("rule_id")
        still = [c for c in candidates if c["rule_id"] == rule_id
                 and c.get("rule_type") == "exception"]
        if not still:
            return "rejected"
        if kind == "dead_exception":
            atom = still[0]
            empty = not whitespace_normalize(str(atom.get("condition") or ""))
            return "confirmed" if empty else "rejected"
        edge = conn.execute(
            "SELECT 1 FROM legal_edges WHERE from_type = 'rule' AND from_ref = %s "
            "AND relation IN ('exception_to', 'overrides') LIMIT 1",
            (rule_id,),
        ).fetchone()
        return "rejected" if edge else "confirmed"
    fact = {k: claim.get(k) for k in
            ("key", "density_code", "lot_type", "pathway", "dwelling_type")}
    res = resolve_winner(candidates, fact)
    return "confirmed" if res["outcome"] == kind else "rejected"


def cmd_judge(conn: psycopg.Connection, args: argparse.Namespace) -> dict:
    round_no = args.round or latest_round(conn)
    report: dict[str, Any] = {"subcommand": "judge", "round": round_no, "escalations": []}
    other, minimax, escalations = build_optional_endpoints()
    llm = minimax or other
    if llm is None:
        report["escalations"].extend(escalations)
    usage: dict[str, Any] = {}

    rows = conn.execute(
        "SELECT id, round, agent_role, target, claim, evidence_quote, severity, status, "
        "resolution_note FROM adversarial_findings WHERE round = %s "
        "AND status IN ('open', 'rejected', 'fixed') ORDER BY created_at",
        (round_no,),
    ).fetchall()
    if args.limit:
        rows = rows[: args.limit]

    confirmed = rejected = pending = eval_cases_added = reverted = 0
    errors: list[str] = []
    for row in rows:
        f = {"id": str(row[0]), "round": row[1], "agent_role": row[2], "target": row[3],
             "claim": row[4], "evidence_quote": row[5], "severity": row[6], "status": row[7],
             "resolution_note": row[8]}
        try:
            claim = json.loads(f["claim"])
        except (json.JSONDecodeError, TypeError):
            claim = {"raw": f["claim"]}

        if f["status"] == "fixed":
            # A proposed fix means the defect was real: lock it in as an eval case.
            if emit_eval_case(conn, f):
                eval_cases_added += 1
            conn.commit()
            continue

        if f["status"] == "rejected":
            # Audit the defense: its rejection quote must anchor verbatim.
            try:
                note = json.loads(f["resolution_note"] or "{}")
            except json.JSONDecodeError:
                note = {}
            clause_text = fetch_clause_text(conn, note.get("clause_id") or claim.get("clause_id"))
            if note.get("quote") and clause_text is not None \
                    and not quote_exists(note.get("quote"), clause_text):
                conn.execute(
                    "UPDATE adversarial_findings SET status = 'open', updated_at = now(), "
                    "resolution_note = %s WHERE id = %s",
                    (canonical_claim({"action": "rejection_overturned_by_judge",
                                      "reason": "defense quote does not anchor verbatim"}),
                     f["id"]),
                )
                reverted += 1
                conn.commit()
            continue

        # status == 'open': deterministic resolution where possible.
        verdict = "pending"
        if f["agent_role"] == "gap_hunter":
            verdict = judge_gap_finding(conn, claim)
        elif f["agent_role"] == "conflict_prosecutor":
            verdict = judge_conflict_finding(conn, claim)
        else:
            clause_text = fetch_clause_text(conn, claim.get("clause_id"))
            if clause_text is not None:
                verdict = judge_decide(f["evidence_quote"], clause_text, claim.get("db_quote"))
            if verdict == "pending" and llm is not None and clause_text:
                user = (
                    f"FINDING CLAIM: {canonical_claim(claim)}\n"
                    f"ATTACKER EVIDENCE QUOTE: {f['evidence_quote']!r}\n"
                    f"DEFENSE NOTE: {f['resolution_note']!r}\n\n"
                    f"--- RAW CLAUSE TEXT ---\n{clause_text}\n--- END ---"
                )
                try:
                    out = parse_llm_json(
                        tracked_complete(llm, usage, JUDGE_SYSTEM_PROMPT, user, 800)
                    ) or {}
                except RuntimeError as exc:
                    errors.append(f"{f['id']}: {exc}")
                    out = {}
                v = str(out.get("verdict", "")).lower()
                # LLM proposes; deterministic gate decides: its quote must anchor.
                if v in ("confirmed", "rejected") and quote_exists(
                    str(out.get("quote", "")), clause_text
                ):
                    verdict = v

        if verdict == "confirmed":
            conn.execute(
                "UPDATE adversarial_findings SET status = 'confirmed', updated_at = now() "
                "WHERE id = %s",
                (f["id"],),
            )
            f["status"] = "confirmed"
            if emit_eval_case(conn, f):
                eval_cases_added += 1
            confirmed += 1
        elif verdict == "rejected":
            conn.execute(
                "UPDATE adversarial_findings SET status = 'rejected', resolution_note = %s, "
                "updated_at = now() WHERE id = %s",
                (canonical_claim({"action": "rejected_by_judge",
                                  "basis": "deterministic re-check / anchored quote"}), f["id"]),
            )
            rejected += 1
        else:
            pending += 1  # unresolved -> stays open (pending queue)
        conn.commit()

    report.update({
        "findings_examined": len(rows),
        "confirmed": confirmed,
        "rejected": rejected,
        "pending_unresolved": pending,
        "defense_rejections_overturned": reverted,
        "eval_cases_added": eval_cases_added,
        "llm_usage": usage,
        "llm_errors": errors,
    })
    return report


# ---------------------------------------------------------------------------
# Subcommand: closure
# ---------------------------------------------------------------------------


def cmd_closure(conn: psycopg.Connection, args: argparse.Namespace) -> dict:
    rows = conn.execute(
        "SELECT round, status, severity, count(*) FROM adversarial_findings "
        "GROUP BY round, status, severity ORDER BY round"
    ).fetchall()
    per_round: dict[int, dict] = {}
    by_severity: dict[str, int] = {}
    by_status: dict[str, int] = {}
    for round_no, status, severity, count in rows:
        bucket = per_round.setdefault(int(round_no), {"confirmed": 0, "open": 0, "total": 0})
        bucket["total"] += count
        if status in ("confirmed", "fixed"):
            bucket["confirmed"] += count
        if status == "open":
            bucket["open"] += count
        by_severity[severity] = by_severity.get(severity, 0) + count
        by_status[status] = by_status.get(status, 0) + count

    closure = compute_closure({r: {"confirmed": v["confirmed"], "open": v["open"]}
                               for r, v in per_round.items()})
    eval_count = conn.execute(
        "SELECT count(*) FROM eval_cases WHERE suite_name = %s", (EVAL_SUITE,)
    ).fetchone()[0]

    report = {
        "subcommand": "closure",
        **closure,
        "per_round": {str(k): v for k, v in sorted(per_round.items())},
        "findings_by_severity": by_severity,
        "findings_by_status": by_status,
        "eval_cases_added": eval_count,
    }
    out_path = args.report or "reports/adversarial_closure.json"
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(report, indent=2, default=str))
    report["report_path"] = out_path
    return report


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="subcommand", required=True)

    def common(p: argparse.ArgumentParser, round_required: bool = True) -> None:
        p.add_argument("--round", type=int, required=round_required, default=None,
                       help="round id tying this run's findings together (idempotent)")
        p.add_argument("--limit", type=int, default=0, help="cap items processed in this slice")
        p.add_argument("--report", default="", help="write the JSON report to this path")

    p = sub.add_parser("re-extract", help="blind re-extraction diff (re_extractor role)")
    common(p)
    p.add_argument("--source-version", required=True)

    p = sub.add_parser("prosecute", help="DB-only Q&A + raw-source verifier (prosecutor role)")
    common(p)

    p = sub.add_parser("gap-hunt", help="re-scrape manifest index URLs (gap_hunter role)")
    common(p)

    p = sub.add_parser("conflict-prosecute",
                       help="fact-pattern single-winner assertions (conflict_prosecutor role)")
    common(p)

    p = sub.add_parser("defend", help="fix-or-reject every open finding (defense role)")
    common(p, round_required=False)
    p.add_argument("--claimed-by", default="", help="lease owner id for the defense pool")

    p = sub.add_parser("judge", help="resolve defense-vs-attacker disputes; emit eval cases")
    common(p, round_required=False)

    p = sub.add_parser("closure", help="compute the stopping rule and write the closure report")
    common(p, round_required=False)
    return ap


HANDLERS = {
    "re-extract": cmd_reextract,
    "prosecute": cmd_prosecute,
    "gap-hunt": cmd_gap_hunt,
    "conflict-prosecute": cmd_conflict_prosecute,
    "defend": cmd_defend,
    "judge": cmd_judge,
    "closure": cmd_closure,
}


def main() -> int:
    args = build_parser().parse_args()
    with psycopg.connect(get_dsn()) as conn:
        report = HANDLERS[args.subcommand](conn, args)
    out = json.dumps(report, indent=2, default=str)
    if args.report and args.subcommand != "closure":
        os.makedirs(os.path.dirname(args.report) or ".", exist_ok=True)
        with open(args.report, "w", encoding="utf-8") as fh:
            fh.write(out)
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
