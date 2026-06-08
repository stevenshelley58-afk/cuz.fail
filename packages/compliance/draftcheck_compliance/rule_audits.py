from __future__ import annotations

from collections import Counter, defaultdict
import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from draftcheck_compliance.rule_validation import has_normative_language
from draftcheck_core.json_utils import normalize_text, word_limited_quote
from draftcheck_core.models import Clause, ClauseDisposition, RuleCarveout, RuleExtractionCandidate, RuleRow
from draftcheck_shared.schemas import NoOrphanAuditItem, NoOrphanAuditResponse, NoOrphanAuditStatus


EXCEPTION_LANGUAGE_PATTERN = re.compile(
    r"\b(unless|except|exception|may be approved|deemed[- ]to[- ]comply|does not apply|"
    r"notwithstanding|despite)\b",
    re.IGNORECASE,
)
NUMERIC_REQUIREMENT_PATTERN = re.compile(
    r"\b\d+(?:\.\d+)?\s*(?:m|mm|metres?|meters?|%|percent|m2|sqm)\b",
    re.IGNORECASE,
)
APPROVED_RULE_STATUSES = {"approved", "auto_accepted"}
PENDING_CANDIDATE_STATUSES = {"candidate", "pending_review"}
PENDING_RULE_STATUSES = {"pending_review"}


