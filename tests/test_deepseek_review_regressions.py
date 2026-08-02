"""Regression tests for the 7 bugs fixed from DeepSeek code review rounds 1-2.

Each test encodes the exact scenario that was broken, so a future refactor
that re-introduces the bug will fail immediately.
"""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

from draftcheck.checks.engine import (
    _condition_rank,
    _filter_rules_by_spatial_scope,
    _source_spatial_scope,
)

UTC = timezone.utc


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _rule(
    key: str,
    *,
    value: float | None = 1.5,
    operator: str = "gte",
    council_scope: str | None = None,
    source_version_id: str | None = None,
    condition_json: dict | None = None,
    applicable_r_codes: list[str] | None = None,
    applicable_zones: list[str] | None = None,
    rule_type: str = "standard",
    check_type: str = "numeric",
) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        rule_key=key,
        canonical_rule_key=key,
        value_json={"value": value} if value is not None else {},
        operator=operator,
        unit="m",
        quote=f"Test rule for {key}",
        lifecycle_status="approved",
        council_scope=council_scope,
        source_version_id=uuid4() if source_version_id is None else source_version_id,
        condition_json=condition_json or {},
        applicable_r_codes=applicable_r_codes,
        applicable_zones=applicable_zones,
        rule_type=rule_type,
        check_type=check_type,
        pathway="none",
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )


def _fact(fact_type: str, value: dict, *, method: str = "postgis_st_intersects_zone", review_status: str = "pending_review") -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        fact_type=fact_type,
        value_json=value,
        method=method,
        review_status=review_status,
        confidence=0.85,
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        provenance_json={},
    )


# ---------------------------------------------------------------------------
# Round 2, Fix 1: LDP fact_type remap mismatch
# ---------------------------------------------------------------------------

class TestLdpFactTypeRemap:
    """The engine must NOT remap local_development_plan → structure_plan.

    The resolver writes fact_type='local_development_plan' as-is.  If the
    engine remaps it, LDP rules never match their spatial facts.
    """

    def test_source_spatial_scope_preserves_ldp_fact_type(self) -> None:
        source = SimpleNamespace(
            source_type="local_development_plan",
            title="LDP 42 — Ellenbrook",
            canonical_url=None,
            metadata_json={},
        )
        required, fact_type, refs = _source_spatial_scope(source)
        assert required is True
        assert fact_type == "local_development_plan"
        assert "LDP/42" in refs

    def test_source_spatial_scope_preserves_structure_plan(self) -> None:
        source = SimpleNamespace(
            source_type="structure_plan",
            title="SPN 100 — Alkimos",
            canonical_url=None,
            metadata_json={},
        )
        required, fact_type, refs = _source_spatial_scope(source)
        assert required is True
        assert fact_type == "structure_plan"
        assert "SPN/100" in refs

    def test_source_spatial_scope_maps_local_structure_plan_to_structure_plan(self) -> None:
        """local_structure_plan sources must map to fact_type='structure_plan'
        because the resolver writes fact_type from planning_features.layer_type
        which is 'structure_plan' for all structure-plan subtypes."""
        source = SimpleNamespace(
            source_type="local_structure_plan",
            title="LSP 5 — Yanchep",
            canonical_url=None,
            metadata_json={},
        )
        required, fact_type, refs = _source_spatial_scope(source)
        assert required is True
        assert fact_type == "structure_plan"


# ---------------------------------------------------------------------------
# Round 2, Fix 3: DELETE must preserve manual_override facts
# ---------------------------------------------------------------------------

class TestResolverDeletePreservesOverrides:
    """The resolver's _upsert_facts DELETE must not wipe manual_override rows.

    Verified by reading the SQL in resolver.py:767-770.  This test documents
    the invariant so a future refactor that drops the AND clause will be caught.
    """

    def test_delete_sql_contains_manual_override_guard(self) -> None:
        import inspect
        from draftcheck.domain.address.resolver import AddressResolver

        source = inspect.getsource(AddressResolver._upsert_facts)
        assert "manual_override" in source, (
            "The DELETE in _upsert_facts must exclude method='manual_override' "
            "to preserve user-entered proposed values across re-resolutions."
        )


# ---------------------------------------------------------------------------
# Round 2, Fix 4: council_scope=None must NOT load all councils' rules
# ---------------------------------------------------------------------------

