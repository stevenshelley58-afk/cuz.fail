from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from draftcheck_compliance.rule_validation import (
    APPROVED_RULE_STATUSES,
    has_normative_language,
    normalize_clause_disposition,
    normalize_unit,
    validate_rule_candidate_status,
    validate_rule_key,
    validate_rule_row_for_status,
)
from draftcheck_core.audit import record_audit
from draftcheck_core.json_utils import from_json, normalize_text, to_json, word_limited_quote
from draftcheck_core.models import (
    Clause,
    ClauseDisposition,
    RuleExtractionCandidate,
    RuleRow,
    SourceDocument,
    SourceLicenceReview,
    SourceVersion,
    utcnow,
)
from draftcheck_shared.schemas import (
    ClauseDispositionRead,
    ClauseDispositionReviewRequest,
    ClauseRead,
    RuleCandidatePromotionRequest,
    RuleCandidateReviewRequest,
    RuleExtractionCandidateRead,
    RuleExtractionRunResponse,
    RuleCoverageAuditItem,
    RuleCoverageAuditResponse,
    RuleCoverageStatus,
    RuleReviewRequest,
    RuleRowRead,
)


EXTRACTOR_NAME = "deterministic_rule_extractor"
EXTRACTOR_VERSION = "0.1"

_SENTENCE_SPLIT_PATTERN = re.compile(r"(?<=[.!?])\s+|\n+")
_VALUE_UNIT_PATTERN = re.compile(
    r"\b(?P<value>\d+(?:\.\d+)?)\s*"
    r"(?P<unit>m2|sqm|mm|m|metres?|meters?|%|percent|per\s+cent)(?=\b|[^a-zA-Z0-9_])",
    re.IGNORECASE,
)
_SETBACK_AFTER_LABEL_PATTERN = re.compile(
    r"\b(?:minimum|not\s+less\s+than|no\s+less\s+than|at\s+least)?\s*"
    r"(?:\w+\s+){0,3}(?:set\s+back|setback)s?\s*"
    r"(?:of|is|to|:|=|at\s+least|not\s+less\s+than|no\s+less\s+than|minimum)?\s*"
    r"(?P<value>\d+(?:\.\d+)?)\s*"
    r"(?P<unit>mm|m|metres?|meters?)(?=\b|[^a-zA-Z0-9_])",
    re.IGNORECASE,
)
_SETBACK_BEFORE_LABEL_PATTERN = re.compile(
    r"\b(?P<value>\d+(?:\.\d+)?)\s*"
    r"(?P<unit>mm|m|metres?|meters?)\s+"
    r"(?:minimum\s+)?(?:\w+\s+){0,3}(?:set\s+back|setback)s?\b",
    re.IGNORECASE,
)
_MINIMUM_TERMS = (
    "at least",
    "minimum",
    "not less than",
    "no less than",
)
_MAXIMUM_TERMS = (
    "maximum",
    "not exceed",
    "does not exceed",
    "must not exceed",
    "no more than",
    "up to",
)
_PROCEDURAL_TERMS = (
    "application",
    "drawing",
    "drawings",
    "include",
    "provide",
    "report",
    "shown",
    "site plan",
    "submit",
)
_DEFINITION_TERMS = (
    "means",
    "definition",
    "defined as",
)
ACTIVE_CANDIDATE_STATUSES = {"candidate", "pending_review"}


@dataclass(frozen=True)
class _CandidatePayload:
    rule_key: str
    operator: str
    value_json: str
    unit: str
    condition_text: str
    quote: str