class RuleAuditService:
    def __init__(self, db: Session):
        self.db = db

    def no_orphan_audit(
        self, *, source_version_id: str | None = None, summary_only: bool = False
    ) -> NoOrphanAuditResponse:
        stmt = select(Clause).order_by(Clause.source_version_id, Clause.clause_id)
        if source_version_id:
            stmt = stmt.where(Clause.source_version_id == source_version_id)
        clauses = list(self.db.scalars(stmt))
        clause_ids = [clause.id for clause in clauses]
        dispositions_by_clause = self._latest_dispositions_by_clause(clause_ids)
        rule_rows_by_clause = self._rule_rows_by_clause(clause_ids)
        candidates_by_clause = self._candidates_by_clause(clause_ids)
        carveouts_by_clause = self._carveouts_by_clause(clause_ids)

        items: list[NoOrphanAuditItem] = []
        summary: Counter[str] = Counter()
        blocking_count = 0
        for clause in clauses:
            disposition = dispositions_by_clause.get(clause.id)
            clause_items: list[NoOrphanAuditItem] = []
            clause_issue_count = 0
            rule_rows = rule_rows_by_clause[clause.id]
            candidates = candidates_by_clause[clause.id]
            carveouts = carveouts_by_clause[clause.id]

            def add_clause_item(
                *,
                status: NoOrphanAuditStatus,
                reason: str,
                evidence: dict[str, object],
                recommended_action: str,
            ) -> None:
                nonlocal blocking_count, clause_issue_count
                blocking_count += 1
                clause_issue_count += 1
                summary[status] += 1
                if not summary_only:
                    clause_items.append(
                        _audit_item(
                            clause,
                            status=status,
                            reason=reason,
                            evidence=evidence,
                            recommended_action=recommended_action,
                        )
                    )

            if not disposition:
                add_clause_item(
                    status="missing_disposition",
                    reason="Clause has no ClauseDisposition.",
                    evidence={},
                    recommended_action="Disposition the clause before accepting this source version.",
                )
            elif disposition.disposition == "informational" and has_normative_language(clause.text):
                add_clause_item(
                    status="invalid_informational_normative",
                    reason="Normative or exception language cannot be dispositioned as informational.",
                    evidence={"disposition_id": disposition.id, "disposition": disposition.disposition},
                    recommended_action="Reclassify the clause as rule_bearing, procedural, definition, or manual_review.",
                )
            exception_terms = _exception_terms(clause.text)
            if exception_terms and not _exception_language_represented(
                clause,
                rule_rows,
                carveouts,
            ):
                add_clause_item(
                    status="exception_language_orphan",
                    reason="Exception or carveout language is not represented by a rule condition or carveout.",
                    evidence={"terms": sorted(exception_terms)},
                    recommended_action="Add a source-cited RuleRow.condition_text or RuleCarveout for the exception.",
                )
            pending_candidates = [
                row.id
                for row in candidates
                if row.status in PENDING_CANDIDATE_STATUSES and not _candidate_has_matching_rule_row(row, rule_rows)
            ]
            pending_rules = [row.id for row in rule_rows if row.lifecycle_status in PENDING_RULE_STATUSES]
            if pending_candidates or pending_rules:
                add_clause_item(
                    status="pending_rule_review",
                    reason="Rule extraction candidates or rule rows are still pending review.",
                    evidence={"rule_candidate_ids": pending_candidates, "rule_row_ids": pending_rules},
                    recommended_action="Promote, approve, reject, or document the pending rule work.",
                )
            mismatched_rule_ids = [row.id for row in rule_rows if row.lifecycle_status in APPROVED_RULE_STATUSES and not _quote_matches_clause(row, clause)]
            if mismatched_rule_ids:
                add_clause_item(
                    status="quote_anchor_mismatch",
                    reason="Approved rule quote is not anchored verbatim in the clause text.",
                    evidence={"rule_row_ids": mismatched_rule_ids},
                    recommended_action="Correct the rule quote or reject the rule row before source acceptance.",
                )
            unclaimed_numbers = (
                _unclaimed_numeric_tokens(clause, rule_rows, carveouts)
                if _numeric_tokens_require_rule_support(clause, disposition)
                else []
            )
            if unclaimed_numbers:
                add_clause_item(
                    status="unclaimed_numeric_token",
                    reason="Measurement-like numeric tokens are not claimed by approved rules or carveouts.",
                    evidence={"tokens": unclaimed_numbers},
                    recommended_action="Claim each threshold in an approved rule quote/condition or document why it is non-normative.",
                )

            if not clause_issue_count:
                summary["ok"] += 1
            else:
                items.extend(clause_items)

        return NoOrphanAuditResponse(
            source_version_id=source_version_id,
            total_clauses=len(clauses),
            blocking_count=blocking_count,
            summary=dict(summary),
            items=items,
        )

    def _latest_dispositions_by_clause(self, clause_ids: list[str]) -> dict[str, ClauseDisposition]:
        if not clause_ids:
            return {}
        rows = self.db.scalars(
            select(ClauseDisposition)
            .where(ClauseDisposition.clause_id.in_(clause_ids))
            .order_by(ClauseDisposition.created_at, ClauseDisposition.id)
        ).all()
        by_clause: dict[str, ClauseDisposition] = {}
        for row in rows:
            by_clause[row.clause_id] = row
        return by_clause

    def _rule_rows_by_clause(self, clause_ids: list[str]) -> dict[str, list[RuleRow]]:
        by_clause: dict[str, list[RuleRow]] = defaultdict(list)
        if not clause_ids:
            return by_clause
        rows = self.db.scalars(
            select(RuleRow)
            .where(RuleRow.clause_id.in_(clause_ids))
            .order_by(RuleRow.created_at, RuleRow.id)
        ).all()
        for row in rows:
            by_clause[row.clause_id].append(row)
        return by_clause

    def _carveouts_by_clause(self, clause_ids: list[str]) -> dict[str, list[RuleCarveout]]:
        by_clause: dict[str, list[RuleCarveout]] = defaultdict(list)
        if not clause_ids:
            return by_clause
        rows = self.db.scalars(
            select(RuleCarveout)
            .where(RuleCarveout.clause_id.in_(clause_ids))
            .order_by(RuleCarveout.created_at, RuleCarveout.id)
        ).all()
        for row in rows:
            if row.clause_id:
                by_clause[row.clause_id].append(row)
        return by_clause

    def _candidates_by_clause(self, clause_ids: list[str]) -> dict[str, list[RuleExtractionCandidate]]:
        by_clause: dict[str, list[RuleExtractionCandidate]] = defaultdict(list)
        if not clause_ids:
            return by_clause
        rows = self.db.scalars(
            select(RuleExtractionCandidate)
            .where(RuleExtractionCandidate.clause_id.in_(clause_ids))
            .order_by(RuleExtractionCandidate.created_at, RuleExtractionCandidate.id)
        ).all()
        for row in rows:
            if row.clause_id:
                by_clause[row.clause_id].append(row)
        return by_clause