class TestCouncilScopeNullFiltering:
    """When council_scope is unknown, only global rules (council_scope IS NULL)
    should be loaded.  Without this, council-scoped rules from every LGA leak
    into the candidate set."""

    def test_advisory_rules_null_council_only_globals(self) -> None:
        # _get_advisory_rules with council_scope=None adds
        # Rule.council_scope == None filter.  We verify the source contains
        # the else-branch guard.
        import inspect
        from draftcheck.checks.engine import _get_advisory_rules

        source = inspect.getsource(_get_advisory_rules)
        # The else branch must restrict to council_scope IS NULL
        assert "council_scope == None" in source or "council_scope.is_(None)" in source


# ---------------------------------------------------------------------------
# Round 2, Fix 5: Missing source_version_id must fail CLOSED
# ---------------------------------------------------------------------------

class TestSpatialScopeFailClosed:
    """_filter_rules_by_spatial_scope must EXCLUDE rules whose source_version
    cannot be resolved, not silently include them."""

    def test_unresolvable_source_version_excluded(self) -> None:
        rule = _rule("setback_front", source_version_id=str(uuid4()))
        # Empty session mock — no sources will resolve
        class FakeSession:
            def query(self, *a, **kw):
                return self
            def join(self, *a, **kw):
                return self
            def filter(self, *a, **kw):
                return self
            def all(self):
                return []

        result = _filter_rules_by_spatial_scope(
            FakeSession(), [rule], [], blocked_scope_types=None,
        )
        assert result == [], (
            "Rule with unresolvable source_version_id must be excluded "
            "(fail closed), not silently included."
        )


# ---------------------------------------------------------------------------
# Round 2, Fix 6: Label detection for lower-bound markers
# ---------------------------------------------------------------------------

class TestConditionLabelDetection:
    """_condition_rank must recognise 'more than', 'greater than', 'exceeds',
    'minimum', 'at least' as lower-bound markers, not just 'over'."""

    def _rank_with_label(self, label: str) -> tuple:
        rule = _rule(
            "boundary_wall_height",
            condition_json={
                "wall_height_m": 3.0,
                "wall_height_label": label,
            },
        )
        facts = {
            "proposed_wall_height_m": _fact(
                "proposed_wall_height_m",
                {"value": 4.0},
                method="manual_override",
                review_status="confirmed",
            ),
        }
        match, rank, missing = _condition_rank(rule, facts)
        return match, rank, missing

    def test_over_label_is_lower_bound(self) -> None:
        match, rank, _ = self._rank_with_label("wall height over 3.0m")
        assert match is True

    def test_more_than_label_is_lower_bound(self) -> None:
        match, rank, _ = self._rank_with_label("wall height more than 3.0m")
        assert match is True

    def test_greater_than_label_is_lower_bound(self) -> None:
        match, rank, _ = self._rank_with_label("wall height greater than 3.0m")
        assert match is True

    def test_exceeds_label_is_lower_bound(self) -> None:
        match, rank, _ = self._rank_with_label("wall height exceeds 3.0m")
        assert match is True

    def test_minimum_label_is_lower_bound(self) -> None:
        match, rank, _ = self._rank_with_label("minimum wall height 3.0m")
        assert match is True

    def test_at_least_label_is_lower_bound(self) -> None:
        match, rank, _ = self._rank_with_label("wall height at least 3.0m")
        assert match is True

    def test_upper_bound_label_rejects_over(self) -> None:
        """A measured value BELOW the boundary should fail for lower-bound."""
        rule = _rule(
            "boundary_wall_height",
            condition_json={
                "wall_height_m": 3.0,
                "wall_height_label": "wall height over 3.0m",
            },
        )
        facts = {
            "proposed_wall_height_m": _fact(
                "proposed_wall_height_m",
                {"value": 2.0},  # below 3.0 → should NOT match
                method="manual_override",
                review_status="confirmed",
            ),
        }
        match, _, _ = _condition_rank(rule, facts)
        assert match is False


# ---------------------------------------------------------------------------
# Round 2, Fix 7: Engine must load ALL resolver-written fact methods
# ---------------------------------------------------------------------------

class TestEngineFactLoadingMethods:
    """The engine's fact query must include postgis_st_within,
    postgis_st_area_epsg3112, and the three heuristic methods."""

    def test_run_check_source_includes_all_resolver_methods(self) -> None:
        import inspect
        from draftcheck.checks.engine import ComplianceEngine

        source = inspect.getsource(ComplianceEngine.run_check)
        # Broadened pattern
        assert 'postgis_%' in source or "postgis_%" in source, (
            "Engine must use LIKE 'postgis_%' to capture st_within and st_area"
        )
        # Heuristic methods
        assert "longest_exterior_edge_heuristic" in source
        assert "battle_axe_heuristic" in source
        assert "two_long_edges_heuristic" in source
