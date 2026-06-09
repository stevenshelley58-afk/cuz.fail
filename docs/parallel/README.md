# Parallel Prep Sessions — Map & Isolation Guarantee

Date: 2026-06-09

Four independent Claude Code sessions you can run **at the same time** as the consolidation build
and each other. Each brief defines its own multi-agent roster. They are doc/data-only — none touch
`src/`, `web/`, `db/alembic/`, `models.py`, or `tests/fixtures/golden/`, so they cannot collide with
the consolidation branch or with one another.

| Session | Brief | Sole output path | Touches code? |
|---|---|---|---|
| A | `SESSION_A_SOURCE_CURRENCY.md` | `docs/SOURCE_CURRENCY_AUDIT.md` | No (read + web) |
| B | `SESSION_B_FIXTURE_ASSETS.md` | `data/fixtures/m1/` | No (assets only) |
| C | `SESSION_C_DATA_ACQUISITION.md` | `docs/DATA_ACQUISITION_RUNBOOK.md`, `data/fixtures/samples/` | No (web + data) |
| D | `SESSION_D_STAGE_3_SPEC.md` | `docs/STAGE_3_BUILD.md` | No (spec doc) |

**Isolation rule for all four:** write only to your listed output path. If you believe you need to
edit code, stop and record it as a follow-up in your output doc — do not edit `src/`, `web/`,
migrations, or `pyproject.toml`. This keeps every session safely concurrent.

**Shared safety invariants (all sessions):** all-AI pipeline, no human reviewer/approval gate;
outputs advisory/cited, never a final certification; no superseded source supports an answer; legal/
numeric values in any asset are **illustrative**, never authoritative — hardcoding one as truth is a
defect. Authority: `docs/MASTER_REBUILD_PLAN.md` (V3), `docs/ROAD_TO_PROD.md`, `docs/M1_GOLDEN_FIXTURE.md`.
