"""WA instrument precedence ruleset — code, not DB rows, not AI.

Implements CORPUS_COMPLETENESS_PLAN Phase 4b item 3 and MASTER_REBUILD_PLAN
§5.4 / §8.2: the Western Australian planning-instrument hierarchy is encoded
as a small, ordered, typed ruleset, each entry carrying its statutory
citation string.  The engine (or any caller) walks this ruleset over the
``legal_edges`` graph to pick a winning rule.  AI never picks a winner —
``resolve_precedence`` is a pure function with no DB, no LLM, no I/O.

Hierarchy encoded (highest first):

1. Deemed provisions (P&D (LPS) Regulations 2015 Sch 2) prevail over the
   scheme to the extent of inconsistency — no edge required.
2. Scheme amendment > local planning scheme (the amendment forms part of the
   scheme; later-in-time prevails).
3. Scheme (and scheme-family instruments) > local planning policy — an LPP
   must be consistent with the scheme and cannot bind or override it.
4. Scheme/structure-plan instruments displace R-Codes deemed-to-comply
   provisions ONLY where express (an approved ``overrides``/``modifies``/
   ``supersedes``/``repeals`` edge with a verbatim quote).  Bare hierarchy
   never silently beats the R-Codes.
5. LPP displaces R-Codes deemed-to-comply provisions ONLY where the scheme /
   the Codes empower it (an approved ``applies_with``/``modifies``/
   ``overrides`` edge evidencing the empowerment).
6. Everything statutory > guidance material.
7. An ``exception_to`` edge makes the exception rule take precedence over its
   base rule (the deterministic engine still evaluates the exception's
   ``condition_json`` against lot facts; this module only orders the rules).

Anything the ruleset cannot order with distinct surviving values resolves to
``needs_more_info`` with every candidate's citation attached — the system
never silently picks one of two contradictory legal sources (Phase 4b item 4).

NOTE (MASTER_REBUILD_PLAN §12): any numeric or legal values appearing in
docstrings or examples in this module are illustrative only.  Real values
come exclusively from approved, cited rule rows — never from code defaults.

Intended integration (kept standalone on purpose; the coordinator wires the
engine later)::

    from draftcheck.checks.precedence import (
        CandidateRule, Edge, InstrumentLevel, resolve_precedence,
    )

    candidates = [CandidateRule(...), ...]   # approved rules for one rule_key
    edges = [Edge(...), ...]                 # legal_edges rows (any granularity)
    resolution = resolve_precedence(candidates, edges)
    if resolution.status == "winner":
        ...use resolution.winner, record resolution.trace in precedence_trace
    else:  # "needs_more_info"
        ...surface every citation in resolution.surviving, never pick one
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from enum import IntEnum

# ---------------------------------------------------------------------------
# Instrument levels (rank: lower number = higher precedence)
# ---------------------------------------------------------------------------


class InstrumentLevel(IntEnum):
    """Ordered WA planning-instrument levels (MASTER_REBUILD_PLAN §8.2)."""

    DEEMED_PROVISIONS = 1
    SCHEME_AMENDMENT = 2
    SCHEME = 3
    STRUCTURE_PLAN_LDP = 4
    LOCAL_PLANNING_POLICY = 5
    RCODES_STATE_POLICY = 6
    GUIDANCE = 7


#: Map source_documents.source_type / target_manifest.category strings to levels.
SOURCE_TYPE_LEVELS: dict[str, InstrumentLevel] = {
    "deemed_provisions": InstrumentLevel.DEEMED_PROVISIONS,
    "lps_regulations": InstrumentLevel.DEEMED_PROVISIONS,
    "scheme_amendment": InstrumentLevel.SCHEME_AMENDMENT,
    "local_planning_scheme": InstrumentLevel.SCHEME,
    "scheme_map": InstrumentLevel.SCHEME,
    "region_scheme": InstrumentLevel.SCHEME,
    "structure_plan": InstrumentLevel.STRUCTURE_PLAN_LDP,
    "local_development_plan": InstrumentLevel.STRUCTURE_PLAN_LDP,
    "local_planning_policy": InstrumentLevel.LOCAL_PLANNING_POLICY,
    "local_planning_strategy": InstrumentLevel.GUIDANCE,
    "r_codes": InstrumentLevel.RCODES_STATE_POLICY,
    "state_planning_policy": InstrumentLevel.RCODES_STATE_POLICY,
    "spp": InstrumentLevel.RCODES_STATE_POLICY,
    "planning_guidance": InstrumentLevel.GUIDANCE,
    "practice_note": InstrumentLevel.GUIDANCE,
    "guidance": InstrumentLevel.GUIDANCE,
}


def instrument_level_for(source_type: str | None) -> InstrumentLevel:
    """Map a source_type/category string to its precedence level.

    Unknown types map to GUIDANCE (lowest statutory weight) so an unmapped
    instrument can never silently beat a mapped one.
    """
    if not source_type:
        return InstrumentLevel.GUIDANCE
    return SOURCE_TYPE_LEVELS.get(source_type.strip().lower(), InstrumentLevel.GUIDANCE)


# ---------------------------------------------------------------------------
# Closed phrase lists (deterministic validators — Phase 4b items 1 and 2)
# ---------------------------------------------------------------------------

#: Exception-language sweep phrases (mirrors the wp6_extract sweep).
EXCEPTION_PHRASES: tuple[str, ...] = (
    "notwithstanding",
    "despite",
    "except where",
    "except as",
    "unless",
    "other than where",
    "does not apply",
    "shall not apply",
)

#: Closed list of modification/exception language an edge evidence quote must
#: contain.  "No quote, no edge" — and a quote without one of these phrases is
#: not evidence of a cross-instrument relationship.
MODIFICATION_PHRASES: tuple[str, ...] = EXCEPTION_PHRASES + (
    "in lieu of",
    "instead of",
    "in place of",
    "prevail",
    "prevails",
    "overrides",
    "override",
    "supersedes",
    "supersede",
    "replaces",
    "replace",
    "varies",
    "vary",
    "varied by",
    "amends",
    "amend",
    "amended by",
    "modifies",
    "modify",
    "modified by",
    "subject to",
    "in accordance with",
    "read in conjunction with",
    "read as part of",
    "applies as if",
    "apply as if",
    "to the extent of any inconsistency",
    "to the extent of the inconsistency",
    "deemed-to-comply",
    "deemed to comply",
    "design principle",
    "is satisfied where",
    "in addition to",
    "depends on",
    "as defined in",
    "has the meaning given",
)

#: Relations the Phase 4b edge-proposal pass may produce.
EDGE_RELATIONS: tuple[str, ...] = (
    "modifies",
    "overrides",
    "exception_to",
    "applies_with",
    "performance_alternative_to",
    "depends_on",
)

#: Edge relations that express that the *from* rule displaces the *to* rule.
OVERRIDE_RELATIONS: frozenset[str] = frozenset({"overrides", "modifies", "supersedes", "repeals"})

#: Edge relations that evidence a scheme/Codes empowerment of an LPP.
EMPOWERMENT_RELATIONS: frozenset[str] = frozenset({"applies_with", "modifies", "overrides"})

#: legal_edges.review_status values that count when walking the graph.
APPROVED_EDGE_STATUSES: frozenset[str] = frozenset({"approved", "auto_accepted"})


@dataclass(frozen=True)
class QuoteValidation:
    """Outcome of the deterministic edge-quote validator."""

    ok: bool
    detail: str


def _whitespace_normalize(text: str) -> str:
    # Local copy of draftcheck.extraction.normalize.whitespace_normalize to
    # keep checks/ free of extraction imports; identical semantics.
    import re

    return re.sub(r"\s+", " ", text).strip()


def validate_edge_quote(quote: str | None, from_document_text: str) -> QuoteValidation:
    """Deterministic validator for a proposed legal edge's evidence quote.

    Accepts only when BOTH hold (Phase 4b item 2 — "No quote, no edge"):

    1. ``quote`` appears verbatim (whitespace-normalised, case-preserving) in
       ``from_document_text`` — the *from* document of the edge.
    2. ``quote`` contains at least one phrase from the closed
       ``MODIFICATION_PHRASES`` list (case-insensitive).
    """
    if not quote or not quote.strip():
        return QuoteValidation(False, "quote is empty — no quote, no edge")
    norm_quote = _whitespace_normalize(quote)
    if len(norm_quote) < 10:
        return QuoteValidation(False, f"quote too short ({len(norm_quote)} chars, minimum 10)")
    norm_doc = _whitespace_normalize(from_document_text)
    if norm_quote not in norm_doc:
        return QuoteValidation(
            False, "quote not found verbatim (whitespace-normalised) in the from-document"
        )
    low = norm_quote.lower()
    matched = [p for p in MODIFICATION_PHRASES if p in low]
    if not matched:
        return QuoteValidation(
            False, "quote contains no phrase from the closed modification/exception list"
        )
    return QuoteValidation(True, f"verbatim quote with modification language: {matched[:3]}")


# ---------------------------------------------------------------------------
# Candidate / edge inputs
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CandidateRule:
    """One approved rule row competing for a rule_key, plus its lineage refs.

    ``value_repr`` is an opaque identity for the rule's value (e.g.
    ``"gte:<value>:<unit>"`` built from operator/value_json/unit).  It is used
    only to detect agreement between survivors — never interpreted.
    """

    rule_id: str
    rule_key: str
    instrument_level: InstrumentLevel
    rule_type: str = "requirement"  # requirement | exception | definition | procedural_gate
    pathway: str = "none"
    value_repr: str | None = None
    citation: str | None = None
    clause_ref: str | None = None
    source_version_id: str | None = None

    def refs(self) -> frozenset[str]:
        """All graph refs this rule answers to (rule id, clause, source version)."""
        return frozenset(
            r for r in (self.rule_id, self.clause_ref, self.source_version_id) if r
        )


@dataclass(frozen=True)
class Edge:
    """One legal_edges row (refs are opaque strings, any granularity)."""

    from_ref: str
    to_ref: str
    relation: str
    review_status: str = "approved"
    from_type: str = "rule"
    to_type: str = "rule"
    evidence_quote: str | None = None


@dataclass(frozen=True)
class PrecedenceResolution:
    """Result of walking the ruleset.  ``status`` ∈ {"winner", "needs_more_info"}."""

    status: str
    winner: CandidateRule | None
    surviving: tuple[CandidateRule, ...]
    trace: tuple[dict, ...]
    reason: str

    @property
    def citations(self) -> tuple[str, ...]:
        return tuple(c.citation for c in self.surviving if c.citation)


# ---------------------------------------------------------------------------
# The ordered ruleset — each entry carries its statutory citation string
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PrecedenceEntry:
    """One typed entry in the ordered WA precedence ruleset.

    ``kind`` semantics (walked in order by :func:`resolve_precedence`):

    - ``exception_edge``      — exception rule with an approved exception_to
      edge to a base candidate takes precedence over that base.
    - ``unconditional_level`` — ``winner_level`` beats ``loser_level`` with no
      edge required.
    - ``express_edge_required`` — ``winner_level`` beats ``loser_level`` only
      when an approved edge in ``relations`` runs from the winner's lineage to
      the loser's lineage.
    - ``intra_level_express`` — within one level, an approved edge in
      ``relations`` between two candidates picks the from-side.
    """

    key: str
    kind: str
    citation: str
    description: str
    winner_level: InstrumentLevel | None = None
    loser_level: InstrumentLevel | None = None
    relations: tuple[str, ...] = ()


PRECEDENCE_RULESET: tuple[PrecedenceEntry, ...] = (
    PrecedenceEntry(
        key="exception_over_base",
        kind="exception_edge",
        citation=(
            "Interpretation Act 1984 (WA) s 8; generalia specialibus non derogant — "
            "a specific exception provision controls its base provision to the extent "
            "of its own terms."
        ),
        description=(
            "A rule_type=exception candidate with an approved exception_to edge to a "
            "base candidate takes precedence over that base rule.  The engine still "
            "evaluates the exception's condition_json against lot facts."
        ),
        relations=("exception_to",),
    ),
    PrecedenceEntry(
        key="deemed_provisions_prevail",
        kind="unconditional_level",
        citation=(
            "Planning and Development Act 2005 (WA) s 257B; Planning and Development "
            "(Local Planning Schemes) Regulations 2015 (WA) Sch 2 — the deemed "
            "provisions are read into every local planning scheme and prevail over "
            "scheme provisions to the extent of any inconsistency."
        ),
        description="Deemed provisions beat the scheme (and all lower levels).",
        winner_level=InstrumentLevel.DEEMED_PROVISIONS,
        loser_level=InstrumentLevel.GUIDANCE,  # beats everything down to here
    ),
    PrecedenceEntry(
        key="scheme_amendment_over_scheme",
        kind="unconditional_level",
        citation=(
            "Planning and Development Act 2005 (WA) Pt 5 Div 1 — an approved scheme "
            "amendment forms part of the scheme; the later amending provision prevails "
            "over the provision it amends."
        ),
        description="A gazetted scheme amendment beats the unamended scheme text.",
        winner_level=InstrumentLevel.SCHEME_AMENDMENT,
        loser_level=InstrumentLevel.SCHEME,
    ),
    PrecedenceEntry(
        key="scheme_over_structure_plan",
        kind="unconditional_level",
        citation=(
            "Planning and Development (Local Planning Schemes) Regulations 2015 (WA) "
            "Sch 2 Pt 4 — a structure plan / local development plan is given due "
            "regard but cannot override the scheme."
        ),
        description="Scheme-family text beats structure plans and LDPs.",
        winner_level=InstrumentLevel.SCHEME,
        loser_level=InstrumentLevel.STRUCTURE_PLAN_LDP,
    ),
    PrecedenceEntry(
        key="scheme_over_lpp",
        kind="unconditional_level",
        citation=(
            "Planning and Development (Local Planning Schemes) Regulations 2015 (WA) "
            "Sch 2 Pt 2 cl 3 — a local planning policy must be consistent with the "
            "scheme and cannot bind, vary or override scheme provisions."
        ),
        description="Scheme-family text beats local planning policies.",
        winner_level=InstrumentLevel.SCHEME,
        loser_level=InstrumentLevel.LOCAL_PLANNING_POLICY,
    ),
    PrecedenceEntry(
        key="structure_plan_over_lpp",
        kind="unconditional_level",
        citation=(
            "MASTER_REBUILD_PLAN §8.2 precedence order, reflecting Planning and "
            "Development (Local Planning Schemes) Regulations 2015 (WA) Sch 2 Pt 4 "
            "(structure plans / LDPs sit above local planning policies in the "
            "assessment hierarchy)."
        ),
        description="Structure plans / LDPs beat local planning policies.",
        winner_level=InstrumentLevel.STRUCTURE_PLAN_LDP,
        loser_level=InstrumentLevel.LOCAL_PLANNING_POLICY,
    ),
    PrecedenceEntry(
        key="scheme_amends_rcodes_only_where_express",
        kind="express_edge_required",
        citation=(
            "State Planning Policy 7.3 Residential Design Codes Volume 1 cl 1.2 — the "
            "Codes apply as if part of the scheme and may be amended or replaced by a "
            "scheme provision only as the Codes expressly provide, with WAPC approval. "
            "Without express words, the Codes' provision stands."
        ),
        description=(
            "Scheme-family text displaces an R-Codes / state-policy provision ONLY "
            "where an approved express overrides/modifies edge exists."
        ),
        winner_level=InstrumentLevel.SCHEME,
        loser_level=InstrumentLevel.RCODES_STATE_POLICY,
        relations=tuple(sorted(OVERRIDE_RELATIONS)),
    ),
    PrecedenceEntry(
        key="lpp_where_scheme_empowers",
        kind="express_edge_required",
        citation=(
            "State Planning Policy 7.3 Residential Design Codes Volume 1 cl 1.2.3 — a "
            "local planning policy may amend specified deemed-to-comply provisions "
            "only where the Codes expressly permit local variation and the policy is "
            "adopted under the scheme (P&D (LPS) Regulations 2015 Sch 2 Pt 2)."
        ),
        description=(
            "An LPP displaces an R-Codes deemed-to-comply provision ONLY where an "
            "approved empowerment edge (applies_with/modifies/overrides) exists."
        ),
        winner_level=InstrumentLevel.LOCAL_PLANNING_POLICY,
        loser_level=InstrumentLevel.RCODES_STATE_POLICY,
        relations=tuple(sorted(EMPOWERMENT_RELATIONS)),
    ),
    PrecedenceEntry(
        key="statutory_over_guidance",
        kind="unconditional_level",
        citation=(
            "Planning and Development Act 2005 (WA) s 77 and Planning and Development "
            "(Local Planning Schemes) Regulations 2015 (WA) Sch 2 cl 67 — guidance and "
            "practice material is given due regard only; it has no statutory force "
            "against scheme, policy or Codes provisions."
        ),
        description="Any statutory instrument beats non-statutory guidance material.",
        winner_level=InstrumentLevel.RCODES_STATE_POLICY,
        loser_level=InstrumentLevel.GUIDANCE,
    ),
    PrecedenceEntry(
        key="intra_level_express_relation",
        kind="intra_level_express",
        citation=(
            "Express words of modification within an instrument family — the provision "
            "that states it overrides/modifies another prevails to the extent of its "
            "express terms (ordinary principles of construction; Interpretation Act "
            "1984 (WA) s 8)."
        ),
        description=(
            "Within one instrument level, an approved overrides/modifies edge between "
            "two candidates picks the from-side."
        ),
        relations=tuple(sorted(OVERRIDE_RELATIONS)),
    ),
)


# ---------------------------------------------------------------------------
# Resolution — pure function, deterministic, no AI
# ---------------------------------------------------------------------------


@dataclass
class _State:
    candidates: list[CandidateRule]
    edges: list[Edge]
    trace: list[dict] = field(default_factory=list)


def _approved_edges(edges: Iterable[Edge]) -> list[Edge]:
    return [e for e in edges if e.review_status in APPROVED_EDGE_STATUSES]


def _edge_between(
    edges: Iterable[Edge],
    winner: CandidateRule,
    loser: CandidateRule,
    relations: Iterable[str],
) -> Edge | None:
    """Approved edge in ``relations`` from the winner's lineage to the loser's."""
    rels = set(relations)
    w_refs, l_refs = winner.refs(), loser.refs()
    for e in edges:
        if e.relation in rels and e.from_ref in w_refs and e.to_ref in l_refs:
            return e
    return None


def _eliminate(state: _State, loser: CandidateRule, entry: PrecedenceEntry, why: str) -> None:
    state.candidates = [c for c in state.candidates if c.rule_id != loser.rule_id]
    state.trace.append(
        {
            "entry": entry.key,
            "citation": entry.citation,
            "eliminated_rule_id": loser.rule_id,
            "detail": why,
        }
    )


def _apply_exception_edge(state: _State, entry: PrecedenceEntry, edges: list[Edge]) -> None:
    exceptions = [c for c in state.candidates if c.rule_type == "exception"]
    for exc in exceptions:
        for base in list(state.candidates):
            if base.rule_id == exc.rule_id:
                continue
            edge = _edge_between(edges, exc, base, entry.relations)
            if edge is not None:
                _eliminate(
                    state,
                    base,
                    entry,
                    f"exception rule {exc.rule_id} has approved exception_to edge to "
                    f"base rule {base.rule_id}; condition_json still gates the exception",
                )


def _apply_unconditional_level(state: _State, entry: PrecedenceEntry) -> None:
    assert entry.winner_level is not None and entry.loser_level is not None
    winners = [c for c in state.candidates if c.instrument_level == entry.winner_level]
    # deemed_provisions_prevail spans every lower level; the rest are one pair.
    if entry.winner_level == InstrumentLevel.DEEMED_PROVISIONS:
        losers = [
            c for c in state.candidates if c.instrument_level > InstrumentLevel.DEEMED_PROVISIONS
        ]
    elif entry.key == "statutory_over_guidance":
        winners = [c for c in state.candidates if c.instrument_level < InstrumentLevel.GUIDANCE]
        losers = [c for c in state.candidates if c.instrument_level == InstrumentLevel.GUIDANCE]
    else:
        # Scheme-family entries treat amendment/scheme alike on the winner side.
        if entry.winner_level == InstrumentLevel.SCHEME:
            winners = [
                c
                for c in state.candidates
                if c.instrument_level
                in (InstrumentLevel.SCHEME_AMENDMENT, InstrumentLevel.SCHEME)
            ]
        losers = [c for c in state.candidates if c.instrument_level == entry.loser_level]
    if not winners or not losers:
        return
    for loser in losers:
        _eliminate(
            state,
            loser,
            entry,
            f"{loser.instrument_level.name} candidate displaced by "
            f"{winners[0].instrument_level.name} without an express edge being required",
        )


def _apply_express_edge_required(state: _State, entry: PrecedenceEntry, edges: list[Edge]) -> None:
    assert entry.winner_level is not None and entry.loser_level is not None
    if entry.winner_level == InstrumentLevel.SCHEME:
        winner_levels = {
            InstrumentLevel.SCHEME_AMENDMENT,
            InstrumentLevel.SCHEME,
            InstrumentLevel.STRUCTURE_PLAN_LDP,
        }
    else:
        winner_levels = {entry.winner_level}
    winners = [c for c in state.candidates if c.instrument_level in winner_levels]
    losers = [c for c in state.candidates if c.instrument_level == entry.loser_level]
    for winner in winners:
        for loser in losers:
            if loser.rule_id not in {c.rule_id for c in state.candidates}:
                continue
            edge = _edge_between(edges, winner, loser, entry.relations)
            if edge is not None:
                _eliminate(
                    state,
                    loser,
                    entry,
                    f"express approved {edge.relation} edge from {winner.rule_id} "
                    f"({winner.instrument_level.name}) — quote-anchored displacement",
                )
            # No edge → both stay; resolve_precedence ends needs_more_info if
            # their values differ.  Bare hierarchy never beats the R-Codes.


def _apply_intra_level_express(state: _State, entry: PrecedenceEntry, edges: list[Edge]) -> None:
    for winner in list(state.candidates):
        for loser in list(state.candidates):
            if winner.rule_id == loser.rule_id:
                continue
            if winner.instrument_level != loser.instrument_level:
                continue
            if loser.rule_id not in {c.rule_id for c in state.candidates}:
                continue
            edge = _edge_between(edges, winner, loser, entry.relations)
            if edge is not None:
                _eliminate(
                    state,
                    loser,
                    entry,
                    f"approved {edge.relation} edge from {winner.rule_id} within "
                    f"{winner.instrument_level.name}",
                )


def resolve_precedence(
    candidate_rules: Sequence[CandidateRule],
    edges: Sequence[Edge],
) -> PrecedenceResolution:
    """Walk the ordered WA precedence ruleset over legal edges. Pure, no AI.

    Returns a :class:`PrecedenceResolution` whose ``status`` is ``"winner"``
    (exactly one rule survives, or every survivor agrees on ``value_repr``)
    or ``"needs_more_info"`` (zero candidates, or two-plus survivors with
    different values and no precedence path — both citations are surfaced and
    the system never silently picks one).
    """
    if not candidate_rules:
        return PrecedenceResolution(
            status="needs_more_info",
            winner=None,
            surviving=(),
            trace=(),
            reason="no candidate rules supplied",
        )

    state = _State(candidates=list(candidate_rules), edges=list(edges))
    approved = _approved_edges(state.edges)

    for entry in PRECEDENCE_RULESET:
        if len(state.candidates) <= 1:
            break
        if entry.kind == "exception_edge":
            _apply_exception_edge(state, entry, approved)
        elif entry.kind == "unconditional_level":
            _apply_unconditional_level(state, entry)
        elif entry.kind == "express_edge_required":
            _apply_express_edge_required(state, entry, approved)
        elif entry.kind == "intra_level_express":
            _apply_intra_level_express(state, entry, approved)

    survivors = tuple(sorted(state.candidates, key=lambda c: (c.instrument_level, c.rule_id)))
    trace = tuple(state.trace)

    if len(survivors) == 1:
        return PrecedenceResolution(
            status="winner",
            winner=survivors[0],
            surviving=survivors,
            trace=trace,
            reason="single candidate survives the precedence walk",
        )

    values = {c.value_repr for c in survivors}
    if len(values) == 1 and None not in values:
        # All survivors agree — no legal conflict; report the highest-ranked.
        return PrecedenceResolution(
            status="winner",
            winner=survivors[0],
            surviving=survivors,
            trace=trace,
            reason="all surviving candidates carry the same value; highest-ranked reported",
        )

    return PrecedenceResolution(
        status="needs_more_info",
        winner=None,
        surviving=survivors,
        trace=trace,
        reason=(
            "multiple candidates with differing values and no precedence path — "
            "surfacing every citation rather than silently picking one"
        ),
    )