class RuleGovernanceService:
    def __init__(self, db: Session):
        self.db = db

    def get_clause(self, clause_row_id: str) -> ClauseRead:
        clause = self.db.get(Clause, clause_row_id)
        if not clause:
            raise KeyError("Clause not found")
        return _clause_read(clause, _latest_dispositions_by_clause(self.db, [clause.id]).get(clause.id))

    def review_clause_disposition(
        self,
        clause_row_id: str,
        payload: ClauseDispositionReviewRequest,
    ) -> ClauseRead:
        clause = self.db.get(Clause, clause_row_id)
        if not clause:
            raise KeyError("Clause not found")
        disposition = normalize_clause_disposition(payload.disposition, clause.text)
        rationale = payload.rationale.strip()
        row = ClauseDisposition(
            clause_id=clause.id,
            disposition=disposition,
            rationale=rationale,
            reviewer=payload.reviewed_by,
        )
        self.db.add(row)
        self.db.flush()
        record_audit(
            self.db,
            action="clause.disposition_reviewed",
            target_type="clause",
            target_id=clause.id,
            metadata={
                "source_version_id": clause.source_version_id,
                "disposition_id": row.id,
                "disposition": disposition,
                "reviewed_by": payload.reviewed_by,
            },
        )
        self.db.flush()
        return _clause_read(clause, row)

    def extract_source_version_rules(
        self,
        source_version_id: str,
        *,
        source_document_id: str | None = None,
        extractor_name: str = EXTRACTOR_NAME,
        extractor_version: str = EXTRACTOR_VERSION,
    ) -> RuleExtractionRunResponse:
        version = self.db.get(SourceVersion, source_version_id)
        if not version:
            raise KeyError("Source version not found")
        if source_document_id and version.source_document_id != source_document_id:
            raise KeyError("Source version not found for source document")

        clauses = list(
            self.db.scalars(
                select(Clause)
                .where(Clause.source_version_id == source_version_id)
                .order_by(Clause.clause_id, Clause.created_at, Clause.id)
            )
        )
        dispositions_by_clause = _latest_dispositions_by_clause(self.db, [clause.id for clause in clauses])

        dispositions_created = 0
        candidates_created = 0
        candidates_existing = 0
        run_candidates: list[RuleExtractionCandidate] = []
        for clause in clauses:
            payloads = _candidate_payloads_for_clause(clause)
            if clause.id not in dispositions_by_clause:
                disposition = _disposition_for_clause(clause, payloads)
                self.db.add(
                    ClauseDisposition(
                        clause_id=clause.id,
                        disposition=disposition,
                        rationale=_disposition_rationale(disposition, payloads),
                        reviewer=extractor_name,
                    )
                )
                dispositions_created += 1

            for payload in payloads:
                existing = _existing_candidate(self.db, source_version_id, clause.id, payload)
                if existing:
                    candidates_existing += 1
                    run_candidates.append(existing)
                    continue

                candidate = RuleExtractionCandidate(
                    source_version_id=source_version_id,
                    clause_id=clause.id,
                    rule_key=payload.rule_key,
                    operator=payload.operator,
                    value_json=payload.value_json,
                    unit=payload.unit,
                    condition_text=payload.condition_text,
                    quote=payload.quote,
                    extractor_name=extractor_name,
                    extractor_version=extractor_version,
                    status="candidate",
                )
                self.db.add(candidate)
                self.db.flush()
                candidates_created += 1
                run_candidates.append(candidate)

        record_audit(
            self.db,
            action="rules.extracted",
            target_type="source_version",
            target_id=source_version_id,
            metadata={
                "source_document_id": version.source_document_id,
                "extractor_name": extractor_name,
                "extractor_version": extractor_version,
                "clauses_scanned": len(clauses),
                "dispositions_created": dispositions_created,
                "candidates_created": candidates_created,
                "candidates_existing": candidates_existing,
            },
        )
        self.db.flush()
        return RuleExtractionRunResponse(
            source_document_id=version.source_document_id,
            source_version_id=source_version_id,
            extractor_name=extractor_name,
            extractor_version=extractor_version,
            clauses_scanned=len(clauses),
            dispositions_created=dispositions_created,
            candidates_created=candidates_created,
            candidates_existing=candidates_existing,
            candidates=[_candidate_read(candidate) for candidate in run_candidates],
        )

    def list_rule_candidates(
        self,
        *,
        source_version_id: str | None = None,
        status: str | None = None,
    ) -> list[RuleExtractionCandidateRead]:
        stmt = select(RuleExtractionCandidate).order_by(
            RuleExtractionCandidate.source_version_id,
            RuleExtractionCandidate.rule_key,
            RuleExtractionCandidate.created_at,
            RuleExtractionCandidate.id,
        )
        if source_version_id:
            stmt = stmt.where(RuleExtractionCandidate.source_version_id == source_version_id)
        if status:
            status = validate_rule_candidate_status(status)
            stmt = stmt.where(RuleExtractionCandidate.status == status)
        return [_candidate_read(row) for row in self.db.scalars(stmt)]

    def review_rule_candidate(
        self,
        candidate_id: str,
        payload: RuleCandidateReviewRequest,
    ) -> RuleExtractionCandidateRead:
        candidate = self.db.get(RuleExtractionCandidate, candidate_id)
        if not candidate:
            raise KeyError("Rule extraction candidate not found")
        status = validate_rule_candidate_status(payload.status)
        candidate.status = status
        candidate.review_notes = _candidate_review_notes(payload)
        record_audit(
            self.db,
            action="rule_candidate.reviewed",
            target_type="rule_extraction_candidate",
            target_id=candidate.id,
            metadata={
                "status": status,
                "reviewed_by": payload.reviewed_by,
                "source_version_id": candidate.source_version_id,
            },
        )
        self.db.flush()
        return _candidate_read(candidate)

    def promote_rule_candidate(
        self,
        candidate_id: str,
        payload: RuleCandidatePromotionRequest,
    ) -> RuleRowRead:
        candidate = self.db.get(RuleExtractionCandidate, candidate_id)
        if not candidate:
            raise KeyError("Rule extraction candidate not found")
        if candidate.status == "rejected":
            raise ValueError("Rejected rule extraction candidates cannot be promoted")
        if not candidate.clause_id:
            raise ValueError("Rule extraction candidate requires clause_id provenance before promotion")

        clause = self.db.get(Clause, candidate.clause_id)
        if not clause or clause.source_version_id != candidate.source_version_id:
            raise ValueError("Rule extraction candidate clause/source provenance is invalid")
        version = self.db.get(SourceVersion, candidate.source_version_id)
        if not version or version.is_superseded or version.review_status == "rejected":
            raise ValueError("Rule extraction candidate source version is not current for promotion")
        if not candidate.quote.strip() or normalize_text(candidate.quote) not in normalize_text(clause.text):
            raise ValueError("Rule extraction candidate quote must appear verbatim in its source clause")

        validate_rule_key(candidate.rule_key)
        unit = normalize_unit(candidate.unit)
        existing = _existing_rule_row_for_candidate(self.db, candidate)
        if existing:
            rule_row = existing
        else:
            rule_row = RuleRow(
                rule_key=candidate.rule_key,
                operator=candidate.operator,
                value_json=candidate.value_json,
                unit=unit,
                condition_text=candidate.condition_text,
                quote=candidate.quote,
                clause_id=candidate.clause_id,
                source_version_id=candidate.source_version_id,
                lifecycle_status="pending_review",
            )
            self.db.add(rule_row)
            self.db.flush()

        candidate.status = "pending_review"
        candidate.review_notes = _promotion_notes(rule_row.id, payload)
        record_audit(
            self.db,
            action="rule_candidate.promoted",
            target_type="rule_extraction_candidate",
            target_id=candidate.id,
            metadata={
                "rule_row_id": rule_row.id,
                "source_version_id": candidate.source_version_id,
                "reviewed_by": payload.reviewed_by,
            },
        )
        self.db.flush()
        return _rule_row_read(rule_row)

    def list_rule_rows(
        self,
        *,
        source_version_id: str | None = None,
        lifecycle_status: str | None = None,
    ) -> list[RuleRowRead]:
        stmt = select(RuleRow).order_by(RuleRow.rule_key, RuleRow.created_at)
        if source_version_id:
            stmt = stmt.where(RuleRow.source_version_id == source_version_id)
        if lifecycle_status:
            stmt = stmt.where(RuleRow.lifecycle_status == lifecycle_status)
        return [_rule_row_read(row) for row in self.db.scalars(stmt)]

    def coverage_audit(
        self,
        *,
        source_version_id: str | None = None,
        include_superseded: bool = False,
        only_gaps: bool = True,
        summary_only: bool = False,
    ) -> RuleCoverageAuditResponse:
        stmt = (
            select(
                Clause,
                SourceVersion.id,
                SourceVersion.version_label,
                SourceVersion.effective_date,
                SourceVersion.is_superseded,
                SourceDocument.id,
                SourceDocument.title,
            )
            .join(SourceVersion, Clause.source_version_id == SourceVersion.id)
            .join(SourceDocument, SourceVersion.source_document_id == SourceDocument.id)
            .order_by(SourceDocument.title, SourceVersion.effective_date, Clause.clause_id)
        )
        if source_version_id:
            stmt = stmt.where(Clause.source_version_id == source_version_id)
        if not include_superseded:
            stmt = stmt.where(SourceVersion.is_superseded.is_(False))

        clause_rows = self.db.execute(stmt).all()
        clause_ids = [row[0].id for row in clause_rows]
        dispositions_by_clause = _latest_dispositions_by_clause(self.db, clause_ids)
        rule_rows_by_clause = _rule_rows_by_clause(self.db, clause_ids)
        candidates_by_clause = _candidates_by_clause(self.db, clause_ids)

        items: list[RuleCoverageAuditItem] = []
        summary: Counter[str] = Counter()
        total_clauses = len(clause_rows)
        for (
            clause,
            version_id,
            version_label,
            effective_date,
            is_superseded,
            source_id,
            source_title,
        ) in clause_rows:
            disposition = dispositions_by_clause.get(clause.id)
            rule_rows = rule_rows_by_clause[clause.id]
            candidates = candidates_by_clause[clause.id]
            active_candidates = [row for row in candidates if row.status in ACTIVE_CANDIDATE_STATUSES]
            active_rule_rows = [
                row
                for row in rule_rows
                if row.lifecycle_status in APPROVED_RULE_STATUSES and row.source_version_id == version_id
            ]
            normative_language_detected = has_normative_language(clause.text)
            status = _coverage_status(
                normative_language_detected=normative_language_detected,
                disposition=disposition.disposition if disposition else None,
                active_rule_count=len(active_rule_rows),
                rule_row_count=len(rule_rows),
                candidate_count=len(active_candidates),
            )
            summary[status] += 1
            if summary_only or (only_gaps and status in {"covered", "not_rule_bearing"}):
                continue
            items.append(
                RuleCoverageAuditItem(
                    source_document_id=source_id,
                    source_title=source_title,
                    source_version_id=version_id,
                    version_label=version_label,
                    effective_date=effective_date,
                    is_superseded=is_superseded,
                    clause_row_id=clause.id,
                    clause_id=clause.clause_id,
                    heading=clause.heading,
                    quote=word_limited_quote(clause.text, 60),
                    normative_language_detected=normative_language_detected,
                    disposition=disposition.disposition if disposition else None,
                    disposition_id=disposition.id if disposition else None,
                    rule_row_ids=[row.id for row in rule_rows],
                    active_rule_row_ids=[row.id for row in active_rule_rows],
                    rule_lifecycle_statuses=dict(Counter(row.lifecycle_status for row in rule_rows)),
                    rule_candidate_ids=[
                        row.id for row in (active_candidates if active_candidates else candidates)
                    ],
                    rule_candidate_statuses=dict(Counter(row.status for row in candidates)),
                    status=status,
                    review_required=status != "covered" and status != "not_rule_bearing",
                    recommended_action=_recommended_action(status),
                )
            )

        return RuleCoverageAuditResponse(
            source_version_id=source_version_id,
            include_superseded=include_superseded,
            only_gaps=only_gaps,
            total_clauses=total_clauses,
            gap_count=sum(count for status, count in summary.items() if status not in {"covered", "not_rule_bearing"}),
            summary=dict(summary),
            items=items,
        )

    def review_rule_row(self, rule_row_id: str, payload: RuleReviewRequest) -> RuleRowRead:
        rule_row = self.db.get(RuleRow, rule_row_id)
        if not rule_row:
            raise KeyError("Rule row not found")
        lifecycle_status = validate_rule_row_for_status(
            lifecycle_status=payload.lifecycle_status,
            quote=rule_row.quote,
            clause_id=rule_row.clause_id,
            source_version_id=rule_row.source_version_id,
        )
        if lifecycle_status in APPROVED_RULE_STATUSES and not _source_version_allows_rule_approval(
            self.db,
            rule_row.source_version_id,
        ):
            raise ValueError("Approved RuleRow requires a current source version with approved licence review")
        if lifecycle_status in APPROVED_RULE_STATUSES and not _rule_quote_matches_clause(self.db, rule_row):
            raise ValueError("Approved RuleRow quote must appear verbatim in its source clause")
        rule_row.lifecycle_status = lifecycle_status
        if lifecycle_status in {"auto_accepted", "approved"}:
            rule_row.approved_by = payload.reviewed_by
            rule_row.approved_at = utcnow()
        elif lifecycle_status in {"pending_review", "rejected", "stale", "superseded"}:
            rule_row.approved_by = None
            rule_row.approved_at = None
        record_audit(
            self.db,
            action="rule_row.reviewed",
            target_type="rule_row",
            target_id=rule_row.id,
            metadata={"lifecycle_status": lifecycle_status, "reviewed_by": payload.reviewed_by},
        )
        self.db.flush()
        return _rule_row_read(rule_row)


