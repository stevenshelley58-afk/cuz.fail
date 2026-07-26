"""Phase 1 acceptance: R-Codes Vol 1 Part B all density codes.

Tests the rule coverage expansion (§2.1-§2.3) implementation:
- Migration 0020 columns exist on Rule model
- Check registry includes coverage expansion checks
- New CheckCategory values exist
- Schema contract for new columns

These are unit/schema tests that do NOT require a live database.
Integration tests (marked @pytest.mark.integration) require DATABASE_URL.
"""
from __future__ import annotations

import pytest

from draftcheck.db.models import Base, Rule
from draftcheck.checks.registry import (
    ALL_CHECKS,
    CHECK_BY_KEY,
    CheckCategory,
    CheckTier,
    COVERAGE_TIER1_CHECKS,
    COVERAGE_TIER2_CHECKS,
    SEED_CANONICAL_RULE_KEYS,
)


# ---------------------------------------------------------------------------
# Schema contract tests (no DB required)
# ---------------------------------------------------------------------------

class TestRuleCoverageColumns:
    """Verify migration 0020 columns exist on the Rule model."""

    def test_rules_table_has_dwelling_type(self) -> None:
        table = Base.metadata.tables["rules"]
        assert "dwelling_type" in table.c

    def test_rules_table_has_effective_from(self) -> None:
        table = Base.metadata.tables["rules"]
        assert "effective_from" in table.c

    def test_rules_table_has_effective_to(self) -> None:
        table = Base.metadata.tables["rules"]
        assert "effective_to" in table.c

    def test_rules_table_has_instrument_section(self) -> None:
        table = Base.metadata.tables["rules"]
        assert "instrument_section" in table.c

    def test_rules_table_has_table_reference(self) -> None:
        table = Base.metadata.tables["rules"]
        assert "table_reference" in table.c

    def test_dwelling_type_indexed(self) -> None:
        table = Base.metadata.tables["rules"]
        index_names = {idx.name for idx in table.indexes}
        assert "ix_rules_dwelling_type" in index_names

    def test_instrument_section_indexed(self) -> None:
        table = Base.metadata.tables["rules"]
        index_names = {idx.name for idx in table.indexes}
        assert "ix_rules_instrument_section" in index_names


class TestCheckCategoryExpansion:
    """Verify new CheckCategory values from §2.3."""

    def test_amenity_category_exists(self) -> None:
        assert hasattr(CheckCategory, "AMENITY")
        assert CheckCategory.AMENITY == "amenity"

    def test_subdivision_category_exists(self) -> None:
        assert hasattr(CheckCategory, "SUBDIVISION")
        assert CheckCategory.SUBDIVISION == "subdivision"

    def test_building_safety_category_exists(self) -> None:
        assert hasattr(CheckCategory, "BUILDING_SAFETY")
        assert CheckCategory.BUILDING_SAFETY == "building_safety"

    def test_environmental_category_exists(self) -> None:
        assert hasattr(CheckCategory, "ENVIRONMENTAL")
        assert CheckCategory.ENVIRONMENTAL == "environmental"


class TestCoverageCheckDefinitions:
    """Verify §2.3 check definitions are registered."""

    EXPECTED_TIER1_KEYS = [
        "setback_front_secondary",
        "deep_soil_area",
        "tree_planting",
        "outdoor_living_area",
        "outdoor_living_dimension",
        "pool_barrier_height",
        "smoke_alarm",
        "min_lot_size",
        "min_frontage",
    ]

    EXPECTED_TIER2_KEYS = [
        "solar_access",
        "visual_privacy",
        "overshadowing",
        "vehicle_access",
        "car_parking_spaces",
        "street_surveillance",
        "building_height_partc",
        "plot_ratio",
        "building_separation",
        "communal_open_space",
        "bal_construction",
    ]

    def test_coverage_tier1_checks_defined(self) -> None:
        keys = {c.key for c in COVERAGE_TIER1_CHECKS}
        for expected in self.EXPECTED_TIER1_KEYS:
            assert expected in keys, f"Missing TIER1 coverage check: {expected}"

    def test_coverage_tier2_checks_defined(self) -> None:
        keys = {c.key for c in COVERAGE_TIER2_CHECKS}
        for expected in self.EXPECTED_TIER2_KEYS:
            assert expected in keys, f"Missing TIER2 coverage check: {expected}"

    def test_coverage_checks_in_all_checks(self) -> None:
        all_keys = {c.key for c in ALL_CHECKS}
        for expected in self.EXPECTED_TIER1_KEYS + self.EXPECTED_TIER2_KEYS:
            assert expected in all_keys, f"Missing from ALL_CHECKS: {expected}"

    def test_coverage_checks_in_check_by_key(self) -> None:
        for expected in self.EXPECTED_TIER1_KEYS:
            assert expected in CHECK_BY_KEY, f"Missing from CHECK_BY_KEY: {expected}"

    def test_canonical_rule_keys_include_coverage(self) -> None:
        for key in self.EXPECTED_TIER1_KEYS + self.EXPECTED_TIER2_KEYS:
            assert key in SEED_CANONICAL_RULE_KEYS, (
                f"Missing canonical mapping for: {key}"
            )

    def test_coverage_tier1_have_correct_tier(self) -> None:
        for check in COVERAGE_TIER1_CHECKS:
            assert check.tier == CheckTier.TIER1, (
                f"{check.key} should be TIER1"
            )

    def test_coverage_tier2_have_correct_tier(self) -> None:
        for check in COVERAGE_TIER2_CHECKS:
            assert check.tier == CheckTier.TIER2, (
                f"{check.key} should be TIER2"
            )


