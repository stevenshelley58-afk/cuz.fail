# Master Plan Addendum

Date: 2026-06-06

**SUPERSEDED:** See `docs/MASTER_REBUILD_PLAN.md`. This file is background context only
for the V3 rebuild where it conflicts with the rebuild plan.

Status: authoritative addendum to `docs/MASTER_IMPLEMENTATION_PLAN.md`.

This addendum records the required corrections from the 2026-06-06 review and the repo-truth deltas
from `REPO_AUDIT.md`. If this file and an older planning document disagree, this file wins. If this
file and `docs/MASTER_IMPLEMENTATION_PLAN.md` disagree, update the master plan before implementation
continues.

## Required Implementation Corrections

1. Address resolver payload:
   - Use `resolution_status`, not `status: "high"`.
   - `confidence` remains `high | medium | low`.
   - `resolution_status` is `resolved | missing_info | needs_human_review | unsupported`.

2. Rule statuses:
   - `RuleExtractionCandidate.status = candidate | pending_review | rejected`.
   - `RuleRow.lifecycle_status = auto_accepted | approved | pending_review | rejected | stale |
     superseded`.
   - Deprecated: `needs_review`.

3. ClauseDisposition:
   - Canonical values: `rule_bearing | definition | procedural | informational | manual_review`.
   - Deprecated aliases: `definitions`, `fluff`.
   - Migration: `definitions -> definition`; `fluff -> informational` unless normative-language audit
     flags the clause.

4. AddressFact:
   - Store as row-per-fact with `fact_type`, `value_json`, `confidence`, `method`,
     `spatial_dataset_id`, `source_version_id`, `planning_layer_feature_id`, `effective_from`,
     `effective_to`, `stale_at`, and `review_status`.
   - Do not store `overlays[]` as an opaque list if each overlay needs independent provenance.

5. Assessment date:
   - Every resolved-rules and compliance run must carry `as_of_date`.
   - Add `lodgement_date` and `assessment_basis` to `Project`.
   - Every `ResolvedRule` selection must be made against an explicit date.

6. Proposal facts:
   - Add `ProjectProposal`.
   - Do not treat `dwelling_type` or `proposal_type` as address facts.

7. Source/project parsing:
   - A shared parser package is allowed.
   - Agent B alone writes `SourceArtifact`.
   - Agent E alone writes `DocumentArtifact`, `DrawingEntity`, and `DrawingMeasurement`.
   - Parser services return outputs; owning services persist them.

8. Property migration:
   - Do not convert `Property` to a DB view until a write-path audit proves it is safe.
   - First add `address_profile_id` and keep backward-compatible fields.

9. DecisionTrace:
   - Add unit conversions, rounding policy, tolerance, input sources, applicability trace,
     precedence trace, engine version, rule snapshot hash, and measurement snapshot hash.

10. DB image:
   - Verify both PostGIS and pgvector are installed.
   - If the selected PostGIS image lacks pgvector, build a custom DB image or use a proven image that
     includes both.

## Canonical Endpoint Set

Use these as final:

```text
POST /v1/address/resolve
POST /v1/projects/{id}/property/resolve
GET  /v1/projects/{id}/property/profile
POST /v1/projects/{id}/resolved-rules
POST /v1/projects/{id}/compliance/run
GET  /v1/projects/{id}/compliance/matrix
```

Deprecated aliases:

```text
POST /v1/properties/resolve
POST /v1/projects/{id}/address-profile/build
GET  /v1/projects/{id}/address-profile
GET  /v1/projects/{id}/spatial-facts
POST /v1/projects/{id}/checks/run
GET  /v1/projects/{id}/compliance-matrix
```

Keep aliases for backwards compatibility where practical, but mark them deprecated in OpenAPI.

## Repo-Truth Deltas

Observed current state from `REPO_AUDIT.md`:

- The router is mounted at both `/v1` and `/api`. Treat `/v1` as canonical and `/api` as compatibility
  only.
- `POST /v1/address/resolve`, project-scoped property resolution, resolved-rules, and the final
  compliance matrix route are not implemented yet.
- `Property` is actively written by `ProjectService.upsert_property()`.
- No active code writes `PlanningOverlay`.
- Current compliance uses 25 seed `DEFAULT_CHECKS` and can emit pass/fail without the future
  `ResolvedRule` and `DecisionTrace` preconditions.
- Current parsing uses pypdf, python-docx, BeautifulSoup, text decoding, and a handwritten DXF parser.
  Source ingestion uses a separate regex clause splitter.
- Retrieval is keyword/SQLite FTS plus lexical scoring. `SourceChunk.embedding_ref`, the mock
  embedding provider, and pgvector dependency are not wired into a vector schema.
- Root `docker-compose.yml` uses plain `postgres:16`; production/VPS compose files do not yet include
  DB, Redis, MinIO, or Caddy.
- Existing tests are green: 23 passed across 8 test files.

## Implementation Sequencing Lock

Do not start migrations before the PR 1 audit and plan-lock artifacts are committed.

Authorized first PR order:

```text
PR 1: repo audit + plan lock
PR 2: infrastructure foundation
PR 3: source artifact + licence gate
PR 4: clause and rule foundation
PR 5: spatial data skeleton + resolver contract
```

Every later PR that adds regulatory output must include a status, citation or explicit refusal path,
and an eval/test case for the new behavior. No export is submission-ready without human signoff.
# SUPERSEDED - see docs/MASTER_REBUILD_PLAN.md

This file is background context only for the V3 rebuild. Do not use it as implementation
authority where it conflicts with `docs/MASTER_REBUILD_PLAN.md`.
