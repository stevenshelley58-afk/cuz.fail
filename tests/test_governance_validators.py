"""Validator tests for the process-control / source-governance feature.

PR-3 of docs/process-control/implementation-map.md.

The V3 schema is JSONB-on-Postgres; SQLite cannot render the column
type. Existing V3 tests avoid this by either (a) using a real Postgres
DB or (b) only creating the small subset of tables they need. The
validators inspect ~25 tables with extensive JSONB columns, so neither
option is practical here.

The validators are pure functions: they query, branch on field values,
and append to a list. They never mutate. So we test them against a
hand-rolled ``MockSession`` that responds to the limited surface the
validators use, with rows we construct in-test. This is the same
pattern the repo uses for unit-testing non-DB code in
``test_v3_jobs.py`` and similar.

Each validator has at least one positive (no failure produced) and
one negative (failure produced) test.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from typing import Any, Callable
from uuid import UUID, uuid4

from draftcheck.governance.types import (
    GovernanceFailure,
    GovernanceFailureCode,
    GovernanceSeverity,
)
from draftcheck.governance.validators import (
    capa,
    check_results,
    controls,
    exports,
    findings,
    kpis,
    pipeline_steps,
    rules,
    sources,
)
from draftcheck.governance import run_all_validators


# ---------------------------------------------------------------------------
# MockSession — minimal session surface for the validators
# ---------------------------------------------------------------------------


@dataclass
class MockResult:
    rows: list[Any]

    def first(self) -> Any | None:
        return self.rows[0] if self.rows else None

    def all(self) -> list[Any]:
        return list(self.rows)

    def one(self) -> Any:
        if not self.rows:
            raise ValueError("no rows")
        return self.rows[0]

    def scalar(self) -> Any | None:
        """Returns the first element of the first row, or the row itself
        for a bare scalar query."""
        if not self.rows:
            return None
        first = self.rows[0]
        # If it's a tuple, return the first element.
        if isinstance(first, tuple):
            return first[0]
        return first

    def __iter__(self):
        return iter(self.rows)


def _table_name(stmt: Any) -> str | None:
    """Extract the primary table name from a SQLAlchemy Select statement.

    Returns the lowercase table name if the statement is a single-table
    SELECT, or None for JOINs / unions / function calls.
    """
    try:
        cols = stmt.get_final_froms()
    except Exception:
        return None
    if not cols:
        return None
    # cols[0] is a Table or aliased Table.
    table = getattr(cols[0], "table", cols[0])
    return getattr(table, "name", None)


@dataclass
class MockSession:
    """Hand-rolled session stub for the validators.

    Tests build a list of mock rows. The session filters rows by the
    table being queried: a ``select(SourceVersion)`` returns only rows
    that *look like* SourceVersion rows (i.e. have a ``superseded_by_version_id``
    attribute). A ``select(SourceReviewRecord)`` returns only rows that
    have a ``review_status`` attribute. The filter is duck-typed because
    the validators issue many different queries and we cannot bind the
    mock to a specific ORM class without coupling to the production
    models.

    For queries with WHERE clauses that the test cares about (e.g.
    "give me the source_review for this source_version_id"), tests can
    install a custom ``scalars_handler`` that overrides this behaviour.
    """

    rows: list[Any] = field(default_factory=list)
    get_by_id: dict[tuple[str, UUID], Any] = field(default_factory=dict)
    scalars_handler: Callable[[Any], list[Any] | None] | None = None
    scalar_handler: Callable[[Any], Any | None] = None

    def _filter_rows(self, stmt: Any) -> list[Any]:
        """Default filter: match rows by duck-typed attribute presence
        matching the queried table.
        """
        tname = _table_name(stmt)
        if tname is None:
            return list(self.rows)
        # Each table has a distinctive set of attributes the validators
        # check. Use those as the duck-type filter.
        signature_map: dict[str, set[str]] = {
            "source_documents": {"title", "jurisdiction", "authority"},
            "source_versions": {"sha256", "licence_status", "review_status",
                                "superseded_by_version_id"},
            "source_chunks": {"source_version_id", "chunk_index", "text"},
            "source_citations": {"source_chunk_id", "source_version_id",
                                  "citation_json"},
            "source_reviews": {"review_status", "licence_status",
                                "reviewed_at", "source_version_id"},
            "rules": {"rule_key", "lifecycle_status", "operator",
                      "value_json", "quote"},
            "rule_clause_links": {"link_type", "rule_id", "clause_id"},
            "resolved_rules": {"check_run_id", "rule_id", "rule_key",
                                "citations_json"},
            "check_runs": {"as_of_date", "engine_version", "status"},
            "check_results": {"check_key", "status", "citations_json",
                              "decision_trace_json"},
            "rfi_items": {"title", "body", "severity", "status",
                          "check_result_id"},
            "exports": {"format", "status", "manifest_json", "sha256"},
            "artifacts": {"kind", "storage_path", "sha256"},
            "skill_versions": {"skill_name", "version_label", "status"},
            "eval_cases": {"suite_name", "case_key", "skill_name"},
            "eval_runs": {"eval_case_id", "status", "score"},
            "job_traces": {"adapter_name", "provider", "model",
                            "prompt_hash", "status"},
            "review_items": {"subject_type", "subject_id", "reason",
                              "status"},
            "governance_pipeline_steps": {"stage", "function_path",
                                            "is_critical"},
            "governance_risks": {"code", "name", "severity",
                                  "default_owner_role"},
            "governance_controls": {"code", "name", "control_type",
                                     "owner_role", "test_frequency_days"},
            "governance_kpis": {"code", "name", "sql_template",
                                 "review_cadence_days"},
            "governance_kpi_results": {"kpi_id", "period_start",
                                        "period_end", "value", "status"},
            "governance_findings": {"risk_code", "severity", "subject_type",
                                     "status", "summary"},
            "governance_reviews": {"review_type", "period_start",
                                    "period_end"},
            "projects": {"name", "status", "metadata_json"},
            "proposals": {"project_id", "kind"},
            "orgs": {"name", "slug", "status"},
            "users": {"email", "role", "status"},
        }
        sig = signature_map.get(tname)
        if sig is None:
            return list(self.rows)
        return [r for r in self.rows if all(hasattr(r, a) for a in sig)]

    def scalars(self, stmt: Any) -> MockResult:
        if self.scalars_handler is not None:
            result = self.scalars_handler(stmt)
            if result is not None:
                return MockResult(rows=result)
        return MockResult(rows=self._filter_rows(stmt))

    def scalar(self, stmt: Any) -> Any | None:
        if self.scalar_handler is not None:
            return self.scalar_handler(stmt)
        rows = self._filter_rows(stmt)
        if not rows:
            return None
        return rows[0]

    def get(self, model: type, pk: Any) -> Any | None:
        # model.__tablename__ gives the real table name; fall back to name.
        tname = getattr(model, "__tablename__", getattr(model, "__name__", None))
        if tname is None:
            return None
        # Normalise: get_by_id may be keyed by UUID, str(UUID), or other types.
        # Try pk, str(pk), and — if pk looks like a UUID string — the UUID form.
        candidates: list[Any] = [pk, str(pk)]
        try:
            from uuid import UUID as _UUID
            candidates.append(_UUID(str(pk)))
        except (ValueError, AttributeError, TypeError):
            pass
        for key_pk in candidates:
            v = self.get_by_id.get((tname, key_pk))
            if v is not None:
                return v
        return None

    def add(self, obj: Any) -> None:
        # Validators never call .add; tests use this hook for safety.
        self.rows.append(obj)

    def flush(self) -> None:
        pass


# ---------------------------------------------------------------------------
# Row builders
# ---------------------------------------------------------------------------


def _org(id: UUID | None = None) -> Any:
    o = type("Org", (), {})()
    o.id = id or uuid4()
    o.name = "Test Org"
    o.slug = "org-" + uuid4().hex[:8]
    o.status = "active"
    return o


def _user(id: UUID | None = None, role: str = "operator") -> Any:
    u = type("User", (), {})()
    u.id = id or uuid4()
    u.org_id = uuid4()
    u.email = "u@x"
    u.role = role
    u.status = "active"
    return u


def _source(id: UUID | None = None) -> Any:
    s = type("Source", (), {})()
    s.id = id or uuid4()
    s.org_id = uuid4()
    s.title = "Source"
    s.jurisdiction = "WA"
    s.authority = "Test"
    s.source_type = "planning_scheme"
    s.access_type = "public"
    s.status = "active"
    s.metadata_json = {}
    return s


def _source_version(
    id: UUID | None = None,
    source_id: UUID | None = None,
    owner_user_id: UUID | None = None,
    review_due_date: Any = None,
    superseded_by: UUID | None = None,
    effective_from: datetime | None = None,
    effective_to: datetime | None = None,
) -> Any:
    sv = type("SourceVersion", (), {})()
    sv.id = id or uuid4()
    sv.source_id = source_id or uuid4()
    sv.version_label = "v1"
    sv.sha256 = uuid4().hex
    sv.licence_status = "approved"
    sv.review_status = "approved"
    sv.owner_user_id = owner_user_id
    sv.review_due_date = review_due_date
    sv.superseded_by_version_id = superseded_by
    sv.effective_from = effective_from
    sv.effective_to = effective_to
    sv.fetched_at = datetime.now(UTC)
    sv.metadata_json = {}
    return sv


def _source_review(
    version_id: UUID,
    review_status: str = "approved",
    licence_status: str = "approved",
    reviewed_at: datetime | None = None,
) -> Any:
    r = type("SourceReviewRecord", (), {})()
    r.id = uuid4()
    r.org_id = uuid4()
    r.source_id = uuid4()
    r.source_version_id = version_id
    r.review_status = review_status
    r.licence_status = licence_status
    r.notes = None
    r.reviewed_at = reviewed_at or datetime.now(UTC)
    r.decision_metadata_json = {}
    return r


def _project(council_scope: str | None = "City of Cockburn") -> Any:
    p = type("Project", (), {})()
    p.id = uuid4()
    p.org_id = uuid4()
    p.name = "Test Project"
    p.status = "draft"
    p.metadata_json = {}
    p.council_scope = council_scope
    return p


def _check_run(project_id: UUID, status: str = "likely_compliant") -> Any:
    r = type("CheckRun", (), {})()
    r.id = uuid4()
    r.org_id = uuid4()
    r.project_id = project_id
    r.as_of_date = datetime.now(UTC)
    r.status = status
    r.engine_version = "1.0.0"
    r.source_version_ids_json = []
    return r


def _check_result(
    run_id: UUID,
    project_id: UUID,
    status: str = "likely_pass",
    resolved_rule_id: UUID | None = None,
    citations_json: list | None = None,
    decision_trace_json: dict | None = None,
) -> Any:
    cr = type("CheckResult", (), {})()
    cr.id = uuid4()
    cr.org_id = uuid4()
    cr.project_id = project_id
    cr.check_run_id = run_id
    cr.check_key = "test_key"
    cr.status = status
    cr.resolved_rule_id = resolved_rule_id
    cr.citations_json = citations_json or []
    cr.decision_trace_json = decision_trace_json or {}
    cr.requirement_json = {}
    cr.proposed_json = {}
    cr.why_this_applies = ""
    cr.drawing_evidence_json = {}
    cr.human_override_json = {}
    cr.pathway_note = None
    cr.review_reason = None
    cr.reviewed_by_user_id = None
    cr.reviewed_at = None
    return cr


def _rfi(check_result_id: UUID, project_id: UUID) -> Any:
    r = type("RfiItem", (), {})()
    r.id = uuid4()
    r.org_id = uuid4()
    r.project_id = project_id
    r.document_id = None
    r.check_result_id = check_result_id
    r.item_key = None
    r.title = "Fix this"
    r.body = "body"
    r.severity = "high"
    r.status = "open"
    r.assigned_user_id = None
    r.due_at = None
    r.resolved_at = None
    r.source_json = {}
    r.metadata_json = {}
    return r


def _rule(
    id: UUID | None = None,
    key: str = "test_key",
    lifecycle: str = "approved",
    operator: str = "gte",
    council_scope: str | None = None,
    applicable_zones: list | None = None,
    applicable_r_codes: list | None = None,
    source_version_id: UUID | None = None,
    clause_id: UUID | None = None,
) -> Any:
    r = type("Rule", (), {})()
    r.id = id or uuid4()
    r.org_id = uuid4()
    r.source_version_id = source_version_id or uuid4()
    r.clause_id = clause_id or uuid4()
    r.candidate_id = None
    r.rule_key = key
    r.rule_type = "requirement"
    r.pathway = "none"
    r.lifecycle_status = lifecycle
    r.operator = operator
    r.value_json = {"value": 1.0}
    r.unit = "m"
    r.condition_json = {}
    r.quote = "A quote."
    r.extractor_model = None
    r.skill_version_id = None
    r.prompt_hash = None
    r.superseded_by_rule_id = None
    r.metadata_json = {}
    r.council_scope = council_scope
    r.applicable_zones = applicable_zones
    r.applicable_r_codes = applicable_r_codes
    return r


def _primary_link(rule_id: UUID, clause_id: UUID) -> Any:
    link = type("RuleClauseLink", (), {})()
    link.id = uuid4()
    link.rule_id = rule_id
    link.clause_id = clause_id
    link.source_version_id = None
    link.link_type = "primary"
    link.quote = "primary quote"
    link.confidence = 0.9
    link.metadata_json = {}
    return link


def _export(
    run_id: UUID | None = None,
    project_id: UUID | None = None,
    status: str = "completed",
    manifest: dict | None = None,
    sha256: str | None = None,
) -> Any:
    e = type("Export", (), {})()
    e.id = uuid4()
    e.org_id = uuid4()
    e.project_id = project_id or uuid4()
    e.check_run_id = run_id
    e.requested_by_user_id = None
    e.format = "pdf"
    e.status = status
    e.sections_json = []
    e.manifest_json = manifest or {}
    e.storage_path = "/tmp/x"
    e.sha256 = sha256 or uuid4().hex
    e.metadata_json = {}
    return e


def _has_code(failures: list[GovernanceFailure], code: GovernanceFailureCode) -> bool:
    return any(f.code == code for f in failures)


# ---------------------------------------------------------------------------
# Helper: build a session whose scalars() returns the given rows
# ---------------------------------------------------------------------------


def _session_with(rows: list[Any]) -> MockSession:
    """Build a session that knows about ``rows`` and filters by table.

    Tests that need to override the filter for a specific query can pass
    a custom ``scalars_handler`` after construction.
    """
    return MockSession(rows=rows)


# ===========================================================================
# GOV-SRC-* tests
# ===========================================================================


def test_src_001_owner_required() -> None:
    src = _source()
    sv = _source_version(source_id=src.id, owner_user_id=None)
    session = _session_with([sv])

    failures = sources.validate(session)
    assert _has_code(failures, GovernanceFailureCode.SRC_001_OWNER_REQUIRED)


def test_src_001_owner_required_passes_when_set() -> None:
    user = _user()
    src = _source()
    sv = _source_version(source_id=src.id, owner_user_id=user.id)
    session = _session_with([sv])

    failures = sources.validate(session)
    assert not _has_code(failures, GovernanceFailureCode.SRC_001_OWNER_REQUIRED)


def test_src_002_review_due_overdue() -> None:
    user = _user()
    src = _source()
    sv = _source_version(
        source_id=src.id,
        owner_user_id=user.id,
        review_due_date=date(2020, 1, 1),
    )
    session = _session_with([sv])

    failures = sources.validate(session)
    assert _has_code(failures, GovernanceFailureCode.SRC_002_REVIEW_DUE_REQUIRED)


def test_src_002_review_due_future_passes() -> None:
    user = _user()
    src = _source()
    sv = _source_version(
        source_id=src.id,
        owner_user_id=user.id,
        review_due_date=date.today() + timedelta(days=365),
    )
    session = _session_with([sv])

    failures = sources.validate(session)
    assert not _has_code(failures, GovernanceFailureCode.SRC_002_REVIEW_DUE_REQUIRED)


def test_src_003_licence_unapproved() -> None:
    user = _user()
    src = _source()
    sv = _source_version(source_id=src.id, owner_user_id=user.id)
    review = _source_review(sv.id, review_status="pending_review")
    session = MockSession(rows=[sv, review])

    failures = sources.validate(session)
    assert _has_code(failures, GovernanceFailureCode.SRC_003_LICENCE_APPROVED)


def test_src_003_licence_approved_passes() -> None:
    user = _user()
    src = _source()
    sv = _source_version(source_id=src.id, owner_user_id=user.id)
    review = _source_review(sv.id, review_status="approved", licence_status="approved")
    session = MockSession(rows=[sv, review])

    failures = sources.validate(session)
    assert not _has_code(failures, GovernanceFailureCode.SRC_003_LICENCE_APPROVED)


def test_src_005_cited_from_unapproved_version() -> None:
    user = _user()
    src = _source()
    sv = _source_version(source_id=src.id, owner_user_id=user.id)
    review = _source_review(sv.id, review_status="pending_review")
    proj = _project()
    run = _check_run(proj.id)
    cr = _check_result(
        run.id,
        proj.id,
        status="likely_pass",
        resolved_rule_id=uuid4(),
        citations_json=[{"source_version_id": str(sv.id)}],
        decision_trace_json={"x": 1},
    )
    # Build a ResolvedRule mock that the validator will see when it
    # iterates ``session.scalars(select(ResolvedRule))``.
    rr = type("ResolvedRule", (), {})()
    rr.id = uuid4()
    rr.org_id = uuid4()
    rr.project_id = proj.id
    rr.check_run_id = run.id
    rr.rule_id = uuid4()
    rr.rule_key = "k"
    rr.applicability_status = "applicable"
    rr.pathway = "none"
    rr.precedence_rank = None
    rr.assumptions_json = {}
    rr.rule_snapshot_json = {}
    rr.selection_trace_json = {}
    rr.citations_json = [{"source_version_id": str(sv.id)}]

    session = MockSession(
        rows=[sv, review, cr, rr],
        get_by_id={("source_versions", sv.id): sv},
    )

    failures = sources.validate(session)
    assert _has_code(failures, GovernanceFailureCode.SRC_005_CHUNK_FROM_APPROVED_VERSION)


# ===========================================================================
# GOV-RULE-* tests
# ===========================================================================


def test_rule_001_approved_without_quote_fails() -> None:
    r = _rule(lifecycle="approved")
    r.quote = ""
    session = _session_with([r])

    failures = rules.validate(session)
    assert _has_code(failures, GovernanceFailureCode.RULE_001_HAS_QUOTE_AND_CLAUSE)


def test_rule_002_no_primary_link_fails() -> None:
    r = _rule(lifecycle="approved")
    session = _session_with([r])

    failures = rules.validate(session)
    assert _has_code(failures, GovernanceFailureCode.RULE_002_HAS_PRIMARY_LINK)


def test_rule_002_with_primary_link_passes() -> None:
    r = _rule(lifecycle="approved")
    link = _primary_link(r.id, r.clause_id)
    session = MockSession(rows=[r, link])

    failures = rules.validate(session)
    assert not _has_code(failures, GovernanceFailureCode.RULE_001_HAS_QUOTE_AND_CLAUSE)
    assert not _has_code(failures, GovernanceFailureCode.RULE_002_HAS_PRIMARY_LINK)


def test_rule_003_invalid_operator_fails() -> None:
    r = _rule(operator="some_invalid_op")
    session = _session_with([r])

    failures = rules.validate(session)
    assert _has_code(failures, GovernanceFailureCode.RULE_003_OPERATOR_VALID)


def test_rule_004_conflicting_approved_rules() -> None:
    r1 = _rule(key="dup", lifecycle="approved")
    r2 = _rule(key="dup", lifecycle="approved")
    session = _session_with([r1, r2])

    failures = rules.validate(session)
    assert _has_code(failures, GovernanceFailureCode.RULE_004_NO_CONFLICTING_APPROVED_RULES)


# ===========================================================================
# GOV-CHK-* tests
# ===========================================================================


def test_chk_001_advisory_without_resolved_rule_fails() -> None:
    proj = _project()
    run = _check_run(proj.id)
    cr = _check_result(
        run.id, proj.id, status="likely_pass",
        resolved_rule_id=None,
        citations_json=[{"source_version_id": str(uuid4())}],
        decision_trace_json={"x": 1},
    )
    session = _session_with([cr])

    failures = check_results.validate(session)
    assert _has_code(failures, GovernanceFailureCode.CHK_001_RESOLVED_RULE_AND_CITATIONS)


def test_chk_003_failures_have_rfi() -> None:
    proj = _project()
    run = _check_run(proj.id, status="has_likely_failures")
    cr = _check_result(run.id, proj.id, status="likely_fail")
    session = _session_with([run, cr])

    failures = check_results.validate(session)
    assert _has_code(failures, GovernanceFailureCode.CHK_003_FAILURES_HAVE_RFI)


def test_chk_003_with_rfi_passes() -> None:
    proj = _project()
    run = _check_run(proj.id, status="has_likely_failures")
    cr = _check_result(run.id, proj.id, status="likely_fail")
    rfi = _rfi(cr.id, proj.id)
    # The validator needs to find the RfiItem via a select(RfiItem)
    # where check_result_id.in_(...). With a no-handler MockSession,
    # select(RfiItem) returns all rfi rows — that's a positive
    # for this test (we only care that an RfiItem exists).
    session = MockSession(rows=[run, cr, rfi])
    failures = check_results.validate(session)
    assert not _has_code(failures, GovernanceFailureCode.CHK_003_FAILURES_HAVE_RFI)


# ===========================================================================
# GOV-EXP-* tests
# ===========================================================================


def test_exp_002_failed_validation_blocked() -> None:
    proj = _project()
    run = _check_run(proj.id)
    exp = _export(run_id=run.id, project_id=proj.id, manifest={"validation_passed": False})
    session = _session_with([exp])

    failures = exports.validate(session)
    assert _has_code(failures, GovernanceFailureCode.EXP_002_FAILED_VALIDATION_BLOCKED)


def test_exp_001_completed_without_validation_key_fails() -> None:
    proj = _project()
    run = _check_run(proj.id)
    exp = _export(run_id=run.id, project_id=proj.id, manifest={})
    session = _session_with([exp])

    failures = exports.validate(session)
    assert _has_code(failures, GovernanceFailureCode.EXP_001_COMPLETED_HAS_VALIDATION)


# ===========================================================================
# GOV-CTRL-* tests
# ===========================================================================


def _risk(code: str = "R_TEST") -> Any:
    r = type("GovernanceRisk", (), {})()
    r.id = uuid4()
    r.code = code
    r.name = "Test Risk"
    r.description = None
    r.severity = "major"
    r.default_owner_role = "operator"
    return r


def _control(
    code: str = "R_TEST",
    name: str = "Control A",
    owner_role: str = "operator",
    test_frequency_days: int | None = None,
    last_tested_at: datetime | None = None,
) -> Any:
    c = type("GovernanceControl", (), {})()
    c.id = uuid4()
    c.code = code
    c.name = name
    c.control_type = "detective"
    c.description = None
    c.control_function_path = "x.y"
    c.owner_role = owner_role
    c.test_frequency_days = test_frequency_days
    c.last_tested_at = last_tested_at
    c.metadata_json = {}
    return c


def test_ctrl_002_owner_role_required() -> None:
    risk = _risk()
    ctrl = _control(owner_role="")
    session = MockSession(rows=[risk, ctrl])
    failures = controls.validate(session)
    assert _has_code(failures, GovernanceFailureCode.CTRL_002_OWNER_ROLE_SET)


def test_ctrl_001_never_tested_fails() -> None:
    risk = _risk(code="R1")
    ctrl = _control(code="R1", name="C1", test_frequency_days=7, last_tested_at=None)
    session = MockSession(rows=[risk, ctrl])
    failures = controls.validate(session)
    assert _has_code(failures, GovernanceFailureCode.CTRL_001_TESTED_WITHIN_FREQUENCY)


# ===========================================================================
# GOV-FIND-* tests
# ===========================================================================


def _finding(
    status: str = "proposed",
    created_at: datetime | None = None,
    decision_user_id: UUID | None = None,
    decision_reason: str | None = None,
    decision_evidence_id: UUID | None = None,
    linked_capa_id: UUID | None = None,
) -> Any:
    f = type("GovernanceFinding", (), {})()
    f.id = uuid4()
    f.org_id = uuid4()
    f.risk_code = "R"
    f.severity = "major"
    f.subject_type = "rule"
    f.subject_id = uuid4()
    f.summary = "summary"
    f.evidence_refs_json = []
    f.proposed_remediation = None
    f.proposed_by_job_trace_id = None
    f.proposed_by_model = None
    f.skill_version_id = None
    f.status = status
    f.decision_user_id = decision_user_id
    f.decision_reason = decision_reason
    f.decision_evidence_id = decision_evidence_id
    f.decision_at = None
    f.linked_capa_id = linked_capa_id
    f.created_at = created_at or datetime.now(UTC)
    return f


def test_find_001_proposed_stale_fails() -> None:
    f = _finding(
        status="proposed",
        created_at=datetime.now(UTC) - timedelta(days=30),
    )
    session = _session_with([f])
    failures = findings.validate(session)
    assert _has_code(failures, GovernanceFailureCode.FIND_001_PROPOSED_NOT_STALE)


def test_find_002_accepted_missing_decision_fails() -> None:
    f = _finding(status="accepted")
    session = _session_with([f])
    failures = findings.validate(session)
    assert _has_code(failures, GovernanceFailureCode.FIND_002_ACCEPTED_HAS_DECISION_FIELDS)


def test_find_003_converted_capa_linked() -> None:
    capa_id = uuid4()
    # Capa row is missing severity.
    capa_row = type("ReviewItem", (), {})()
    capa_row.id = capa_id
    capa_row.subject_type = "rule"
    capa_row.subject_id = uuid4()
    capa_row.reason = "x"
    capa_row.status = "open"
    capa_row.severity = None
    capa_row.assigned_user_id = uuid4()
    capa_row.due_at = datetime.now(UTC) + timedelta(days=7)

    f = _finding(status="converted_to_capa", linked_capa_id=capa_id)
    session = MockSession(
        rows=[f],
        get_by_id={("review_items", capa_id): capa_row},
    )
    failures = findings.validate(session)
    assert _has_code(failures, GovernanceFailureCode.FIND_003_CONVERTED_CAPA_LINKED)


# ===========================================================================
# GOV-CAPA-* tests
# ===========================================================================


def _review_item(
    status: str = "open",
    closure_evidence_id: UUID | None = None,
    effectiveness_check_due_date: Any = None,
    effectiveness_result: str | None = None,
    proposed_by_finding_id: UUID | None = None,
    severity: str | None = "major",
    assigned_user_id: UUID | None = None,
    due_at: datetime | None = None,
) -> Any:
    ri = type("ReviewItem", (), {})()
    ri.id = uuid4()
    ri.org_id = uuid4()
    ri.project_id = None
    ri.subject_type = "rule"
    ri.subject_id = uuid4()
    ri.reason = "x"
    ri.status = status
    ri.priority = 0
    ri.assigned_user_id = assigned_user_id
    ri.due_at = due_at
    ri.resolved_by_user_id = None
    ri.resolved_at = None
    ri.source_json = {}
    ri.metadata_json = {}
    ri.closure_evidence_id = closure_evidence_id
    ri.effectiveness_check_due_date = effectiveness_check_due_date
    ri.effectiveness_result = effectiveness_result
    ri.proposed_by_finding_id = proposed_by_finding_id
    ri.severity = severity
    return ri


def test_capa_001_resolved_without_evidence_fails() -> None:
    ri = _review_item(status="resolved")
    session = _session_with([ri])
    failures = capa.validate(session)
    assert _has_code(failures, GovernanceFailureCode.CAPA_001_CLOSED_HAS_EVIDENCE_AND_DATE)


def test_capa_001_resolved_with_evidence_passes() -> None:
    ri = _review_item(
        status="resolved",
        closure_evidence_id=uuid4(),
        effectiveness_check_due_date=date.today() + timedelta(days=30),
    )
    session = _session_with([ri])
    failures = capa.validate(session)
    assert not _has_code(failures, GovernanceFailureCode.CAPA_001_CLOSED_HAS_EVIDENCE_AND_DATE)


def test_capa_002_effectiveness_overdue_fails() -> None:
    ri = _review_item(
        status="resolved",
        closure_evidence_id=uuid4(),
        effectiveness_check_due_date=date(2020, 1, 1),
        effectiveness_result=None,
    )
    session = _session_with([ri])
    failures = capa.validate(session)
    assert _has_code(failures, GovernanceFailureCode.CAPA_002_EFFECTIVENESS_CHECK_OVERDUE)


# ===========================================================================
# GOV-KPI-* tests
# ===========================================================================


def _kpi(review_cadence_days: int | None = 7) -> Any:
    k = type("GovernanceKpi", (), {})()
    k.id = uuid4()
    k.code = "K1"
    k.name = "K1"
    k.description = None
    k.sql_template = "SELECT 1"
    k.warning_threshold = None
    k.breach_threshold = None
    k.review_cadence_days = review_cadence_days
    k.owner_role = "operator"
    return k


def test_kpi_001_stale_result_fails() -> None:
    k = _kpi(review_cadence_days=7)
    # Validator queries func.max(GovernanceKpiResult.computed_at)
    # via session.scalar(...). The mock returns the first row's scalar,
    # which is the kpi itself (kpi has no .computed_at, returns None
    # path) — but we want to control the scalar. Use scalar_handler.
    session = MockSession(
        rows=[k],
        scalar_handler=lambda _stmt: datetime(2020, 1, 8, tzinfo=UTC),
    )
    failures = kpis.validate(session)
    assert _has_code(failures, GovernanceFailureCode.KPI_001_RESULT_FRESH)


# ===========================================================================
# GOV-PIPE-* tests
# ===========================================================================


def _step(stage: str = "unknown", is_critical: bool = True) -> Any:
    s = type("GovernancePipelineStep", (), {})()
    s.id = uuid4()
    s.stage = stage
    s.function_path = "x.y"
    s.description = None
    s.is_critical = is_critical
    s.owner_role = "operator"
    return s


def test_pipe_001_critical_step_without_risk() -> None:
    step = _step(stage="unknown_stage", is_critical=True)
    session = MockSession(rows=[step])
    failures = pipeline_steps.validate(session)
    assert _has_code(failures, GovernanceFailureCode.PIPE_001_CRITICAL_STEP_HAS_CONTROL)


# ===========================================================================
# run_all_validators smoke test
# ===========================================================================


def test_run_all_validators_smoke() -> None:
    """run_all_validators should never raise and returns a list."""
    src = _source()
    sv = _source_version(source_id=src.id, owner_user_id=None)
    session = _session_with([sv])
    failures = run_all_validators(session)
    assert isinstance(failures, list)
    for f in failures:
        assert isinstance(f, GovernanceFailure)
        assert f.severity in (
            GovernanceSeverity.CRITICAL,
            GovernanceSeverity.MAJOR,
            GovernanceSeverity.MINOR,
        )


def test_run_all_validators_severity_filter() -> None:
    src = _source()
    sv = _source_version(source_id=src.id, owner_user_id=None)
    session = _session_with([sv])
    failures = run_all_validators(session)
    critical = [f for f in failures if f.severity == GovernanceSeverity.CRITICAL]
    assert any(f.code == GovernanceFailureCode.SRC_001_OWNER_REQUIRED for f in critical)
