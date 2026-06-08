# Plan Lock Notice

Date: 2026-06-06

**SUPERSEDED:** See `docs/MASTER_REBUILD_PLAN.md`. This file is background context only
for the V3 rebuild. Its earlier backend-only and `/v1` lock rules no longer govern implementation.

The active implementation source is:

```text
docs/MASTER_IMPLEMENTATION_PLAN.md
MASTER_PLAN_ADDENDUM.md
REPO_AUDIT.md
AGENTS.md
```

When these documents disagree with older planning documents, the active implementation source wins.

Older documents may remain useful for background context, but they are not implementation authority
where they conflict with the master plan or addendum:

```text
docs/GAP_ANALYSIS.md
docs/SPATIAL_ENGINE_DESIGN.md
docs/FRONTEND_API_WIRING.md
docs/FRONTEND_HANDOFF.md
docs/ARCHITECTURE.md
docs/API_CONTRACT.md
docs/RULES_EXTRACTION_PIPELINE.md
docs/SOURCE_GOVERNANCE.md
docs/SOURCE_LIBRARY_AUDIT.md
docs/DATA_SOURCES.md
docs/HERMES_SCRAPE_JOB.md
docs/LEGAL_AND_LICENSING_NOTES.md
```

Specific lock rules:

- Use `RuleRow`, `CheckDefinition`, `ResolvedRule`, and `DecisionTrace` as the canonical legal and
  compliance model.
- Use `POST /v1/address/resolve` as the canonical address resolver endpoint.
- Use `resolution_status` for address resolution state; do not overload `status`.
- Use row-per-fact `AddressFact`; do not persist opaque overlay lists as authoritative facts.
- Do not convert `Property` to a DB view until a fresh write-path audit proves no code writes it.
- Do not scrape or store paid Australian Standards full text.
- Do not add frontend/browser UI in this repository.
# SUPERSEDED - see docs/MASTER_REBUILD_PLAN.md

This file is background context only for the V3 rebuild. Its earlier backend-only and `/v1`
lock rules are superseded by `docs/MASTER_REBUILD_PLAN.md`.