class TestRuleModelAttributes:
    """Verify Rule ORM model has the new attributes."""

    def test_rule_model_has_dwelling_type(self) -> None:
        assert hasattr(Rule, "dwelling_type")

    def test_rule_model_has_effective_from(self) -> None:
        assert hasattr(Rule, "effective_from")

    def test_rule_model_has_effective_to(self) -> None:
        assert hasattr(Rule, "effective_to")

    def test_rule_model_has_instrument_section(self) -> None:
        assert hasattr(Rule, "instrument_section")

    def test_rule_model_has_table_reference(self) -> None:
        assert hasattr(Rule, "table_reference")


# ---------------------------------------------------------------------------
# Integration tests (require DATABASE_URL)
# ---------------------------------------------------------------------------

REQUIRED_R_CODES = ["R2", "R5", "R10", "R15", "R17.5", "R20", "R25", "R30", "R35", "R40"]
REQUIRED_DWELLING_TYPES = ["single_house", "grouped_dwelling", "multiple_dwelling"]
MIN_RULES_PER_R_CODE = 5


@pytest.mark.integration
class TestPhase1Integration:
    """Integration tests requiring a live database with Phase 1 data."""

    @pytest.fixture(autouse=True)
    def _skip_no_db(self, request: pytest.FixtureRequest) -> None:
        import os
        if not os.environ.get("DATABASE_URL"):
            pytest.skip("DATABASE_URL not set")

    def test_all_r_codes_have_rules(self) -> None:
        """Every R-code from R2 to R40 has at least MIN_RULES_PER_R_CODE approved rules."""
        import psycopg
        import os
        db_url = os.environ["DATABASE_URL"].replace(
            "postgresql+asyncpg://", "postgresql://"
        ).replace("postgresql+psycopg://", "postgresql://")

        with psycopg.connect(db_url) as conn:
            cur = conn.cursor()
            for r_code in REQUIRED_R_CODES:
                cur.execute(
                    """SELECT COUNT(*) FROM rules
                       WHERE lifecycle_status = 'approved'
                         AND applicable_r_codes @> %s::jsonb""",
                    (f'["{r_code}"]',),
                )
                count = cur.fetchone()[0]
                assert count >= MIN_RULES_PER_R_CODE, (
                    f"{r_code} has only {count} approved rules (need {MIN_RULES_PER_R_CODE})"
                )

    def test_dwelling_types_have_rules(self) -> None:
        """Every dwelling type has at least 10 approved rules."""
        import psycopg
        import os
        db_url = os.environ["DATABASE_URL"].replace(
            "postgresql+asyncpg://", "postgresql://"
        ).replace("postgresql+psycopg://", "postgresql://")

        with psycopg.connect(db_url) as conn:
            cur = conn.cursor()
            for dt in REQUIRED_DWELLING_TYPES:
                cur.execute(
                    """SELECT COUNT(*) FROM rules
                       WHERE lifecycle_status = 'approved'
                         AND dwelling_type = %s""",
                    (dt,),
                )
                count = cur.fetchone()[0]
                assert count >= 10, (
                    f"{dt} has only {count} approved rules (need 10)"
                )

    def test_part_b_instrument_section_coverage(self) -> None:
        """At least 150 approved rules with instrument_section LIKE 'Part B%'."""
        import psycopg
        import os
        db_url = os.environ["DATABASE_URL"].replace(
            "postgresql+asyncpg://", "postgresql://"
        ).replace("postgresql+psycopg://", "postgresql://")

        with psycopg.connect(db_url) as conn:
            cur = conn.cursor()
            cur.execute(
                """SELECT COUNT(*) FROM rules
                   WHERE lifecycle_status = 'approved'
                     AND instrument_section LIKE 'Part B%%'"""
            )
            count = cur.fetchone()[0]
            assert count >= 150, (
                f"Only {count} Part B rules (need 150)"
            )
