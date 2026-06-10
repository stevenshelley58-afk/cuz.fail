"""Unit tests for scripts/wp4_acquire.py pure logic — no Postgres, no network.

Covers lease-claim SQL construction, pre-fetch outcome classification,
fetch-error classification, blocked/metadata_only note formatting (incl. the
one-command unblock), category mapping, and report assembly.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve().parent.parent / "scripts" / "wp4_acquire.py"
_spec = importlib.util.spec_from_file_location("wp4_acquire", SCRIPT_PATH)
wp4 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(wp4)


# ---------------------------------------------------------------------------
# DSN normalisation
# ---------------------------------------------------------------------------


def test_psycopg_dsn_strips_sqlalchemy_drivers() -> None:
    assert wp4.psycopg_dsn("postgresql+psycopg://u:p@h/db") == "postgresql://u:p@h/db"
    assert wp4.psycopg_dsn("postgresql+asyncpg://u:p@h/db") == "postgresql://u:p@h/db"
    assert wp4.psycopg_dsn("postgresql://u:p@h/db") == "postgresql://u:p@h/db"


def test_sqlalchemy_url_forces_psycopg3_driver() -> None:
    assert wp4.sqlalchemy_url("postgresql://u:p@h/db") == "postgresql+psycopg://u:p@h/db"
    assert wp4.sqlalchemy_url("postgresql+asyncpg://u:p@h/db") == "postgresql+psycopg://u:p@h/db"
    assert wp4.sqlalchemy_url("postgresql+psycopg://u:p@h/db") == "postgresql+psycopg://u:p@h/db"


# ---------------------------------------------------------------------------
# Lease-claim SQL (swarm queue)
# ---------------------------------------------------------------------------


def test_claim_sql_default_targets_pending_only_with_skip_locked() -> None:
    sql = wp4.build_claim_sql()
    assert "status IN ('pending')" in sql
    assert "'blocked'" not in sql
    assert "FOR UPDATE SKIP LOCKED" in sql
    assert "claimed_by = %(worker_id)s" in sql
    assert "lease_expires_at < now()" in sql
    assert "make_interval(mins => %(lease_minutes)s)" in sql
    assert "LIMIT %(batch_size)s" in sql
    # no optional filters unless requested
    assert "%(category)s" not in sql
    assert "%(ids)s" not in sql


def test_claim_sql_skips_rows_with_live_leases() -> None:
    sql = wp4.build_claim_sql()
    assert "(claimed_by IS NULL OR lease_expires_at IS NULL OR lease_expires_at < now())" in sql


def test_claim_sql_retry_blocked_reopens_blocked_rows() -> None:
    sql = wp4.build_claim_sql(retry_blocked=True)
    assert "status IN ('pending', 'blocked')" in sql


def test_claim_sql_category_filter_only_when_given() -> None:
    sql = wp4.build_claim_sql(category="state_planning_policy")
    assert "category = %(category)s" in sql


def test_claim_sql_ids_filter_implies_blocked_retry() -> None:
    sql = wp4.build_claim_sql(ids=["abc"])
    assert "id = ANY(%(ids)s::uuid[])" in sql
    assert "status IN ('pending', 'blocked')" in sql


def test_claim_sql_returns_columns_needed_for_processing() -> None:
    sql = wp4.build_claim_sql()
    for column in ("instrument_name", "category", "issuing_authority", "canonical_url", "notes"):
        assert column in sql.split("RETURNING", 1)[1]


def test_claim_sql_never_touches_terminal_statuses() -> None:
    # Idempotence: acquired / metadata_only / out_of_scope are never claimable.
    for sql in (wp4.build_claim_sql(), wp4.build_claim_sql(retry_blocked=True)):
        assert "'acquired'" not in sql
        assert "'metadata_only'" not in sql
        assert "'out_of_scope'" not in sql


# ---------------------------------------------------------------------------
# Pre-fetch classification
# ---------------------------------------------------------------------------


def test_classify_target_without_url_is_no_url() -> None:
    assert wp4.classify_target(None, None, "regulations") == "no_url"
    assert wp4.classify_target("  ", "note", "act") == "no_url"


def test_classify_target_standards_australia_is_metadata_only() -> None:
    assert (
        wp4.classify_target("https://www.standards.org.au/as-3959", None, "standard")
        == "metadata_only"
    )
    assert wp4.classify_target("https://example.gov.au/doc.pdf", None, "standard") == "metadata_only"


def test_classify_target_paid_licence_notes_are_metadata_only() -> None:
    for note in (
        "Landgate paid cadastre",
        "licence-blocked pending DPLH bulk licence",
        "subscription required",
        "Metadata only per CORPUS_SCOPE.md",
    ):
        assert wp4.classify_target("https://example.gov.au/x.pdf", note, "spatial_layer") == (
            "metadata_only"
        )


def test_classify_target_plain_public_url_is_fetch() -> None:
    assert (
        wp4.classify_target(
            "https://www.wa.gov.au/spp7-3.pdf",
            "Includes Schedule 2 deemed provisions",
            "regulations",
        )
        == "fetch"
    )


# ---------------------------------------------------------------------------
# Fetch-error classification
# ---------------------------------------------------------------------------


def test_permanent_fetch_errors_are_recognised() -> None:
    for message in (
        "robots.txt disallows this URL for automated fetch",
        "source requires restricted access: HTTP 403",
        "restricted source URL or licence notes require automated validation",
        "only absolute public HTTP(S) URLs can be fetched",
        "Standards Australia full text is metadata-only unless lawfully supplied",
    ):
        assert wp4.is_permanent_fetch_error(message), message
    assert not wp4.is_permanent_fetch_error("connection reset by peer")


def test_licence_errors_route_to_metadata_only() -> None:
    assert wp4.is_licence_error(
        "Standards Australia full text is metadata-only unless lawfully supplied"
    )
    assert not wp4.is_licence_error("source requires restricted access: HTTP 403")


def test_parse_failure_marker() -> None:
    assert wp4.is_parse_failure("source fetch produced no parseable text")
    assert not wp4.is_parse_failure("HTTP 500")


# ---------------------------------------------------------------------------
# Notes / unblock formatting
# ---------------------------------------------------------------------------


def test_unblock_command_is_a_single_docker_exec() -> None:
    cmd = wp4.unblock_command("11111111-2222-3333-4444-555555555555")
    assert cmd.startswith("docker exec draftcheck-wa-v3-api-1 python /app/scripts/wp4_acquire.py")
    assert "--retry-blocked" in cmd
    assert "--ids 11111111-2222-3333-4444-555555555555" in cmd
    assert "--report" in cmd
    assert "\n" not in cmd


def test_blocked_note_contains_error_attempts_and_unblock() -> None:
    note = wp4.format_blocked_note(
        error="fetch failed after 3 attempts: HTTP 503",
        unblock=wp4.unblock_command("abc"),
        attempts=3,
    )
    assert "BLOCKED after 3 attempt(s)" in note
    assert "HTTP 503" in note
    assert "unblock: docker exec" in note
    assert note.startswith("[wp4 ")


def test_blocked_note_is_truncated_to_note_budget() -> None:
    note = wp4.format_blocked_note(error="x" * 5000, unblock="rerun", attempts=3)
    assert len(note) <= wp4.NOTE_MAX_CHARS


def test_metadata_only_note_states_no_full_text_rule() -> None:
    note = wp4.format_metadata_only_note("Standards Australia licence")
    assert "metadata_only" in note
    assert "full text never stored" in note


def test_unblock_hint_per_failure_class() -> None:
    assert "UPDATE target_manifest" in wp4.unblock_hint("no_url", "mid-1")
    assert "robots.txt" in wp4.unblock_hint("robots", "mid-1", "https://x.gov.au")
    assert "browser" in wp4.unblock_hint("restricted", "mid-1", "https://x.gov.au")
    assert "raw artifact preserved" in wp4.unblock_hint("parse", "mid-1")
    # default/transient = plain rerun
    assert wp4.unblock_hint("transient", "mid-1") == wp4.unblock_command("mid-1")


# ---------------------------------------------------------------------------
# Category / authority mapping
# ---------------------------------------------------------------------------


def test_source_type_for_category_known_and_fallback() -> None:
    assert wp4.source_type_for_category("act") == "legislation"
    assert wp4.source_type_for_category("state_planning_policy") == "state_planning_policy"
    assert wp4.source_type_for_category("standard") == "standard_metadata"
    assert wp4.source_type_for_category("mystery_category") == "source_document"


def test_local_government_only_for_lga_authorities() -> None:
    assert wp4.local_government_for_authority("City of Cockburn") == "City of Cockburn"
    assert wp4.local_government_for_authority("Shire of Mundaring") == "Shire of Mundaring"
    assert wp4.local_government_for_authority("Western Australian Planning Commission") is None


def test_looks_like_pdf_by_type_url_and_magic_bytes() -> None:
    assert wp4.looks_like_pdf(b"", "application/pdf", "https://x/doc")
    assert wp4.looks_like_pdf(b"", "application/octet-stream", "https://x/doc.PDF")
    assert wp4.looks_like_pdf(b"%PDF-1.7", "application/octet-stream", "https://x/doc")
    assert not wp4.looks_like_pdf(b"<html>", "text/html", "https://x/page")


# ---------------------------------------------------------------------------
# Report assembly
# ---------------------------------------------------------------------------


def _outcome(status: str, category: str, name: str = "Doc") -> dict:
    return {
        "manifest_id": "mid",
        "instrument_name": name,
        "category": category,
        "status": status,
        "source_document_id": "sid" if status == "acquired" else None,
        "source_version_id": None,
        "attempts": 1,
        "error": None,
        "note": None,
    }


def test_build_report_counts_by_status_and_category() -> None:
    outcomes = [
        _outcome("acquired", "state_planning_policy"),
        _outcome("acquired", "regulations"),
        _outcome("blocked", "regulations"),
        _outcome("metadata_only", "standard"),
    ]
    report = wp4.build_report(
        worker_id="wp4-test",
        args_summary={"limit": 0},
        outcomes=outcomes,
        manifest_totals={"by_status": {"pending": 3}},
        escalations=["Doc: blocked — HTTP 503"],
        started_at="2026-06-10T00:00:00+00:00",
        finished_at="2026-06-10T00:05:00+00:00",
    )
    assert report["counts"]["processed"] == 4
    assert report["counts"]["by_status"] == {"acquired": 2, "blocked": 1, "metadata_only": 1}
    assert report["counts"]["by_category_status"]["regulations"] == {"acquired": 1, "blocked": 1}
    assert report["rows"] == outcomes
    assert report["escalations"] == ["Doc: blocked — HTTP 503"]
    assert report["manifest_totals_after"] == {"by_status": {"pending": 3}}
    assert report["run"]["worker_id"] == "wp4-test"
    assert report["run"]["args"] == {"limit": 0}


def test_build_report_empty_run_is_valid() -> None:
    report = wp4.build_report(
        worker_id="wp4-test",
        args_summary={},
        outcomes=[],
        manifest_totals={"by_status": {}},
        escalations=[],
        started_at="t0",
        finished_at="t1",
    )
    assert report["counts"]["processed"] == 0
    assert report["counts"]["by_status"] == {}
    assert report["rows"] == []
