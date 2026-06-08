from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from draftcheck_core.audit import record_audit
from draftcheck_core.json_utils import from_json, to_json
from draftcheck_core.models import (
    AddressProfile,
    Project,
    ResolvedRule,
    RuleOverride,
    RuleRow,
    SourceCitation,
    SourceDocument,
    SourceLicenceReview,
    SourceVersion,
)
from draftcheck_core.source_support import (
    source_version_can_support_regulatory_output,
    source_version_runtime_support_conditions,
)
from draftcheck_shared.schemas import ResolvedRuleRead, ResolvedRulesRequest, ResolvedRulesResponse


class ResolvedRuleService:
    def __init__(self, db: Session):
        self.db = db

    def resolve_for_project(self, project_id: str, payload: ResolvedRulesRequest) -> ResolvedRulesResponse:
        project = self._get_project(project_id)
        address_profile_id = payload.address_profile_id or self._latest_address_profile_id(project_id)
        as_of_date = payload.as_of_date or project.as_of_date or date.today().isoformat()
        assessment_basis = payload.assessment_basis or project.assessment_basis
        issues: list[str] = []
        profile: AddressProfile | None = None

        if not address_profile_id:
            issues.append("address_profile_required")
        else:
            profile = self.db.get(AddressProfile, address_profile_id)
            if not profile:
                issues.append("address_profile_not_found")
            elif profile.resolution_status != "resolved":
                issues.append("address_profile_not_resolved")

        resolved_rules: list[ResolvedRule] = []
        suppressed_rule_ids: list[str] = []
        if profile and profile.resolution_status == "resolved":
            rule_rows = self._approved_rule_rows(project, profile, as_of_date)
            rule_rows, override_map, suppressed_rule_ids = self._apply_overrides(
                rule_rows,
                project=project,
                profile=profile,
                assessment_basis=assessment_basis,
            )
            if suppressed_rule_ids:
                self._mark_overridden_resolved_rules(
                    project_id=project_id,
                    address_profile_id=profile.id,
                    rule_row_ids=suppressed_rule_ids,
                    as_of_date=as_of_date,
                    assessment_basis=assessment_basis,
                )
            if not rule_rows:
                issues.append("approved_rule_rows_not_available")
            for rule_row in rule_rows:
                citations = self._rule_citations(rule_row)
                if not citations:
                    issues.append(f"citation_required_for_rule:{rule_row.rule_key}")
                    continue
                resolved_rules.append(
                    self._upsert_resolved_rule(
                        project_id=project_id,
                        address_profile_id=profile.id,
                        rule_row=rule_row,
                        citations=citations,
                        as_of_date=as_of_date,
                        assessment_basis=assessment_basis,
                        overridden_rule_ids=override_map.get(rule_row.id, []),
                    )
                )
        else:
            issues.append("approved_rule_rows_not_available")

        response_status = "needs_human_review" if resolved_rules else "unsupported"
        record_audit(
            self.db,
            action="resolved_rules.requested",
            target_type="project",
            target_id=project_id,
            project_id=project_id,
            metadata={
                "address_profile_id": address_profile_id,
                "as_of_date": as_of_date,
                "assessment_basis": assessment_basis,
                "issues": issues,
                "resolved_rule_count": len(resolved_rules),
                "overridden_rule_ids": suppressed_rule_ids if profile else [],
            },
        )
        return ResolvedRulesResponse(
            project_id=project_id,
            address_profile_id=address_profile_id,
            as_of_date=as_of_date,
            assessment_basis=assessment_basis,  # type: ignore[arg-type]
            status=response_status,  # type: ignore[arg-type]
            resolved_rules=[_resolved_rule_read(rule) for rule in resolved_rules],
            issues=issues,
        )

    def list_project_rules(self, project_id: str) -> list[ResolvedRuleRead]:
        return [
            _resolved_rule_read(rule)
            for rule in self.db.scalars(
                select(ResolvedRule)
                .where(ResolvedRule.project_id == project_id)
                .order_by(ResolvedRule.created_at.desc())
            )
        ]

    def _approved_rule_rows(
        self,
        project: Project,
        profile: AddressProfile,
        as_of_date: str,
    ) -> list[RuleRow]:
        local_government = profile.local_government or project.local_government
        stmt = (
            select(RuleRow)
            .distinct()
            .join(SourceVersion, SourceVersion.id == RuleRow.source_version_id)
            .join(SourceDocument, SourceDocument.id == SourceVersion.source_document_id)
            .join(
                SourceLicenceReview,
                SourceLicenceReview.source_version_id == RuleRow.source_version_id,
            )
            .where(
                RuleRow.lifecycle_status.in_(("approved", "auto_accepted")),
                *source_version_runtime_support_conditions(),
                SourceDocument.is_active.is_(True),
                or_(
                    SourceVersion.effective_date.is_(None),
                    SourceVersion.effective_date <= as_of_date,
                ),
                or_(
                    SourceDocument.local_government.is_(None),
                    SourceDocument.local_government == "",
                    SourceDocument.local_government == local_government,
                ),
            )
            .order_by(RuleRow.rule_key, RuleRow.created_at)
        )
        return _filter_rule_rows_by_regulatory_source_support(self.db, list(self.db.scalars(stmt).all()))

    def _apply_overrides(
        self,
        rule_rows: list[RuleRow],
        *,
        project: Project,
        profile: AddressProfile,
        assessment_basis: str,
    ) -> tuple[list[RuleRow], dict[str, list[str]], list[str]]:
        rule_ids = [row.id for row in rule_rows]
        if not rule_ids:
            return rule_rows, {}, []
        overrides = self.db.scalars(
            select(RuleOverride)
            .where(
                RuleOverride.overriding_rule_id.in_(rule_ids),
                RuleOverride.overridden_rule_id.in_(rule_ids),
            )
            .order_by(RuleOverride.created_at, RuleOverride.id)
        ).all()
        suppressed_rule_ids: set[str] = set()
        override_map: dict[str, list[str]] = {}
        for override in overrides:
            if not _override_scope_applies(override, project, profile, assessment_basis):
                continue
            suppressed_rule_ids.add(override.overridden_rule_id)
            override_map.setdefault(override.overriding_rule_id, []).append(override.overridden_rule_id)
        active_rule_rows = [row for row in rule_rows if row.id not in suppressed_rule_ids]
        return active_rule_rows, override_map, sorted(suppressed_rule_ids)

    def _rule_citations(self, rule_row: RuleRow) -> list[dict]:
        citation_rows = self.db.scalars(
            select(SourceCitation)
            .where(
                SourceCitation.source_version_id == rule_row.source_version_id,
                SourceCitation.clause_id == rule_row.clause_id,
            )
            .order_by(SourceCitation.created_at)
        ).all()
        return [from_json(citation.citation_json, {}) for citation in citation_rows]

    def _upsert_resolved_rule(
        self,
        *,
        project_id: str,
        address_profile_id: str,
        rule_row: RuleRow,
        citations: list[dict],
        as_of_date: str,
        assessment_basis: str,
        overridden_rule_ids: list[str],
    ) -> ResolvedRule:
        existing = self.db.scalar(
            select(ResolvedRule).where(
                ResolvedRule.project_id == project_id,
                ResolvedRule.address_profile_id == address_profile_id,
                ResolvedRule.rule_row_id == rule_row.id,
                ResolvedRule.as_of_date == as_of_date,
                ResolvedRule.assessment_basis == assessment_basis,
            )
        )
        applies_reason = (
            "Approved rule row selected for the resolved address profile. "
            "Human review is still required before treating the rule selection as submission-ready."
        )
        if overridden_rule_ids:
            applies_reason = (
                f"{applies_reason} Override precedence suppressed rule rows: "
                f"{', '.join(overridden_rule_ids)}."
            )
        if existing:
            existing.status = "needs_human_review"
            existing.applies_reason = applies_reason
            existing.overridden_rule_ids_json = to_json(overridden_rule_ids)
            existing.citations_json = to_json(citations)
            return existing

        resolved_rule = ResolvedRule(
            project_id=project_id,
            address_profile_id=address_profile_id,
            rule_row_id=rule_row.id,
            as_of_date=as_of_date,
            assessment_basis=assessment_basis,
            applies_reason=applies_reason,
            overridden_rule_ids_json=to_json(overridden_rule_ids),
            status="needs_human_review",
            citations_json=to_json(citations),
        )
        self.db.add(resolved_rule)
        self.db.flush()
        return resolved_rule

    def _mark_overridden_resolved_rules(
        self,
        *,
        project_id: str,
        address_profile_id: str,
        rule_row_ids: list[str],
        as_of_date: str,
        assessment_basis: str,
    ) -> None:
        if not rule_row_ids:
            return
        rows = self.db.scalars(
            select(ResolvedRule).where(
                ResolvedRule.project_id == project_id,
                ResolvedRule.address_profile_id == address_profile_id,
                ResolvedRule.rule_row_id.in_(rule_row_ids),
                ResolvedRule.as_of_date == as_of_date,
                ResolvedRule.assessment_basis == assessment_basis,
            )
        ).all()
        for row in rows:
            row.status = "not_applicable"
            row.applies_reason = "Suppressed by approved rule override precedence. Human review remains required."
            row.overridden_rule_ids_json = "[]"

    def _latest_address_profile_id(self, project_id: str) -> str | None:
        profile = self.db.scalar(
            select(AddressProfile)
            .where(AddressProfile.project_id == project_id)
            .order_by(AddressProfile.created_at.desc())
        )
        return profile.id if profile else None

    def _get_project(self, project_id: str) -> Project:
        project = self.db.get(Project, project_id)
        if not project:
            raise KeyError("Project not found")
        return project