def _latest_dispositions_by_clause(db: Session, clause_ids: list[str]) -> dict[str, ClauseDisposition]:
    if not clause_ids:
        return {}
    rows = db.scalars(
        select(ClauseDisposition)
        .where(ClauseDisposition.clause_id.in_(clause_ids))
        .order_by(ClauseDisposition.created_at, ClauseDisposition.id)
    ).all()
    by_clause: dict[str, ClauseDisposition] = {}
    for row in rows:
        by_clause[row.clause_id] = row
    return by_clause


def _rule_rows_by_clause(db: Session, clause_ids: list[str]) -> dict[str, list[RuleRow]]:
    by_clause: dict[str, list[RuleRow]] = defaultdict(list)
    if not clause_ids:
        return by_clause
    rows = db.scalars(
        select(RuleRow).where(RuleRow.clause_id.in_(clause_ids)).order_by(RuleRow.created_at, RuleRow.id)
    ).all()
    for row in rows:
        by_clause[row.clause_id].append(row)
    return by_clause


def _candidates_by_clause(db: Session, clause_ids: list[str]) -> dict[str, list[RuleExtractionCandidate]]:
    by_clause: dict[str, list[RuleExtractionCandidate]] = defaultdict(list)
    if not clause_ids:
        return by_clause
    rows = db.scalars(
        select(RuleExtractionCandidate)
        .where(RuleExtractionCandidate.clause_id.in_(clause_ids))
        .order_by(RuleExtractionCandidate.created_at, RuleExtractionCandidate.id)
    ).all()
    for row in rows:
        if row.clause_id:
            by_clause[row.clause_id].append(row)
    return by_clause