def _audit_item(
    clause: Clause,
    *,
    status: NoOrphanAuditStatus,
    reason: str,
    evidence: dict[str, object],
    recommended_action: str,
) -> NoOrphanAuditItem:
    return NoOrphanAuditItem(
        source_version_id=clause.source_version_id,
        clause_row_id=clause.id,
        clause_id=clause.clause_id,
        heading=clause.heading,
        quote=word_limited_quote(clause.text, 60),
        status=status,
        blocking=True,
        reason=reason,
        evidence=evidence,
        recommended_action=recommended_action,
    )


def _exception_language_represented(
    clause: Clause,
    rule_rows: list[RuleRow],
    carveouts: list[RuleCarveout],
) -> bool:
    clause_terms = _exception_terms(clause.text)
    if not clause_terms:
        return True
    represented_text = " ".join(
        [
            *(row.condition_text for row in rule_rows),
            *(carveout.condition_text for carveout in carveouts),
            *(carveout.quote for carveout in carveouts),
        ]
    ).lower()
    return any(term in represented_text for term in clause_terms)


def _exception_terms(text: str) -> set[str]:
    return {
        match.group(0).lower()
        for match in EXCEPTION_LANGUAGE_PATTERN.finditer(text)
        if not _is_negated_deemed_to_comply(text, match)
    }


def _is_negated_deemed_to_comply(value: str, match: re.Match[str]) -> bool:
    term = match.group(0).lower().replace(" ", "-")
    if term != "deemed-to-comply":
        return False
    prefix = value[max(0, match.start() - 24) : match.start()].lower()
    return bool(re.search(r"\bnot\s+(?:a\s+|an\s+|the\s+)?$", prefix))


def _quote_matches_clause(rule_row: RuleRow, clause: Clause) -> bool:
    quote = normalize_text(rule_row.quote)
    if not quote:
        return False
    return quote in normalize_text(clause.text)


def _candidate_has_matching_rule_row(
    candidate: RuleExtractionCandidate,
    rule_rows: list[RuleRow],
) -> bool:
    return any(
        row.source_version_id == candidate.source_version_id
        and row.clause_id == candidate.clause_id
        and row.rule_key == candidate.rule_key
        and row.operator == candidate.operator
        and row.value_json == candidate.value_json
        and row.unit == candidate.unit
        and row.quote == candidate.quote
        for row in rule_rows
    )


def _unclaimed_numeric_tokens(
    clause: Clause,
    rule_rows: list[RuleRow],
    carveouts: list[RuleCarveout],
) -> list[str]:
    tokens = sorted({match.group(0).lower() for match in NUMERIC_REQUIREMENT_PATTERN.finditer(clause.text)})
    if not tokens:
        return []
    claimed_text = normalize_text(
        " ".join(
            [
                *(row.quote for row in rule_rows if row.lifecycle_status in APPROVED_RULE_STATUSES),
                *(row.condition_text for row in rule_rows if row.lifecycle_status in APPROVED_RULE_STATUSES),
                *(carveout.quote for carveout in carveouts),
                *(carveout.condition_text for carveout in carveouts),
            ]
        )
    ).lower()
    return [token for token in tokens if token not in claimed_text]


def _numeric_tokens_require_rule_support(clause: Clause, disposition: ClauseDisposition | None) -> bool:
    if not disposition:
        return True
    if disposition.disposition in {"definition", "procedural", "informational"}:
        return False
    return disposition.disposition in {"rule_bearing", "manual_review"} or has_normative_language(clause.text)