def _override_scope_applies(
    override: RuleOverride,
    project: Project,
    profile: AddressProfile,
    assessment_basis: str,
) -> bool:
    scope: dict[str, Any] = from_json(override.scope_json, {})
    if not isinstance(scope, dict):
        return False
    supported_scope_values = {
        "local_government": profile.local_government or project.local_government,
        "project_type": project.project_type,
        "r_code_density": project.r_code_density,
        "assessment_basis": assessment_basis,
        "address_profile_id": profile.id,
    }
    for key, expected in scope.items():
        if key not in supported_scope_values:
            return False
        actual = supported_scope_values[key]
        if isinstance(expected, list):
            if actual not in expected:
                return False
        elif actual != expected:
            return False
    return True


def _filter_rule_rows_by_regulatory_source_support(db: Session, rule_rows: list[RuleRow]) -> list[RuleRow]:
    support_cache: dict[str, bool] = {}
    supported: list[RuleRow] = []
    for row in rule_rows:
        if row.source_version_id not in support_cache:
            support_cache[row.source_version_id] = source_version_can_support_regulatory_output(
                db,
                row.source_version_id,
            )
        if support_cache[row.source_version_id]:
            supported.append(row)
    return supported


def _resolved_rule_read(rule: ResolvedRule) -> ResolvedRuleRead:
    return ResolvedRuleRead(
        id=rule.id,
        project_id=rule.project_id,
        address_profile_id=rule.address_profile_id,
        rule_row_id=rule.rule_row_id,
        as_of_date=rule.as_of_date,
        assessment_basis=rule.assessment_basis,  # type: ignore[arg-type]
        applies_reason=rule.applies_reason,
        overridden_rule_ids=from_json(rule.overridden_rule_ids_json, []),
        status=rule.status,  # type: ignore[arg-type]
        citations=from_json(rule.citations_json, []),
        created_at=rule.created_at,
    )
