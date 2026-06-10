"""Deterministic citation / cross-reference extractor — CORPUS_COMPLETENESS_PLAN Phase 3.

Pure functions over clause or chunk text. No database access and strictly NO LLM:
the citation-closure loop (scripts/wp5_citation_closure.py) must be reproducible
and cheap enough to re-run in CI on every merge.

Public surface:

- ``extract_references(text)`` -> list[Reference] — every cross-reference found,
  with raw span, char offsets, a normalized instrument-key guess, and clause path.
  References whose ``instrument_key`` is None are *internal* (e.g. "Schedule 4"
  with no instrument named) and create no cross-document edge.
- ``normalize_instrument_key(text)`` — the one normalization both sides of
  resolution must use ("the R-Codes" / "R-Codes " / "R-CODES" -> "r-codes").
- ``candidate_keys(key)`` — deterministic variants tried during resolution
  ("spp 2" <-> "spp 2.0", "tps 3" -> "town planning scheme no 3", ...).
- ``build_alias_map(pairs)`` / ``resolve_key(key, alias_map)`` — pure resolution
  helpers reused by the closure script against instrument_aliases + target_manifest.
- ``classify_out_of_scope(key, context)`` — closed-list classifier mirroring the
  "Out of scope" section of docs/CORPUS_SCOPE.md.

The pattern table (``PATTERNS``) is data-driven: add a ``PatternSpec`` row to
cover a new citation form. Composite patterns ("clause X of <instrument>") defer
the instrument-key guess to the non-composite patterns via ``_key_for_phrase``.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass

__all__ = [
    "LPS_REGS_KEY",
    "OUT_OF_SCOPE_CATEGORIES",
    "PATTERNS",
    "PD_ACT_KEY",
    "PatternSpec",
    "Reference",
    "build_alias_map",
    "candidate_keys",
    "classify_out_of_scope",
    "default_category",
    "extract_references",
    "normalize_instrument_key",
    "out_of_scope_note",
    "resolve_key",
]

# Canonical normalized keys for the context-dependent shorthand forms. In this
# corpus (WA planning instruments, pilot LGA City of Cockburn) "the Act" is the
# Planning and Development Act 2005 and "the Regulations" are the LPS Regulations
# 2015; "the Scheme" resolves via the prod alias "the Scheme" -> Cockburn TPS3.
PD_ACT_KEY = "planning and development act 2005"
LPS_REGS_KEY = "planning and development local planning schemes regulations 2015"

_VOL_WORD_TO_DIGIT = {"one": "1", "two": "2", "three": "3", "1": "1", "2": "2", "3": "3"}
_VOL_DIGIT_TO_WORD = {"1": "one", "2": "two", "3": "three", "one": "one", "two": "two", "three": "three"}

_DASH_TRANSLATION = dict.fromkeys(map(ord, "‐‑‒–—―"), "-")


def normalize_instrument_key(text: str) -> str:
    """Normalize an instrument name/alias/citation for matching.

    Lowercase; unify dashes; drop punctuation except decimal points, '/', '&' and
    intra-word hyphens; collapse whitespace; strip a leading article. Idempotent.
    """
    t = text.translate(_DASH_TRANSLATION).lower()
    t = re.sub(r"[‘’']", "", t)
    t = re.sub(r"(?<!\d)\.(?!\d)|(?<=\d)\.(?!\d)", " ", t)  # keep dots only between digits
    t = re.sub(r"[^a-z0-9./&\- ]+", " ", t)
    t = re.sub(r"\s+-\s+", " ", t)  # " - " separators; intra-word hyphens (r-codes) survive
    t = re.sub(r"\s+", " ", t).strip(" -")
    t = re.sub(r"^(?:the|this|that|these) ", "", t)
    return t


# ---------------------------------------------------------------------------
# Reference + pattern table
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Reference:
    """One extracted cross-reference.

    ``instrument_key`` is the normalized instrument guess (None = internal/self
    reference, e.g. a bare "Schedule 4"). ``instrument_text`` is the raw
    instrument phrase only (without any "clause X of" prefix). ``raw`` equals
    ``text[start:end]`` of the input.
    """

    raw: str
    start: int
    end: int
    pattern: str
    instrument_key: str | None
    instrument_text: str
    clause_path: str | None = None

    @property
    def internal(self) -> bool:
        return self.instrument_key is None


# (instrument_key, instrument_text, clause_path, trimmed_absolute_end | None)
# Composite builders trim the match end back to the leftmost instrument inside
# the captured phrase, so "clause 5.1.2 of the R-Codes and AS 3959" leaves
# "AS 3959" outside the composite span (and it survives dedup as its own ref).
_Built = tuple[str | None, str, str | None, int | None]


@dataclass(frozen=True)
class PatternSpec:
    name: str
    regex: re.Pattern[str]
    build: Callable[[re.Match[str]], _Built]
    composite: bool = False  # composite specs delegate key guessing to _key_for_phrase


# Instrument noun-phrase grammar used by the composite patterns: capitalized /
# parenthesized / numeric tokens, optionally chained through lowercase joiners.
# Joiners are only valid when followed by another token, so trailing "and"/"of"
# are never captured. "the" is deliberately NOT a joiner: a mid-phrase article
# almost always marks the boundary between two instruments ("the Metropolitan
# Region Scheme and the Planning and Development Act 2005" is two citations).
_TOKEN = r"(?:\(?[A-Z][\w'&)\-]*\)?|\d+(?:\.\d+)?)"
_JOINER = r"(?:and|of|for|in|to|No\.?)"
_PHRASE_CORE = rf"{_TOKEN}(?:\s+(?:{_JOINER}\s+)*{_TOKEN})*"
_PHRASE = rf"(?:(?:[Tt]he|[Tt]his|[Tt]hat)\s+)?(?:deemed\s+provisions|{_PHRASE_CORE})"

_CLAUSE_NUM = r"\d+[A-Za-z]?(?:\(\d+[A-Za-z]?\))*(?:\.\d+[A-Za-z]?)*"


def _build_clause_of(m: re.Match[str]) -> _Built:
    phrase = m.group("inst")
    key, end_in_phrase = _instrument_match(phrase)
    return key, phrase[:end_in_phrase], m.group("clause"), m.start("inst") + end_in_phrase


def _build_schedule(m: re.Match[str]) -> _Built:
    phrase = m.group("inst")
    if not phrase:
        return None, m.group(0), f"Schedule {m.group('sched')}", None
    key, end_in_phrase = _instrument_match(phrase)
    return (
        key,
        phrase[:end_in_phrase],
        f"Schedule {m.group('sched')}",
        m.start("inst") + end_in_phrase,
    )


def _build_spp(m: re.Match[str]) -> _Built:
    return f"spp {m.group('sppn')}", m.group(0), None, None


def _build_r_codes(m: re.Match[str]) -> _Built:
    raw = m.group(0)
    base = "residential design codes" if raw.startswith("Residential") else "r-codes"
    vol = m.group("rcvol")
    if m.group("apts"):
        vol = "2"
    if vol:
        return f"{base} volume {_VOL_WORD_TO_DIGIT.get(vol.lower(), vol)}", raw, None, None
    return base, raw, None, None


def _build_deemed(m: re.Match[str]) -> _Built:
    return "deemed provisions", m.group(0), None, None


def _build_lps_regs(m: re.Match[str]) -> _Built:
    return LPS_REGS_KEY, m.group(0), None, None


def _build_pd_act(m: re.Match[str]) -> _Built:
    return PD_ACT_KEY, m.group(0), None, None


def _build_ncc(m: re.Match[str]) -> _Built:
    raw = m.group(0)
    vol = m.group("nccvol")
    if vol:
        return f"ncc volume {_VOL_DIGIT_TO_WORD[vol.lower()]}", raw, None, None
    if raw.startswith("National"):
        return "national construction code", raw, None, None
    if raw.startswith("Building"):
        return "building code of australia", raw, None, None
    if raw.startswith("BCA"):
        return "bca", raw, None, None
    return "ncc", raw, None, None


def _build_as(m: re.Match[str]) -> _Built:
    if m.group("asnzs"):
        return f"as/nzs {m.group('asnzs')}", m.group(0), None, None
    return f"as {m.group('asnum')}", m.group(0), None, None


_REGION_ABBREV = {
    "mrs": "metropolitan region scheme",
    "prs": "peel region scheme",
    "gbrs": "greater bunbury region scheme",
}


def _build_region(m: re.Match[str]) -> _Built:
    norm = normalize_instrument_key(m.group(0))
    return _REGION_ABBREV.get(norm, norm), m.group(0), None, None


def _build_tps(m: re.Match[str]) -> _Built:
    if m.group("tpsabbr"):
        return f"tps {m.group('tpsabbr')}", m.group(0), None, None
    return normalize_instrument_key(m.group(0)), m.group(0), None, None


def _build_lpp_numbered(m: re.Match[str]) -> _Built:
    return f"lpp {m.group('lppn')}", m.group(0), None, None


def _build_normalized(m: re.Match[str]) -> _Built:
    return normalize_instrument_key(m.group(0)), m.group(0), None, None


def _build_the_scheme(m: re.Match[str]) -> _Built:
    return "scheme", m.group(0), None, None


def _build_the_act(m: re.Match[str]) -> _Built:
    return PD_ACT_KEY, m.group(0), None, None


def _build_the_regulations(m: re.Match[str]) -> _Built:
    return LPS_REGS_KEY, m.group(0), None, None


PATTERNS: tuple[PatternSpec, ...] = (
    PatternSpec(
        "clause_of_instrument",
        re.compile(rf"\b[Cc]lauses?\s+(?P<clause>{_CLAUSE_NUM})\s+of\s+(?P<inst>{_PHRASE})"),
        _build_clause_of,
        composite=True,
    ),
    PatternSpec(
        "schedule_reference",
        re.compile(
            rf"\b[Ss]chedules?\s+(?P<sched>\d+[A-Za-z]?)\b"
            rf"(?:\s+(?:of|to)\s+(?P<inst>{_PHRASE}))?"
        ),
        _build_schedule,
        composite=True,
    ),
    PatternSpec(
        "lps_regulations",
        re.compile(
            r"\bPlanning\s+and\s+Development\s+\(Local\s+Planning\s+Schemes\)\s+"
            r"Regulations(?:\s+2015)?\b"
        ),
        _build_lps_regs,
    ),
    PatternSpec(
        "pd_act",
        re.compile(r"\bPlanning\s+and\s+Development\s+Act(?:\s+2005)?\b|\bP&D\s+Act\b"),
        _build_pd_act,
    ),
    PatternSpec(
        "spp",
        re.compile(
            r"\b(?:State\s+Planning\s+Policy|SPP)\s*(?:No\.?\s*)?(?P<sppn>\d+(?:\.\d+)?)\b"
        ),
        _build_spp,
    ),
    PatternSpec(
        "r_codes",
        re.compile(
            r"\b(?:R[-\s]?Codes|Residential\s+Design\s+Codes)\b"
            r"(?:\s*[-–—]?\s*(?:Volumes?\s+(?P<rcvol>1|2|One|Two)\b"
            r"|\(?(?P<apts>Apartments)\)?))?"
        ),
        _build_r_codes,
    ),
    PatternSpec(
        "deemed_provisions",
        re.compile(r"\bdeemed\s+provisions\b", re.IGNORECASE),
        _build_deemed,
    ),
    PatternSpec(
        "bushfire_guidelines",
        re.compile(r"\bGuidelines\s+for\s+Planning\s+in\s+Bushfire[\s-]Prone\s+Areas\b"),
        _build_normalized,
    ),
    PatternSpec(
        "ncc",
        re.compile(
            r"\b(?:NCC|National\s+Construction\s+Code|Building\s+Code\s+of\s+Australia|BCA)\b"
            r"(?:\s+Volumes?\s+(?P<nccvol>One|Two|Three|1|2|3)\b)?"
        ),
        _build_ncc,
    ),
    PatternSpec(
        "as_standard",
        re.compile(
            r"\bAS\s*/\s*NZS\s*(?P<asnzs>\d{3,5}(?:\.\d+)?)(?::\d{4})?"
            r"|\bAS\s*(?P<asnum>\d{3,5}(?:\.\d+)?)(?::\d{4})?\b"
        ),
        _build_as,
    ),
    PatternSpec(
        "region_scheme",
        re.compile(
            r"\b(?:Metropolitan\s+Region\s+Scheme|Peel\s+Region\s+Scheme"
            r"|Greater\s+Bunbury\s+Region\s+Scheme|MRS|PRS|GBRS)\b"
        ),
        _build_region,
    ),
    PatternSpec(
        "tps",
        re.compile(
            r"\b(?:(?:City|Town|Shire)\s+of\s+[A-Z][\w\-]*\s+)?"
            r"(?:Town|Local|District)\s+Planning\s+Scheme\s+No\.?\s*\d+\b"
            r"|\bTPS\s*(?:No\.?\s*)?(?P<tpsabbr>\d+)\b"
        ),
        _build_tps,
    ),
    PatternSpec(
        "lpp_numbered",
        re.compile(
            r"\b(?:Local\s+Planning\s+Policy|LPP)\s*(?:No\.?\s*)?(?P<lppn>\d+(?:\.\d+)?)\b"
        ),
        _build_lpp_numbered,
    ),
    PatternSpec(
        "lpp_named",
        re.compile(rf"\bLocal\s+Planning\s+Policy\s+{_PHRASE_CORE}"),
        _build_normalized,
    ),
    PatternSpec(
        "act_or_regulations_named",
        re.compile(
            rf"\b(?:{_PHRASE_CORE})\s+(?:Act|Regulations)\s+(?:19|20)\d{{2}}\b"
        ),
        _build_normalized,
    ),
    PatternSpec(
        "the_scheme",
        re.compile(r"\b(?:[Tt]he|[Tt]his)\s+Scheme\b"),
        _build_the_scheme,
    ),
    PatternSpec(
        "the_act",
        re.compile(r"\b(?:[Tt]he|[Tt]his)\s+Act\b(?!\s+(?:19|20)\d{2})"),
        _build_the_act,
    ),
    PatternSpec(
        "the_regulations",
        re.compile(r"\b(?:[Tt]he|[Tt]hese)\s+Regulations\b(?!\s+(?:19|20)\d{2})"),
        _build_the_regulations,
    ),
)

_INTERNAL_PHRASE_RE = re.compile(r"(?:(?:the|this|that)\s+)?schedules?\s+\d+[a-z]?$", re.IGNORECASE)


def _instrument_match(phrase: str) -> tuple[str | None, int]:
    """(instrument key, end offset within the phrase) for a composite pattern.

    Runs the non-composite specs over the phrase and keeps the leftmost match
    (widest on ties): the instrument directly follows "of", and anything after
    it ("... of the R-Codes and AS 3959") is a different citation that must stay
    outside the composite span. Falls back to plain normalization of the whole
    phrase. Key is None for internal targets ("clause 67(2) of Schedule 2"
    cites the same document).
    """
    if _INTERNAL_PHRASE_RE.fullmatch(phrase.strip()):
        return None, len(phrase)
    best_rank: tuple[int, int, int] | None = None  # (start, -end, priority)
    best_match: re.Match[str] | None = None
    best_spec: PatternSpec | None = None
    for prio, spec in enumerate(PATTERNS):
        if spec.composite:
            continue
        m = spec.regex.search(phrase)
        if not m:
            continue
        rank = (m.start(), -m.end(), prio)
        if best_rank is None or rank < best_rank:
            best_rank, best_match, best_spec = rank, m, spec
    if best_match is not None and best_spec is not None:
        key = best_spec.build(best_match)[0]
        return (normalize_instrument_key(key) if key else None), best_match.end()
    return (normalize_instrument_key(phrase) or None), len(phrase)


def extract_references(text: str) -> list[Reference]:
    """Extract every cross-reference from clause/chunk text, deduplicated.

    A match fully contained in (or equal to) a wider match is dropped, so
    "clause 5.1.2 of the R-Codes" yields one composite reference, not two.
    """
    candidates: list[tuple[int, int, int, Reference]] = []
    for prio, spec in enumerate(PATTERNS):
        for m in spec.regex.finditer(text):
            key, inst_text, clause_path, trimmed_end = spec.build(m)
            if key is not None:
                key = normalize_instrument_key(key) or None
            end = trimmed_end if trimmed_end is not None else m.end()
            ref = Reference(
                raw=text[m.start():end],
                start=m.start(),
                end=end,
                pattern=spec.name,
                instrument_key=key,
                instrument_text=re.sub(r"\s+", " ", inst_text).strip(),
                clause_path=clause_path,
            )
            candidates.append((m.start(), end, prio, ref))

    kept: list[Reference] = []
    spans: list[tuple[int, int]] = []
    for s, e, _prio, ref in sorted(candidates, key=lambda t: (-(t[1] - t[0]), t[2], t[0])):
        if any(s >= ks and e <= ke for ks, ke in spans):
            continue
        spans.append((s, e))
        kept.append(ref)
    kept.sort(key=lambda r: r.start)
    return kept


# ---------------------------------------------------------------------------
# Resolution helpers (pure; the closure script feeds them DB rows)
# ---------------------------------------------------------------------------


def candidate_keys(key: str) -> list[str]:
    """Deterministic variants of a normalized key to try against the alias map."""
    out: list[str] = []

    def add(k: str) -> None:
        if k and k not in out:
            out.append(k)

    add(key)
    m = re.fullmatch(r"spp (\d+)", key)
    if m:
        add(f"spp {m.group(1)}.0")
    m = re.fullmatch(r"spp (\d+)\.0", key)
    if m:
        add(f"spp {m.group(1)}")
    m = re.match(r"state planning policy (?:no )?(\d+(?:\.\d+)?)\b", key)
    if m:
        add(f"spp {m.group(1)}")
    if key.startswith("r-codes"):
        add("residential design codes" + key[len("r-codes"):])
    if key.startswith("residential design codes"):
        add("r-codes" + key[len("residential design codes"):])
    if key.startswith("as/nzs "):
        add("as " + key[len("as/nzs "):])
    m = re.fullmatch(r"ncc volume (one|two|three|1|2|3)", key)
    if m:
        vol = m.group(1)
        add(f"ncc volume {_VOL_DIGIT_TO_WORD.get(vol, vol)}")
        add(f"ncc volume {_VOL_WORD_TO_DIGIT.get(vol, vol)}")
    m = re.fullmatch(r"tps (\d+)", key)
    if m:
        add(f"tps{m.group(1)}")
        add(f"town planning scheme no {m.group(1)}")
    m = re.match(r"(?:city|town|shire) of [a-z\-]+ (.+)", key)
    if m:
        add(m.group(1))
    m = re.match(r"local planning policy (?:no )?(\d+(?:\.\d+)?)\b", key)
    if m:
        add(f"lpp {m.group(1)}")
    return out


def build_alias_map(pairs: Iterable[tuple[str, str]]) -> dict[str, str]:
    """Normalize (alias_text -> target_id) pairs into a resolution map.

    First mapping for a normalized alias wins, so feed canonical instrument
    names before looser aliases if both exist.
    """
    out: dict[str, str] = {}
    for alias_text, target in pairs:
        norm = normalize_instrument_key(alias_text)
        if norm:
            out.setdefault(norm, target)
    return out


def resolve_key(instrument_key: str, alias_map: dict[str, str]) -> str | None:
    """Resolve a normalized instrument key against an alias map, trying variants."""
    for cand in candidate_keys(instrument_key):
        hit = alias_map.get(cand)
        if hit is not None:
            return hit
    return None


# ---------------------------------------------------------------------------
# Out-of-scope classification — closed list from docs/CORPUS_SCOPE.md
# ---------------------------------------------------------------------------

# Ordered: first matching category wins (non_pilot_lga before other_jurisdiction
# so "Town of Victoria Park" is an LGA, not the state of Victoria). Patterns run
# against *normalized* text.
OUT_OF_SCOPE_CATEGORIES: tuple[tuple[str, re.Pattern[str], str], ...] = (
    (
        "non_pilot_lga",
        re.compile(r"\b(?:city|town|shire) of (?!cockburn\b)[a-z]"),
        "Non-pilot LGA local instrument — out of scope until the pilot list expands "
        "per MASTER_REBUILD_PLAN phases (docs/CORPUS_SCOPE.md).",
    ),
    (
        "strata_titles",
        re.compile(r"\bstrata titles?\b|\bstrata schemes?\b"),
        "Strata Titles Act / strata schemes — tenure, not a drafting-check input "
        "(docs/CORPUS_SCOPE.md).",
    ),
    (
        "building_act_process",
        re.compile(r"\bbuilding act\b|\bbuilding regulations 2012\b|\bbuilding services\b"),
        "Building Act 2011 / building permit process law — process, not design-rule "
        "content; the NCC carries the technical rules we check (docs/CORPUS_SCOPE.md).",
    ),
    (
        "environmental_protection",
        re.compile(
            r"\benvironmental protection act\b|\bepa bulletin\b|\bepbc\b"
            r"|\benvironment protection and biodiversity\b"
        ),
        "Environmental Protection Act / EPA bulletins — assessment process beyond "
        "residential drafting checks (docs/CORPUS_SCOPE.md).",
    ),
    (
        "aboriginal_cultural_heritage",
        re.compile(r"\baboriginal (?:cultural )?heritage act\b"),
        "Aboriginal Cultural Heritage Act — site clearance process, not lot-level "
        "design rules; heritage mapping stays in scope as a spatial layer "
        "(docs/CORPUS_SCOPE.md).",
    ),
    (
        "draft_instrument",
        re.compile(r"^draft\b|\bdraft (?:state planning policy|local planning|scheme|amendment)\b"),
        "Draft/advertised (not yet approved) instrument — only instruments in force "
        "are answer sources (docs/CORPUS_SCOPE.md).",
    ),
    (
        "superseded_version",
        re.compile(r"\bsuperseded\b|\brepealed\b"),
        "Superseded instrument version (docs/CORPUS_SCOPE.md).",
    ),
    (
        "other_jurisdiction",
        re.compile(
            r"\bnew south wales\b|\bnsw\b|\bqueensland\b|\bsouth australia\b"
            r"|\btasmania\b|\bnorthern territory\b|\bcommonwealth\b"
        ),
        "Other states' planning law / Commonwealth law (except NCC) — WA product "
        "(docs/CORPUS_SCOPE.md).",
    ),
)


def classify_out_of_scope(instrument_key: str, context: str = "") -> str | None:
    """Return the out-of-scope category name, or None if not in the closed list.

    ``context`` should be the instrument phrase only (never a surrounding quote —
    an in-scope citation next to out-of-scope words must not be misclassified).
    """
    haystacks = [normalize_instrument_key(instrument_key)]
    if context:
        haystacks.append(normalize_instrument_key(context))
    for name, rx, _note in OUT_OF_SCOPE_CATEGORIES:
        if any(rx.search(h) for h in haystacks):
            return name
    return None


def out_of_scope_note(category: str) -> str:
    for name, _rx, note in OUT_OF_SCOPE_CATEGORIES:
        if name == category:
            return note
    raise KeyError(category)


# ---------------------------------------------------------------------------
# target_manifest category guess per pattern (free-form String(120) column)
# ---------------------------------------------------------------------------

CATEGORY_BY_PATTERN: dict[str, str] = {
    "spp": "state_planning_policy",
    "r_codes": "state_planning_policy",
    "bushfire_guidelines": "state_planning_policy",
    "as_standard": "standard",
    "ncc": "building_code",
    "lpp_numbered": "local_planning_policy",
    "lpp_named": "local_planning_policy",
    "tps": "local_planning_scheme",
    "the_scheme": "local_planning_scheme",
    "region_scheme": "region_scheme",
    "pd_act": "act",
    "the_act": "act",
    "lps_regulations": "regulations",
    "the_regulations": "regulations",
    "deemed_provisions": "regulations",
}


def default_category(pattern: str, key: str | None) -> str:
    """Best-effort target_manifest.category for a reference (pattern, key)."""
    cat = CATEGORY_BY_PATTERN.get(pattern)
    if cat:
        return cat
    k = key or ""
    if "regulations" in k:
        return "regulations"
    if re.search(r"\bact (?:19|20)\d\d\b", k) or k.endswith(" act"):
        return "act"
    if k.startswith(("spp", "r-codes", "residential design codes")) or "state planning policy" in k:
        return "state_planning_policy"
    if k.startswith(("lpp", "local planning policy")):
        return "local_planning_policy"
    if k.startswith(("as ", "as/nzs")):
        return "standard"
    if "scheme" in k:
        return "local_planning_scheme"
    return "uncategorised"