def _source_version_allows_rule_approval(db: Session, source_version_id: str) -> bool:
    version = db.get(SourceVersion, source_version_id)
    if not version or version.review_status == "rejected" or version.is_superseded:
        return False
    approved_licence = db.scalar(
        select(SourceLicenceReview).where(
            SourceLicenceReview.source_version_id == source_version_id,
            SourceLicenceReview.review_status == "approved",
            SourceLicenceReview.allowed_storage.is_(True),
            SourceLicenceReview.allowed_ai_processing.is_(True),
        )
    )
    return approved_licence is not None


def _rule_quote_matches_clause(db: Session, rule_row: RuleRow) -> bool:
    clause = db.get(Clause, rule_row.clause_id)
    if not clause or clause.source_version_id != rule_row.source_version_id:
        return False
    quote = normalize_text(rule_row.quote)
    return bool(quote and quote in normalize_text(clause.text))


def _coverage_status(
    *,
    normative_language_detected: bool,
    disposition: str | None,
    active_rule_count: int,
    rule_row_count: int,
    candidate_count: int,
) -> RuleCoverageStatus:
    requires_rule_support = normative_language_detected or disposition == "rule_bearing"
    if not requires_rule_support:
        return "not_rule_bearing"
    if active_rule_count:
        return "covered"
    if disposition in {"definition", "procedural"}:
        return "not_rule_bearing"
    if disposition == "manual_review":
        return "needs_manual_review"
    if normative_language_detected and disposition not in {"rule_bearing", "manual_review"}:
        return "needs_clause_disposition"
    if rule_row_count:
        return "rule_not_approved"
    if candidate_count:
        return "candidate_not_promoted"
    return "missing_rule_row"


