"""Family-aware ensemble adjudication for WP6 rule extraction.

Why this exists: the original WP6 adjudicator voted on the FULL atom
signature — (rule_key, operator, value, unit, density_codes, pathway,
dwelling_type). Two models that agreed perfectly on the number but phrased
applicability metadata differently never reached consensus, so validator-
passing extractions piled up in pending_review (1,220 of them in the first
full-corpus run) while only 62 rules were approved.

This module votes on the deterministic CORE only:

    core = (rule_key, operator, round(value, 4), unit)

and merges applicability metadata conservatively AFTER the core wins:

- pathway must agree across all votes (deemed-to-comply vs design-principle
  changes engine semantics) — disagreement blocks promotion;
- density codes are intersected; an empty intersection blocks promotion;
  votes that omitted codes never widen the result;
- dwelling_type: a specific type narrows "any"; two different specific
  types block promotion.

A core is promotable only when at least two DISTINCT MODEL FAMILIES
(e.g. minimax vs openai) produced a validator-passing atom with that core.
Two passes of the same model at temperature 0 are one vote, not two — this
was the second defect in the original design (passes 1+2 were both MiniMax,
so "2/3 majority" was nearly always MiniMax agreeing with itself).

Pure functions only: no DB access, no LLM calls. Shared by
scripts/wp6_extract.py (live extraction) and scripts/wp6_adjudicate.py
(re-adjudication of stored candidates).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

PROMOTE = "promote"
PENDING = "pending"

# Pending reasons (stable strings — recorded in candidate metadata and reports)
REASON_NO_VOTES = "no_votes"
REASON_SINGLE_FAMILY = "single_model_family"
REASON_PATHWAY = "pathway_disagreement"
REASON_DENSITY = "density_code_disagreement"
REASON_DWELLING = "dwelling_type_disagreement"


@dataclass(frozen=True)
class Vote:
    """One validator-passing extraction atom, reduced to what adjudication needs."""

    rule_key: str
    rule_type: str
    pathway: str
    operator: str
    value: float
    unit: str | None
    density_codes: tuple[str, ...]
    dwelling_type: str  # "any" when unspecified
    model: str  # e.g. "minimax:MiniMax-M2" or "openai:gpt-4o:challenge"
    ref: str = ""  # candidate id / trace ref


@dataclass(frozen=True)
class Decision:
    outcome: str  # PROMOTE | PENDING
    reason: str  # "" for promote, pending reason otherwise
    confidence: float
    pathway: str = "none"
    rule_type: str = "standard"
    density_codes: tuple[str, ...] = ()
    dwelling_type: str = "any"
    dissent: tuple[str, ...] = field(default=())
    families: tuple[str, ...] = field(default=())


def model_family(model: str) -> str:
    """'openai:gpt-4o:challenge' -> 'openai'. Family = independence unit."""
    return (model or "").split(":", 1)[0].strip().lower()


def core_of(vote: Vote) -> tuple:
    return (vote.rule_key, vote.operator, round(float(vote.value), 4), vote.unit)


def group_by_core(votes: Sequence[Vote]) -> dict[tuple, list[Vote]]:
    groups: dict[tuple, list[Vote]] = {}
    for v in votes:
        groups.setdefault(core_of(v), []).append(v)
    return groups


def adjudicate(votes: Sequence[Vote]) -> Decision:
    """Decide one core group. All votes MUST share the same core signature."""
    votes = list(votes)
    if not votes:
        return Decision(PENDING, REASON_NO_VOTES, 0.0)

    families = sorted({model_family(v.model) for v in votes})
    if len(families) < 2:
        return Decision(PENDING, REASON_SINGLE_FAMILY, 0.0, families=tuple(families))

    dissent: list[str] = []

    # Pathway: engine semantics — must agree.
    pathways = {v.pathway for v in votes}
    if len(pathways) > 1:
        return Decision(PENDING, REASON_PATHWAY, 0.0, families=tuple(families))
    pathway = votes[0].pathway

    # rule_type: informational relative to pathway — take majority, record mix.
    type_counts: dict[str, int] = {}
    for v in votes:
        type_counts[v.rule_type] = type_counts.get(v.rule_type, 0) + 1
    rule_type = sorted(type_counts.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
    if len(type_counts) > 1:
        dissent.append("rule_type_mixed")

    # Density codes: conservative intersection of the explicit sets.
    explicit = [frozenset(v.density_codes) for v in votes if v.density_codes]
    if explicit:
        merged_codes = explicit[0]
        for s in explicit[1:]:
            merged_codes = merged_codes & s
        if not merged_codes:
            return Decision(PENDING, REASON_DENSITY, 0.0, families=tuple(families))
        if len(set(explicit)) > 1:
            dissent.append("density_codes_narrowed")
        if len(explicit) < len(votes):
            dissent.append("density_codes_partial")
        density_codes = tuple(sorted(merged_codes))
    else:
        density_codes = ()

    # Dwelling type: specific narrows "any"; two different specifics disagree.
    specifics = {v.dwelling_type for v in votes if v.dwelling_type and v.dwelling_type != "any"}
    if len(specifics) > 1:
        return Decision(PENDING, REASON_DWELLING, 0.0, families=tuple(families))
    dwelling_type = next(iter(specifics)) if specifics else "any"
    if specifics and any((v.dwelling_type or "any") == "any" for v in votes):
        dissent.append("dwelling_type_narrowed")

    confidence = 0.95 if len(votes) >= 3 else 0.9
    if dissent:
        confidence = min(confidence, 0.9) - 0.05

    return Decision(
        PROMOTE,
        "",
        round(confidence, 2),
        pathway=pathway,
        rule_type=rule_type,
        density_codes=density_codes,
        dwelling_type=dwelling_type,
        dissent=tuple(sorted(set(dissent))),
        families=tuple(families),
    )
