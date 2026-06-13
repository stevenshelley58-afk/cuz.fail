"""Tests for the legacy `licence_status` audit + normalization gate."""
from __future__ import annotations

from sqlalchemy import create_engine, text

from scripts.audit_licence_status import (
    KNOWN_LEGACY_ALIASES,
    V3_VALUES,
    _audit_table,
)


def test_audit_classifies_v3_legacy_known_and_other() -> None:
    rows = [("open", 3), ("verified_open", 4), ("approved", 5), ("junk_vocab", 2), (None, 1)]
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as sa_conn:
        sa_conn.exec_driver_sql("CREATE TABLE source_versions (licence_status TEXT)")
        for value, count in rows:
            for _ in range(count):
                sa_conn.execute(
                    text("INSERT INTO source_versions(licence_status) VALUES (:v)"),
                    {"v": value},
                )
        payload = _audit_table(sa_conn, "source_versions")

    assert payload["v3_values"] == {"open": 3, "verified_open": 4}
    assert payload["legacy_known_aliases"] == {"approved": 5}
    assert payload["other_legacy"] == {"junk_vocab": 2}
    assert payload["null_count"] == 1
    # Drift rows = other_legacy + NULLs.
    drift = sum(payload["other_legacy"].values()) + payload["null_count"]
    assert drift == 3


def test_audit_clean_table_reports_zero_drift() -> None:
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as conn:
        conn.exec_driver_sql("CREATE TABLE source_versions (licence_status TEXT)")
        for value in ("open", "verified_open", "pending_review", "metadata_only"):
            conn.exec_driver_sql(
                "INSERT INTO source_versions(licence_status) VALUES (?)", (value,)
            )
    with engine.connect() as conn:
        payload = _audit_table(conn, "source_versions")
    assert payload["other_legacy"] == {}
    assert payload["null_count"] == 0
    assert sum(payload["legacy_known_aliases"].values()) == 0
    # Gate: drift total is 0.
    drift = sum(payload["other_legacy"].values()) + payload["null_count"]
    assert drift == 0


def test_known_legacy_aliases_is_superset_of_library_shim() -> None:
    """The migration must rewrite every alias the runtime shim knows about."""
    from draftcheck.domain.sources.library import _LEGACY_LICENCE_ALIASES

    shim_values = {member.value for member in _LEGACY_LICENCE_ALIASES.values()}
    migration_values = set(KNOWN_LEGACY_ALIASES.values())
    assert shim_values <= migration_values


def test_v3_values_match_enum() -> None:
    from draftcheck.domain.sources.models import LicenceStatus

    assert V3_VALUES == {member.value for member in LicenceStatus}