def _recommended_action(status: RuleCoverageStatus) -> str:
    return {
        "covered": "No coverage action required.",
        "not_rule_bearing": "No rule row required unless a reviewer reclassifies the clause.",
        "needs_clause_disposition": "Review the clause disposition; normative language cannot be left unsupported.",
        "needs_manual_review": "Human reviewer must decide whether the clause needs a deterministic rule row.",
        "candidate_not_promoted": "Promote, reject, or revise the extraction candidate during rule review.",
        "rule_not_approved": "Review existing rule rows and approve only quote-anchored, source-versioned rules.",
        "missing_rule_row": "Create a source-cited rule row or record a manual-review disposition.",
    }[status]


def _candidate_payloads_for_clause(clause: Clause) -> list[_CandidatePayload]:
    payloads: list[_CandidatePayload] = []
    seen: set[tuple[str, str, str, str]] = set()
    for sentence in _candidate_sentences(clause.text):
        payload = _candidate_payload_from_sentence(sentence, clause)
        if not payload:
            continue
        key = (payload.rule_key, payload.operator, payload.value_json, payload.quote)
        if key in seen:
            continue
        seen.add(key)
        payloads.append(payload)
    return payloads


def _candidate_sentences(text: str) -> list[str]:
    sentences = [sentence.strip(" \t\r\n-;") for sentence in _SENTENCE_SPLIT_PATTERN.split(text)]
    return [sentence for sentence in sentences if sentence]


def _candidate_payload_from_sentence(sentence: str, clause: Clause) -> _CandidatePayload | None:
    lowered = sentence.lower()
    value_match = _first_numeric_value(sentence)
    if not value_match:
        return None
    value, unit = value_match
    text_context = f"{clause.heading or ''} {sentence}".lower()
    condition_text = _condition_text(sentence)

    if "site cover" in text_context and unit == "percent" and _has_any(lowered, _MAXIMUM_TERMS):
        return _payload(
            rule_key="site_cover",
            operator="<=",
            value={"max_percent": value},
            unit=unit,
            condition_text=condition_text,
            quote=sentence,
        )
    if "open space" in text_context and unit == "percent" and _has_any(lowered, _MINIMUM_TERMS):
        return _payload(
            rule_key="open_space",
            operator=">=",
            value={"min_percent": value},
            unit=unit,
            condition_text=condition_text,
            quote=sentence,
        )
    if _mentions_setback(text_context) and unit == "m":
        if _is_nonoperative_setback_context(sentence, clause):
            return None
        setback_value = _setback_numeric_value(sentence)
        if not setback_value:
            return None
        value, unit = setback_value
        return _payload(
            rule_key=_setback_rule_key(f"{text_context} {clause.text}".lower()),
            operator=">=",
            value={"min_value": value},
            unit=unit,
            condition_text=condition_text,
            quote=sentence,
        )
    return None


def _setback_numeric_value(sentence: str) -> tuple[float, str] | None:
    for pattern in (_SETBACK_AFTER_LABEL_PATTERN, _SETBACK_BEFORE_LABEL_PATTERN):
        match = pattern.search(sentence)
        if match:
            return _numeric_value_from_match(match)
    return None


def _payload(
    *,
    rule_key: str,
    operator: str,
    value: dict[str, float],
    unit: str,
    condition_text: str,
    quote: str,
) -> _CandidatePayload:
    return _CandidatePayload(
        rule_key=validate_rule_key(rule_key),
        operator=operator,
        value_json=to_json(value),
        unit=normalize_unit(unit) or unit,
        condition_text=condition_text,
        quote=quote.strip(),
    )


def _first_numeric_value(sentence: str) -> tuple[float, str] | None:
    for match in _VALUE_UNIT_PATTERN.finditer(sentence):
        return _numeric_value_from_match(match)
    return None


def _numeric_value_from_match(match: re.Match[str]) -> tuple[float, str]:
    raw_unit = match.group("unit").lower().replace(" ", "_")
    value = float(match.group("value"))
    if raw_unit == "mm":
        return value / 1000, "m"
    if raw_unit in {"m", "metre", "metres", "meter", "meters"}:
        return value, "m"
    if raw_unit in {"%", "percent", "per_cent"}:
        return value, "percent"
    if raw_unit in {"m2", "sqm"}:
        return value, "m2"
    return value, raw_unit


def _condition_text(sentence: str) -> str:
    match = re.search(r"\b(unless|except|where|if)\b.+$", sentence, flags=re.IGNORECASE)
    return match.group(0).strip(" .;") if match else ""


def _mentions_setback(text: str) -> bool:
    return "setback" in text or "set back" in text


def _is_nonoperative_setback_context(sentence: str, clause: Clause) -> bool:
    lowered_sentence = sentence.lower()
    lowered_clause = f"{clause.heading or ''} {clause.text}".lower()
    if any(
        term in lowered_sentence
        for term in (
            "intent of introducing",
            "method of calculating",
            "not deemed-to-comply",
            "not deemed to comply",
        )
    ):
        return True
    return bool(
        "average side setback" in lowered_clause
        and "total length" in lowered_clause
        and re.search(r"\b\d+(?:\.\d+)?\s*m\s*x\s*\d", lowered_clause)
    )


def _setback_rule_key(text: str) -> str:
    if "front" in text or "primary street" in text:
        return "front_setback"
    if "side" in text:
        return "side_setback"
    if "rear" in text:
        return "rear_setback"
    if "street" in text and "wall" not in text:
        return "front_setback"
    return "wall_setback"


def _has_any(value: str, terms: tuple[str, ...]) -> bool:
    return any(term in value for term in terms)


def _is_procedural_clause(text: str) -> bool:
    if not _has_any(text, _PROCEDURAL_TERMS):
        return False
    if _has_any(text, ("application", "drawing", "drawings", "document", "documents", "report", "site plan", "submit")):
        return True
    return bool(
        re.search(r"\b(?:must|shall|required)\s+(?:include|provide|show|submit)\b", text)
        and _has_any(text, ("plan", "plans", "detail", "details", "schedule", "form"))
    )


def _disposition_for_clause(clause: Clause, payloads: list[_CandidatePayload]) -> str:
    if payloads:
        return normalize_clause_disposition("rule_bearing", clause.text)
    text = f"{clause.heading or ''} {clause.text}".lower()
    if _has_any(text, _DEFINITION_TERMS):
        return normalize_clause_disposition("definition", clause.text)
    if _is_procedural_clause(text):
        return normalize_clause_disposition("procedural", clause.text)
    if has_normative_language(clause.text):
        return normalize_clause_disposition("manual_review", clause.text)
    return normalize_clause_disposition("informational", clause.text)


def _disposition_rationale(disposition: str, payloads: list[_CandidatePayload]) -> str:
    if disposition == "rule_bearing":
        return f"Deterministic extraction found {len(payloads)} numeric rule candidate(s)."
    if disposition == "definition":
        return "Deterministic extraction classified the clause as definitional text."
    if disposition == "procedural":
        return "Deterministic extraction classified the clause as procedural/documentation text."
    if disposition == "manual_review":
        return "Normative language was found, but no deterministic numeric rule candidate was extracted."
    return "No normative rule language was found by deterministic extraction."


def _existing_candidate(
    db: Session,
    source_version_id: str,
    clause_id: str,
    payload: _CandidatePayload,
) -> RuleExtractionCandidate | None:
    return db.scalar(
        select(RuleExtractionCandidate).where(
            RuleExtractionCandidate.source_version_id == source_version_id,
            RuleExtractionCandidate.clause_id == clause_id,
            RuleExtractionCandidate.rule_key == payload.rule_key,
            RuleExtractionCandidate.operator == payload.operator,
            RuleExtractionCandidate.value_json == payload.value_json,
            RuleExtractionCandidate.unit == payload.unit,
            RuleExtractionCandidate.quote == payload.quote,
        )
    )


def _existing_rule_row_for_candidate(
    db: Session,
    candidate: RuleExtractionCandidate,
) -> RuleRow | None:
    if not candidate.clause_id:
        return None
    return db.scalar(
        select(RuleRow).where(
            RuleRow.source_version_id == candidate.source_version_id,
            RuleRow.clause_id == candidate.clause_id,
            RuleRow.rule_key == candidate.rule_key,
            RuleRow.operator == candidate.operator,
            RuleRow.value_json == candidate.value_json,
            RuleRow.unit == normalize_unit(candidate.unit),
            RuleRow.quote == candidate.quote,
        )
    )


def _promotion_notes(rule_row_id: str, payload: RuleCandidatePromotionRequest) -> str:
    suffix = f" {payload.notes.strip()}" if payload.notes.strip() else ""
    return f"Promoted to RuleRow {rule_row_id}; awaiting rule review.{suffix}".strip()


def _candidate_review_notes(payload: RuleCandidateReviewRequest) -> str:
    suffix = f" {payload.notes.strip()}" if payload.notes.strip() else ""
    return f"Reviewed by {payload.reviewed_by}; status set to {payload.status}.{suffix}".strip()


def _clause_read(clause: Clause, disposition: ClauseDisposition | None) -> ClauseRead:
    return ClauseRead(
        id=clause.id,
        source_version_id=clause.source_version_id,
        clause_id=clause.clause_id,
        heading=clause.heading,
        parent_clause_id=clause.parent_clause_id,
        page_number=clause.page_number,
        text=clause.text,
        start_anchor=clause.start_anchor,
        end_anchor=clause.end_anchor,
        text_sha256=clause.text_sha256,
        latest_disposition=_clause_disposition_read(disposition) if disposition else None,
    )


def _clause_disposition_read(row: ClauseDisposition) -> ClauseDispositionRead:
    return ClauseDispositionRead(
        id=row.id,
        clause_id=row.clause_id,
        disposition=row.disposition,
        rationale=row.rationale,
        reviewer=row.reviewer,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _candidate_read(row: RuleExtractionCandidate) -> RuleExtractionCandidateRead:
    return RuleExtractionCandidateRead(
        id=row.id,
        source_version_id=row.source_version_id,
        clause_id=row.clause_id,
        rule_key=row.rule_key,
        operator=row.operator,
        value=from_json(row.value_json, {}),
        unit=row.unit,
        condition_text=row.condition_text,
        quote=row.quote,
        extractor_name=row.extractor_name,
        extractor_version=row.extractor_version,
        status=row.status,
        review_notes=row.review_notes,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _rule_row_read(row: RuleRow) -> RuleRowRead:
    return RuleRowRead(
        id=row.id,
        rule_key=row.rule_key,
        operator=row.operator,
        value=from_json(row.value_json, {}),
        unit=row.unit,
        condition_text=row.condition_text,
        quote=row.quote,
        clause_id=row.clause_id,
        source_version_id=row.source_version_id,
        lifecycle_status=row.lifecycle_status,
        approved_by=row.approved_by,
        approved_at=row.approved_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )
