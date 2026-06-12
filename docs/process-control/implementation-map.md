# LotFile — Process Control / Source-Governance Feature
## Implementation Map (Phase 1 deliverable)

**Status:** Plan only. No code has been written. Awaiting operator review before Phase 2.

**Date:** 2026-06-10
**Owner:** LotFile team
**Authority:** This map is a sub-plan that must remain consistent with `docs/MASTER_REBUILD_PLAN.md`, `AGENTS.md`, and `CLAUDE.md`. If any future conflict is found, the active implementation source wins.

---

## 1. Scope reality check

This is **not** a generic Quality Management System (QMS) product. It is also **not** an ISO 9001 / GRC platform.

What it actually is: **a governance layer over LotFile's own production pipeline** — the way LotFile ingests regulatory sources, extracts rules, runs compliance checks, cites evidence, validates exports, runs evals, and remediates defects. The brief is the control framework; the implementation lives inside LotFile and reuses LotFile's existing primitives.

Mapping anchor (locked, no relitigation):

| Brief concept | LotFile equivalent (locked mapping) |
| --- | --- |
| ControlledDocument | Regulatory `Source` + `SourceVersion` (one source document, many versions) |
| Process | A LotFile pipeline stage (e.g. ingestion, extraction, retrieval, compliance check, export) |
| ProcessStep | A concrete backend function/job (e.g. `source.fetch`, `rule.extract`, `check.run`, `export.validate`) |
| Risk | Compliance / extraction / citation / freshness / source-conflict / export-validation risk |
| Control | Deterministic validator, eval gate, source-acceptance gate, reviewer approval, CI assertion |
| Evidence | `SourceCitation`, extracted `Clause`, `SourceChunk`, `ResolvedRule` citation, `CheckResult.decision_trace_json`, `ExportValidation`, `AuditEvent`, `JobTrace`, `EvalRun` |
| KPI | Source coverage, extraction accuracy, citation completeness, stale-source rate, failed-check rate, export-validation failure rate, eval pass rate |
| CAPA | Accepted `ReviewItem`, `RfiItem`, rule `extractor` defect, `EvalRun` failure follow-up, `Task`-style remediation item |
| GovernanceReview | Periodic source/eval/control review pack (evidence assembly) |

**Non-goals carried over from the brief, with LotFile framing:**

- No BPMN editor. The pipeline is code; the registry of pipeline stages is a code/config artefact.
- No GRC platform. We do not replace external GRC tools.
- No external regulatory interpretation engine. LotFile cites approved sources; it does not interpret regulation.
- No automatic legal / planning / building / certification sign-off. Per `AGENTS.md` §"Pipeline and output governance": outputs are advisory (`likely_pass / likely_fail / needs_more_info / unsupported`), never final certifications.
- No uncontrolled AI auto-fixes. AI findings are *proposed findings*; human acceptance is required before they become remediation (CAPA) items.
- No new auth system, no new analytics stack, no new document storage.

**Hard constraints respected by this map (from `AGENTS.md` and `CLAUDE.md`):**

1. Backend-first. No browser UI for this feature. If a UI is later requested, it is a separate PR.
2. Same-origin, no cross-origin cookies, no `VITE_API_BASE_URL`, single Caddy-mounted `/api/v1`.
3. All new schema is Alembic, never `create_all()`. PR0 already added `tests/test_v3_schema_contract.py::test_v3_source_code_does_not_call_create_all` — the contract test is part of the gate.
4. AI is a *traced, skill-versioned, spend-capped* adapter. No AI call may run outside that pattern, and AI may never decide compliance verdicts.
5. Operator standing approval is in force. This map is the handoff for that approval; it logs the design decision and the constraints it will run under.

---

## 2. Existing repo systems reused (with file:line evidence)

This is what already exists and what the new feature will sit on top of. **Every line below was read from the current source tree on 2026-06-10, not from the older audit doc** — the older `REPO_AUDIT.md` was partly out of date (e.g. it pointed at `apps/` and `packages/core/`, but V3 lives under `src/draftcheck/`).

### 2.1 Models reused (file: `src/draftcheck/db/models.py`)

| Existing model | Location (line) | Used as |
| --- | --- | --- |
| `Source` (table `source_documents`) | `src/draftcheck/db/models.py:345` | ControlledDocument parent. Carries `authority`, `canonical_url`, `jurisdiction`, `local_government`, `source_type`, `access_type`, `status`, `metadata_json`. |
| `SourceVersion` (table `source_versions`) | `src/draftcheck/db/models.py:370` | ControlledDocument version. Carries `version_label`, `sha256`, `licence`, `licence_status`, `review_status`, `effective_from/to`, `published_at`, `fetched_at`, `superseded_by_version_id`, `metadata_json`. |
| `SourceReviewRecord` (table `source_reviews`) | `src/draftcheck/db/models.py:485` | **Already** the source-acceptance control record. Carries `review_status`, `licence_status`, `notes`, `reviewed_at`, `decision_metadata_json`. |
| `SourceFetchLog` (table `source_fetch_log`) | `src/draftcheck/db/models.py:518` | Evidence of fetch attempts for freshness/staleness audits. |
| `SourceChunk` (table `source_chunks`) | `src/draftcheck/db/models.py:403` | Citable chunk with `embedding`. |
| `SourceCitation` (table `source_citations`) | `src/draftcheck/db/models.py:458` | Citation rows linking chunks to versions with `quote` and `citation_json`. |
| `Artifact` (table `artifacts`) | `src/draftcheck/db/models.py:558` | Immutable evidence blob with `sha256`, `parser_name`, `parser_version`. |
| `JobTrace` (table `job_traces`) | `src/draftcheck/db/models.py:585` | Traced LLM call: `adapter_name`, `provider`, `model`, `skill_version_id`, `prompt_hash`, `input/output_artifact_id`, `spend_cap_cents`, `spend_cap_tokens`, `cost_usd`, `status`, `started_at/finished_at`, `error`. **This is exactly what AI finding provenance should record.** |
| `SpendEvent` (table `spend_events`) | `src/draftcheck/db/models.py:636` | Spend-cap enforcement row linked to `job_trace_id`. |
| `SpatialDataset` (table `spatial_datasets`) | `src/draftcheck/db/models.py:668` | Same lifecycle fields as `SourceVersion` (`licence_status`, `approval_status`) — for spatial inputs. |
| `Clause` (table `clauses`) | `src/draftcheck/db/models.py:877` | Extracted clause with `disposition` (used by the validator runner). |
| `SkillVersion` (table `skill_versions`) | `src/draftcheck/db/models.py:921` | Tracked skill version. |
| `RuleCandidate` (table `rule_candidates`) | `src/draftcheck/db/models.py:946` | Pre-promotion rule. Has `validator_results_json`, `review_status` enum (`pending_review / validators_passed / validator_failed / eval_failed / auto_promoted`), `extractor_model`, `skill_version_id`, `prompt_hash`, `confidence`, `extraction_group_id`, `extraction_pass`, `quote_char_start/end`, `auto_promoted_at`. |
| `Rule` (table `rules`) | `src/draftcheck/db/models.py:1013` | Promoted rule with `lifecycle_status` (`pending_review / auto_accepted / approved / retired / ...`), `superseded_by_rule_id`, `council_scope`, `applicable_zones`, `applicable_r_codes`. |
| `RuleClauseLink` (table `rule_clause_links`) | `src/draftcheck/db/models.py:1083` | Rule↔clause traceability with `link_type` and `quote`. |
| `LegalEdge` (table `legal_edges`) | `src/draftcheck/db/models.py:1115` | Cross-document legal relations (`from_type/from_ref`, `to_type/to_ref`, `relation`, `evidence_quote`, `review_status`). **Used for "conflicting source rules" detection.** |
| `CheckRun` (table `check_runs`) | `src/draftcheck/db/models.py:1143` | A single deterministic compliance run with `as_of_date`, `rule_pack_hash`, `source_version_ids_json`, `engine_version`, `status`. |
| `ResolvedRule` (table `resolved_rules`) | `src/draftcheck/db/models.py:1186` | The rule actually applied for a project/check: `applicability_status`, `precedence_rank`, `rule_snapshot_json`, `selection_trace_json`, `citations_json`. |
| `CheckResult` (table `check_results`) | `src/draftcheck/db/models.py:1228` | Result row with `status` (`likely_pass / likely_fail / needs_more_info / unsupported / ...`), `requirement_json`, `proposed_json`, `why_this_applies`, `citations_json`, `decision_trace_json`, `pathway_note`, `human_override_json`, `reviewed_by_user_id`, `reviewed_at`. |
| `Export` (table `exports`) | `src/draftcheck/db/models.py:1556` | Export job with `status`, `manifest_json`, `storage_path`, `sha256`, `sections_json`. |
| `EvalCase` (table `eval_cases`) | `src/draftcheck/db/models.py:1630` | Golden fixture: `suite_name`, `case_key`, `skill_name`, `input_json`, `expected_json`, `status`. |
| `EvalRun` (table `eval_runs`) | `src/draftcheck/db/models.py:1653` | Single eval result: `status`, `score`, `output_json`, `metrics_json`, `job_trace_id`. |
| `AuditEvent` (table `audit_events`) | `src/draftcheck/db/models.py:1689` | Append-only governance log. `event_type`, `action`, `subject_type/subject_id`, `before_json`, `after_json`, `metadata_json`, `request_id`, `ip_address`, `actor_user_id`. |
| `ReviewItem` (table `review_items`) | `src/draftcheck/db/models.py:1722` | **The closest existing primitive to a CAPA.** `subject_type`, `subject_id`, `reason`, `status` (`open / resolved / ...`), `priority`, `assigned_user_id`, `due_at`, `resolved_by_user_id`, `resolved_at`. Already 155 rows. |
| `RfiItem` (table `rfi_items`) | `src/draftcheck/db/models.py:1454` | Per-project remediation item with `severity`, `status`, `due_at`, `resolved_at`, `source_json`. |
| `ResponseDraft` (table `response_drafts`) | `src/draftcheck/db/models.py:1503` | Drafted AI response with `human_edited`, `edited_by_user_id`. |
| `Org`, `User`, `Session`, `MagicLinkToken` | `src/draftcheck/db/models.py:119,142,176,208` | Identity. **Note: RBAC today is binary `OWNER | OPERATOR` only — see §3 and §8.** |

### 2.2 Routers reused (file: `src/draftcheck/api/v1.py` and sibling routers)

The new feature will mount under `/api/v1/governance/*` and piggyback on the existing `/api/v1` surface, not duplicate it.

| Existing router | File | Endpoints reused for governance |
| --- | --- | --- |
| `health_router` | `src/draftcheck/api/health.py` | `/api/v1/health`, `/api/v1/ready` — readiness probes for the audit. |
| `auth_router` | `src/draftcheck/api/auth.py` | `get_current_session` — the only auth dependency. |
| `address_router`, `projects_router`, `sources_router`, `documents_router`, `rules_router`, `compliance_router` | `src/draftcheck/api/*.py` | Read-side access to the existing primitives that governance inspects. |
| `/api/v1/ops/dashboard` | `src/draftcheck/api/v1.py:141` | Source-ingestion dashboard the governance endpoints can also surface as a small JSON view (no UI). |
| `/api/v1/jobs/{job_id}`, `/retry`, `/cancel`, `/traces` (stubs in `v1.py:323`) | `src/draftcheck/api/v1.py:323` | Pattern reused for the AI finding background job. |
| `/api/v1/rules/candidates/{id}/promote\|reject` (stub) | `src/draftcheck/api/v1.py:252` | Existing endpoint *promote/reject* is already an "AI finding → human decision" seam. |

### 2.3 Background job / queue patterns reused

- `JobTrace` (model) + `src/draftcheck/agent/hermes.py` patterns: skill-versioned, prompt-hashed, spend-capped traces.
- `src/draftcheck/jobs/extraction.py` and `src/draftcheck/jobs/embedding.py` are the canonical job layout.
- `src/draftcheck/ai/db_trace_store.py` — DB-backed trace persistence pattern.
- `src/draftcheck/ai/substrate.py` — provider adapter abstraction (we will **not** add a new one; the brief explicitly forbids it).

### 2.4 Audit / event systems reused

- `AuditEvent` model + existing emission in `src/draftcheck/domain/rules/gate.py:262` (auto_promote writes one).
- `src/draftcheck/observability.py` — Sentry init / structured logging.
- `src/draftcheck/api/main.py:40` — request_id middleware that already stamps every request with `x-request-id`. The audit script can group by this.

### 2.5 Eval / test systems reused

- `src/draftcheck/eval/runner.py` — `run_eval_case(eval_case_id, skill_version_id, run_fn, session, score_fn=exact_match_score, job_trace_id=...)`. Reused to score *proposed findings* before they become CAPA-eligible.
- `src/draftcheck/eval/seeds.py` — eval case seed pattern.
- Existing pytest harness in `tests/` (23 files, see §9).

### 2.6 Export validation systems reused

- `Export` model with `manifest_json` and `sha256` (note: a future `ExportValidation` table is mentioned in the older audit but is **not** in the current V3 models). For the moment, validation lives in `manifest_json` + CI check + `EvalRun` results. We will **not** recreate the older `ExportValidation` table — we will reuse `Export.manifest_json` and the existing `EvalRun` rows.

### 2.7 Document / source ingestion systems reused

- `src/draftcheck/domain/sources/` (8 files: `library.py`, `sqlalchemy_store.py`, `models.py`, `fetching.py`, `store/*.py`) — full source-library CRUD.
- `src/draftcheck/domain/sources/sqlalchemy_store.py` — durable SQL source store.
- `src/draftcheck/agent/clause_parser.py` — clause extraction pipeline.
- `src/draftcheck/extraction/validators.py` — `run_all_validators(quote, clause_text, disposition, value_json, unit, rule_key)` — **already a "control"**.

### 2.8 RBAC today (important gap)

- `src/draftcheck/domain/identity/roles.py` defines `IdentityRole = {OWNER, OPERATOR}`. The brief asks for `viewer | process_owner | qa_lead | compliance_owner | admin`. The new feature will **need** at least a new `compliance_owner` (or `auditor`) role. The test `tests/test_v3_schema_contract.py:16` currently pins the role enum to exactly these two values, so a third role requires an Alembic migration to extend the enum and an update to that contract test. This is called out as a real piece of work in §5 and §8.

---

## 3. Concept mapping table

Brief concept → LotFile equivalent → existing model/file → gap → proposed action.

| Brief concept | LotFile equivalent | Existing model/file | Gap | Proposed action |
| --- | --- | --- | --- | --- |
| ControlledDocument | `Source` (parent) + `SourceVersion` (version) | `models.py:345, 370`; `docs/SOURCE_GOVERNANCE.md` | No explicit `owner_user_id` field on either; the brief asks for it. | **Reuse.** Add `owner_user_id` and `review_due_date` to `SourceVersion` via a new Alembic revision (see §5). The rest of the brief's ControlledDocument fields (title, version, status, etc.) already exist. |
| Process | A pipeline stage code/config object | No `Process` table exists | Pipeline stage is currently an implicit concept (functions under `src/draftcheck/jobs/` and packages). | **New lightweight registry** (see §5) — a `PipelineStage` table or a config-driven registry. The brief treats "Process" as the *thing being governed*, but the actual governance work happens at the `ProcessStep` level. |
| ProcessStep | A concrete backend function or job (e.g. `source.fetch`, `rule.extract`, `check.run`, `export.validate`, `eval.run`) | `src/draftcheck/jobs/extraction.py`, `src/draftcheck/jobs/embedding.py`, `src/draftcheck/checks/engine.py`, `src/draftcheck/eval/runner.py` | No central registry. | **Add a `process_steps` reference table** (id, stage, function_path, owner_role, is_critical) — *not* a behavioural change. Each existing function annotates itself in this table at registration time. |
| Risk | A category of failure: compliance, extraction, citation, freshness, conflict, export, eval | Implicit in `RuleCandidate.review_status`, `ReviewItem`, `EvalRun.status`, `SourceVersion.licence_status/review_status` | No first-class `Risk` table that the audit can iterate over. | **Add a `governance_risks` reference table** (code, description, severity, default_control_ids) — see §5. |
| Control | A deterministic check that detects/prevents the risk: validators, eval gate, source-acceptance gate, CI assertion, reviewer approval | `src/draftcheck/extraction/validators.py`, `src/draftcheck/domain/rules/gate.py` (validators + eval gate + auto_promote), `src/draftcheck/api/v1.py:252` (human promote/reject) | No central registry. | **Add a `governance_controls` table** (code, risk_code, control_type, control_function, owner_role, test_frequency, last_tested_at) — see §5. The actual implementations are the existing functions; the table is the registry. |
| Evidence | Citation, clause, source version, audit event, job trace, eval result, export manifest, decision trace | `SourceCitation`, `Clause`, `JobTrace`, `AuditEvent`, `EvalRun`, `Export.manifest_json`, `CheckResult.decision_trace_json` | No "evidence pack" view. | **Reuse.** Add a read-only query layer that materialises an evidence pack for a given (period, scope) — no new storage. |
| KPI | Source coverage, extraction accuracy, citation completeness, stale-source rate, failed-check rate, export-validation failure rate, eval pass rate | All measurable today from existing rows | No KPI table; all KPI numbers must currently be hand-computed from SQL. | **Add a `governance_kpis` table** (code, sql_template, threshold values) and a `governance_kpi_results` table. This is read-side; the SQL is the source of truth. (See §5.) |
| CAPA | Accepted `ReviewItem`, accepted AI-proposed finding, `RfiItem`, eval failure follow-up, remediation `Task` | `ReviewItem` (closest), `RfiItem` (per-project), `AuditEvent` (provenance) | `ReviewItem` doesn't carry `severity` or `root_cause` fields, and the brief wants CAPA to require `closure_evidence` and `effectiveness_check`. `RfiItem` is project-scoped, not pipeline-scoped. | **Reuse `ReviewItem` for pipeline-scope CAPAs.** Extend it with `severity`, `root_cause`, `closure_evidence_id` (FK → `Artifact`), `effectiveness_check_due_date`, `effectiveness_result`, `proposed_by_finding_id` (FK → proposed-finding table). This is a small additive migration on an existing table. |
| TrainingRecord | Not in scope | n/a | The brief is for LotFile's own SDLC. Training records are HR/people-process concerns, not software process concerns. | **Drop.** Out of scope. See §11. |
| GovernanceReview | A periodic evidence pack of source/eval/control review data | Currently produced ad-hoc in `docs/SOURCE_LIBRARY_AUDIT.md`, `docs/SOURCE_CURRENCY_AUDIT.md` | No first-class review record. | **Add a `governance_reviews` table** (review_type, period, summary, evidence_pack_refs) — see §5. The review record is a wrapper around the evidence pack; the pack itself is read-only. |
| AI review workflow | The pattern "AI proposes → validators → eval gate → human accepts/rejects" | `src/draftcheck/domain/rules/gate.py:44-187` (the entire promotion gate chain) | No generic "proposed finding" entity. Today this is hard-coded to `RuleCandidate`. | **Generalise the gate into a `governance_findings` table** (see §5 and §7). Statuses: `proposed | accepted | rejected | converted_to_capa`. The existing `RuleCandidate` flow becomes a *consumer* of the new finding, not the owner of the pattern. |

---

## 4. Proposed backend API surface

All routes mount under `/api/v1/governance/`. All responses are JSON. All write endpoints require an active session (via `get_current_session`); role checks are enforced per-endpoint.

Naming follows the existing convention: plural resources, kebab-case paths, `id` as a UUID. None of these conflict with the locked `/api/v1` surface.

### 4.1 `/api/v1/governance/sources` — controlled-document governance

| Method | Route | Purpose | Backing model |
| --- | --- | --- | --- |
| `GET` | `/api/v1/governance/sources` | List sources with review/freshness metadata. | `Source`, `SourceVersion` |
| `GET` | `/api/v1/governance/sources/{source_id}` | Single source + all versions + review records. | `Source`, `SourceVersion`, `SourceReviewRecord` |
| `GET` | `/api/v1/governance/sources/{source_id}/freshness` | Days since last fetch, days past `effective_to`, days since last successful review. | `SourceVersion`, `SourceFetchLog`, `SourceReviewRecord` |
| `GET` | `/api/v1/governance/sources/{source_id}/conflicts` | Cross-version and cross-document rule conflicts via `LegalEdge`. | `LegalEdge`, `Rule`, `SourceVersion` |
| `POST` | `/api/v1/governance/sources/{source_id}/owner` | Set `owner_user_id` and `review_due_date` on `SourceVersion`. | `SourceVersion` |
| `POST` | `/api/v1/governance/sources/{source_version_id}/supersede` | Mark a version superseded; wire `superseded_by_version_id`. | `SourceVersion` |
| `POST` | `/api/v1/governance/sources/{source_version_id}/retire` | Mark status=retired. | `SourceVersion` |

### 4.2 `/api/v1/governance/pipeline-steps` — process / step registry

| Method | Route | Purpose | Backing model |
| --- | --- | --- | --- |
| `GET` | `/api/v1/governance/pipeline-steps` | List all registered pipeline steps. | `process_steps` (new) |
| `GET` | `/api/v1/governance/pipeline-steps/{step_id}` | Single step with linked risks and controls. | `process_steps`, `governance_risks`, `governance_controls` |

The registry is populated by an Alembic-seeded reference set + a small introspection helper that lists `src/draftcheck/jobs/*` and the `checks.engine` entrypoints. There is no write endpoint — the registry is config.

### 4.3 `/api/v1/governance/controls` — control registry + test results

| Method | Route | Purpose | Backing model |
| --- | --- | --- | --- |
| `GET` | `/api/v1/governance/controls` | List controls (with `last_tested_at`, `next_due_at`, `pass_rate`). | `governance_controls`, `EvalRun` |
| `POST` | `/api/v1/governance/controls/{control_id}/test` | Trigger a control test. Reuses the existing `JobTrace` + `EvalRun` pattern. | `JobTrace`, `EvalRun` |
| `GET` | `/api/v1/governance/controls/{control_id}/results` | Recent test results (most recent `EvalRun` rows where `skill_name = control_id`). | `EvalRun` |

### 4.4 `/api/v1/governance/evidence` — evidence search + pack assembly

| Method | Route | Purpose | Backing model |
| --- | --- | --- | --- |
| `GET` | `/api/v1/governance/evidence` | Search evidence by linked object (source_version_id, project_id, check_run_id, rule_id, finding_id). | Multi-model: `SourceCitation`, `Clause`, `AuditEvent`, `JobTrace`, `EvalRun`, `Artifact`, `CheckResult.decision_trace_json` |
| `GET` | `/api/v1/governance/evidence/pack` | Generate an evidence pack for a `(period_start, period_end, scope)` window. | Read-only query over the same models. |
| `GET` | `/api/v1/governance/evidence/pack.{csv\|json}` | Stream the pack as JSON (CSV deferred; see §11). | Same. |

### 4.5 `/api/v1/governance/findings` — proposed-finding queue (the AI review workflow)

| Method | Route | Purpose | Backing model |
| --- | --- | --- | --- |
| `GET` | `/api/v1/governance/findings` | List findings, filterable by `status`, `severity`, `risk_code`, `proposed_by_job_trace_id`, `subject_type/subject_id`. | `governance_findings` (new) |
| `GET` | `/api/v1/governance/findings/{finding_id}` | Single finding with linked evidence + `JobTrace`. | `governance_findings`, `JobTrace`, `Artifact` |
| `POST` | `/api/v1/governance/findings` | Create a finding (proposed). Body: `risk_code`, `severity`, `subject_type`, `subject_id`, `summary`, `evidence_refs[]`, `proposed_remediation`. | `governance_findings` |
| `POST` | `/api/v1/governance/findings/{finding_id}/accept` | Human accepts the finding. Requires `reason`, `linked_evidence_id`, `actor_user_id` (from session). Sets status=accepted. | `governance_findings`, `ReviewItem` (CAPA created) |
| `POST` | `/api/v1/governance/findings/{finding_id}/reject` | Human rejects. Requires `reason`. Sets status=rejected. | `governance_findings` |
| `POST` | `/api/v1/governance/findings/{finding_id}/convert-to-capa` | Converts accepted finding into a `ReviewItem` (CAPA). Requires `severity`, `owner_user_id`, `due_at`. Sets status=converted_to_capa. | `governance_findings`, `ReviewItem` |

### 4.6 `/api/v1/governance/capa` — CAPA board

| Method | Route | Purpose | Backing model |
| --- | --- | --- | --- |
| `GET` | `/api/v1/governance/capa` | List CAPA items, filterable by `status`, `severity`, `owner_user_id`, overdue. | `ReviewItem` (extended) |
| `GET` | `/api/v1/governance/capa/{capa_id}` | Single CAPA + linked finding + closure evidence. | `ReviewItem`, `governance_findings`, `Artifact` |
| `PATCH` | `/api/v1/governance/capa/{capa_id}` | Update fields. Closing requires `closure_evidence_id` and `effectiveness_check_due_date`. | `ReviewItem`, `Artifact` |
| `POST` | `/api/v1/governance/capa/{capa_id}/verify` | Mark closure verified. Requires `actor_user_id`, `note`. | `ReviewItem` |

### 4.7 `/api/v1/governance/reviews` — governance review records

| Method | Route | Purpose | Backing model |
| --- | --- | --- | --- |
| `GET` | `/api/v1/governance/reviews` | List reviews. | `governance_reviews` (new) |
| `POST` | `/api/v1/governance/reviews` | Create review with `review_type`, `period_start`, `period_end`, `summary`, `decisions_json`, `open_actions_json`, `evidence_pack_refs_json`. | `governance_reviews` |
| `GET` | `/api/v1/governance/reviews/{review_id}` | Single review + linked evidence pack metadata. | `governance_reviews`, plus read-only query to the evidence pack. |

### 4.8 `/api/v1/governance/audit-report` — read-only audit summary

| Method | Route | Purpose | Backing model |
| --- | --- | --- | --- |
| `GET` | `/api/v1/governance/audit-report` | Returns the full governance state: count of overdue CAPAs, count of failing controls, count of stale sources, count of `proposed` findings older than N days, list of recent AuditEvents. Same output as the audit script. | All governance tables + AuditEvent. |
| `GET` | `/api/v1/governance/kpis` | List KPI snapshots (current values + thresholds). | `governance_kpis`, `governance_kpi_results` |

The endpoints above are the only governance surface. **No `/api/v1/governance/login`, no admin role-elevation, no "approve anything without audit_event" path.** Every write endpoint writes an `AuditEvent` (existing pattern in `src/draftcheck/domain/rules/gate.py:262`).

---

## 5. Schema plan

**No migration is included in this Phase 1 deliverable.** This section is the design contract for Phase 2 (new Alembic revision). The PR0 contract test `tests/test_v3_schema_contract.py:33` (`test_v3_source_code_does_not_call_create_all`) is a hard gate.

For every proposed table/column, the question is: *why can't existing schema cover it?* If the answer is "it can, we just don't query it that way," we don't add a new table — we add a query/view layer.

### 5.1 Existing tables extended (additive, non-breaking)

| Table | Proposed additions | Why existing cannot cover |
| --- | --- | --- |
| `SourceVersion` | `owner_user_id` (UUID, FK→users, nullable), `review_due_date` (Date, nullable), `next_required_action` (str, nullable, computed hint) | Brief explicitly requires `owner_user_id` and `review_due_date`. The current `metadata_json` is the wrong place — it's not queryable, and the brief needs filters/joins. |
| `ReviewItem` | `severity` (str, default "normal"), `root_cause` (text, nullable), `closure_evidence_id` (UUID, FK→artifacts, nullable), `effectiveness_check_due_date` (Date, nullable), `effectiveness_result` (text, nullable), `proposed_by_finding_id` (UUID, FK→governance_findings, nullable), `converted_from_finding_id` (UUID, FK→governance_findings, nullable) | Existing `ReviewItem` is a generic subject+reason+status row. The brief's CAPA semantics (severity, root_cause, closure_evidence, effectiveness check) do not exist on it. |
| `SkillVersion` (no change) | n/a | Already covers the skill-version requirement. |
| `JobTrace` (no change) | n/a | Already covers AI call provenance (adapter, provider, model, skill_version, prompt_hash, spend caps). |

### 5.2 New reference / registry tables (small, mostly static)

| Table | Purpose | Why new |
| --- | --- | --- |
| `governance_pipeline_steps` | Registry of pipeline steps. Columns: `id` (UUID), `stage` (str), `function_path` (str), `description` (text), `is_critical` (bool, default false), `owner_role` (str, default "operator"). | No central registry exists. The audit must be able to *enumerate* steps, not just inspect whatever ran. |
| `governance_risks` | Registry of named risks. Columns: `id` (UUID), `code` (str, unique), `name` (str), `description` (text), `severity` (str), `default_owner_role` (str). | The audit needs to enumerate risks. Existing `RuleCandidate.review_status` is a *consequence* of a risk, not the risk itself. |
| `governance_controls` | Registry of controls. Columns: `id` (UUID), `code` (str, unique), `risk_code` (str, FK→governance_risks.code), `control_type` (enum: preventive, detective, corrective), `description` (text), `control_function_path` (str), `owner_role` (str), `test_frequency_days` (int, nullable), `last_tested_at` (datetime, nullable), `metadata_json` (JSONB). | Same reason. The control *implementations* are existing functions (`run_all_validators`, the eval gate, the source-acceptance gate); the table is the registry the audit iterates over. |
| `governance_kpis` | KPI definitions. Columns: `id` (UUID), `code` (str, unique), `name` (str), `description` (text), `sql_template` (text) — a parameterised SQL the audit script runs, `warning_threshold` (numeric), `breach_threshold` (numeric), `review_cadence_days` (int), `owner_role` (str). | KPI numbers today are not defined anywhere; they're hand-computed in markdown. This gives us one place where "what is the stale-source KPI?" has an answer. |
| `governance_kpi_results` | KPI snapshots. Columns: `id` (UUID), `kpi_id` (UUID, FK), `period_start` (date), `period_end` (date), `value` (numeric), `status` (enum: green, amber, red), `evidence_id` (UUID, FK→artifacts, nullable), `computed_at` (datetime). | Time-series of KPI values. |
| `governance_findings` | The proposed-finding queue (see §7). Columns: `id` (UUID), `org_id` (UUID, FK), `risk_code` (str, FK→governance_risks.code), `severity` (str), `subject_type` (str), `subject_id` (UUID, nullable), `summary` (text), `evidence_refs_json` (list of refs), `proposed_remediation` (text), `proposed_by_job_trace_id` (UUID, FK→job_traces, nullable), `proposed_by_model` (str, nullable), `skill_version_id` (str, nullable), `status` (enum: proposed, accepted, rejected, converted_to_capa), `decision_user_id` (UUID, FK→users, nullable), `decision_reason` (text, nullable), `decision_evidence_id` (UUID, FK→artifacts, nullable), `decision_at` (datetime, nullable), `linked_capa_id` (UUID, FK→review_items, nullable), `created_at` (datetime). | **Critical.** Today there is no generic "AI proposed finding" entity. `RuleCandidate` is one special case. This is the generalised form. |
| `governance_reviews` | Periodic review records. Columns: `id` (UUID), `review_type` (enum: monthly, quarterly, annual, ad_hoc), `period_start` (date), `period_end` (date), `chair_user_id` (UUID, FK→users, nullable), `summary` (text), `decisions_json` (JSONB), `open_actions_json` (JSONB), `evidence_pack_refs_json` (JSONB), `created_at` (datetime). | The review record itself, *not* the evidence pack content. |

### 5.3 Things explicitly NOT added (and why)

- **No `KPIResult` extension for "review period" beyond the columns above.** The brief's "review_cadence" lives on `governance_kpis`, not on results.
- **No new audit log table.** `AuditEvent` already exists. We will add a documented convention: governance write endpoints write an `AuditEvent` with `event_type` prefixed `governance.` (e.g. `governance.finding.accepted`).
- **No `TrainingRecord` table.** Out of scope (see §11).
- **No new file storage.** `Artifact` already exists and is content-addressed.
- **No new auth table.** `Org`, `User`, `Session`, `MagicLinkToken` exist. We extend the role enum (see §8) — we do not invent a parallel identity system.

### 5.4 Indexes and constraints to add

- `governance_findings (status, severity)`, `(org_id, status)`, `(proposed_by_job_trace_id)`.
- `governance_controls (risk_code)`, `(last_tested_at)` (for overdue detection).
- `governance_kpi_results (kpi_id, period_end DESC)`.
- `governance_reviews (period_start, period_end)`.
- Partial unique index on `governance_findings` `(subject_type, subject_id, risk_code, status)` where `status='proposed'` — prevents the same finding being proposed twice for the same subject.

### 5.5 Migration order (PR slicing, see §10)

1. New tables (`process_steps`, `governance_risks`, `governance_controls`, `governance_kpis`, `governance_kpi_results`, `governance_findings`, `governance_reviews`) in one Alembic revision.
2. Additive columns on `SourceVersion` and `ReviewItem` in a second Alembic revision.
3. Role enum extension to add `COMPLIANCE_OWNER` in a third Alembic revision (with a contract test update and a backfill default for existing users — operator chooses to set themselves as `COMPLIANCE_OWNER` or remain `OPERATOR`).

---

## 6. Validation rules (deterministic checks the audit script will run)

Each rule is a Python function in `src/draftcheck/governance/validators/` (new package, see §10). Each returns `list[GovernanceFailure]` where `GovernanceFailure` has `code`, `severity` (`critical | major | minor`), `subject_type`, `subject_id`, `message`, `evidence_refs`.

| Code | Severity | Check | Backed by |
| --- | --- | --- | --- |
| `GOV-SRC-001` | critical | Active `SourceVersion` (status=active, not superseded) has `owner_user_id` set. | `SourceVersion` |
| `GOV-SRC-002` | major | Active `SourceVersion` has `review_due_date` set and not in the past. | `SourceVersion` |
| `GOV-SRC-003` | major | Active `SourceVersion` has at least one `SourceReviewRecord` with `review_status='approved'` and `licence_status in {'approved','public','cc-by'}`. | `SourceVersion`, `SourceReviewRecord` |
| `GOV-SRC-004` | minor | No `SourceVersion` exists for the same `Source` whose `effective_from`/`effective_to` windows overlap. | `SourceVersion` |
| `GOV-SRC-005` | major | `SourceChunk` rows that participate in `ResolvedRule`/`CheckResult` must link to a `SourceVersion` whose `review_status='approved'`. | `SourceChunk`, `ResolvedRule`, `SourceReviewRecord` |
| `GOV-RULE-001` | critical | `Rule.lifecycle_status='approved'` row has non-empty `quote`, `clause_id`, `source_version_id`. | `Rule` |
| `GOV-RULE-002` | critical | `Rule` is linked to a `RuleClauseLink` whose `link_type='primary'`. | `Rule`, `RuleClauseLink` |
| `GOV-RULE-003` | major | `Rule.operator` ∈ {`gte`,`lte`,`gt`,`lt`,`eq`} (matches `src/draftcheck/checks/engine.py:_OPERATORS`). | `Rule` |
| `GOV-RULE-004` | major | No two `Rule` rows for the same `rule_key` AND overlapping `applicable_zones` AND overlapping `applicable_r_codes` AND overlapping `council_scope` AND both `lifecycle_status='approved'` — i.e. conflicting approved rules. | `Rule` |
| `GOV-CHK-001` | critical | `CheckResult` with `status='likely_pass' or 'likely_fail'` has a non-empty `citations_json` AND a non-empty `decision_trace_json` AND a non-null `resolved_rule_id`. | `CheckResult`, `ResolvedRule` |
| `GOV-CHK-002` | major | `CheckResult.citations_json` entries all reference `source_version_id`s whose `review_status='approved'`. | `CheckResult`, `SourceReviewRecord` |
| `GOV-CHK-003` | major | `CheckRun` with `status='has_likely_failures'` has at least one `RfiItem` linked via `check_result_id`. | `CheckRun`, `CheckResult`, `RfiItem` |
| `GOV-CHK-004` | minor | Every `CheckRun` has `as_of_date` within the project's `metadata_json.council_scope` currency window. | `CheckRun`, `Project` |
| `GOV-EXP-001` | major | `Export` with `status='completed'` has non-null `sha256` AND `manifest_json` includes `validation_passed=true` (a manifest key written by the export job's CI validation). | `Export` |
| `GOV-EXP-002` | critical | `Export` with `status='completed'` whose `manifest_json.validation_passed=false` is blocked from download. (This is enforced in code AND checked by the audit.) | `Export` |
| `GOV-EXP-003` | major | `Export` with `check_run_id` set has all `CheckResult` rows in that run passing `GOV-CHK-001`. | `Export`, `CheckResult` |
| `GOV-EVAL-001` | major | `EvalRun.status='failed'` for the *currently active* `SkillVersion` has a `ReviewItem` linked (via `governance_findings → ReviewItem`). | `EvalRun`, `governance_findings`, `ReviewItem` |
| `GOV-CTRL-001` | major | `governance_controls.test_frequency_days` not null implies `last_tested_at` is within `now - test_frequency_days`. | `governance_controls` |
| `GOV-CTRL-002` | critical | A control referenced by `governance_risks.default_owner_role` must have an `owner_role` field set. | `governance_risks`, `governance_controls` |
| `GOV-FIND-001` | critical | `governance_findings` with `status='proposed'` AND `created_at < now() - 14 days` is overdue for human review. | `governance_findings` |
| `GOV-FIND-002` | critical | `governance_findings` with `status='accepted'` has `decision_user_id`, `decision_reason`, `decision_evidence_id`, and `linked_capa_id` all non-null. | `governance_findings` |
| `GOV-FIND-003` | critical | `governance_findings` with `status='converted_to_capa'` has a `linked_capa_id` whose `ReviewItem` row has `severity`, `owner_user_id`, `due_at` all set. | `governance_findings`, `ReviewItem` |
| `GOV-CAPA-001` | critical | `ReviewItem` with `status='resolved'` has `closure_evidence_id` non-null AND `effectiveness_check_due_date` non-null. | `ReviewItem` |
| `GOV-CAPA-002` | major | `ReviewItem` with `status='resolved'` AND `effectiveness_check_due_date < now()` AND `effectiveness_result` is null is overdue. | `ReviewItem` |
| `GOV-CAPA-003` | minor | `ReviewItem.proposed_by_finding_id` set implies `governance_findings.status='converted_to_capa'`. | `ReviewItem`, `governance_findings` |
| `GOV-KPI-001` | minor | `governance_kpi_results` for a KPI whose `review_cadence_days` elapsed since last result exists. | `governance_kpis`, `governance_kpi_results` |
| `GOV-PIPE-001` | minor | `governance_pipeline_steps.is_critical=true` rows have a `governance_controls` row whose `risk_code` references the stage. | `governance_pipeline_steps`, `governance_controls`, `governance_risks` |

`critical` findings cause the audit script to exit non-zero. `major` and `minor` are reported but do not fail CI by default (operator can flip a flag).

---

## 7. AI review workflow

This is the heart of the feature: **AI proposes, humans accept, accepted findings become CAPA.**

### 7.1 States

`governance_findings.status` ∈ `proposed | accepted | rejected | converted_to_capa`.

Transitions:

```
proposed ──accept──> accepted ──convert-to-capa──> converted_to_capa
   │
   └──reject──> rejected (terminal)
```

`rejected` and `converted_to_capa` are terminal. `accepted` is intermediate; a finding that has been *accepted* but not yet *converted* is still awaiting a human to set severity, owner, and due date.

### 7.2 Invariants (enforced in code, checked by audit)

- A finding is **never** created with status `accepted`, `rejected`, or `converted_to_capa`. The default is `proposed`.
- `accepted` requires `decision_user_id`, `decision_reason`, `decision_evidence_id`, `decision_at`. The endpoint refuses without these.
- `converted_to_capa` requires `accepted` and `linked_capa_id`.
- A `proposed` finding may be auto-superseded (e.g. the underlying subject changes) — that is a separate transition `proposed → superseded` not listed in the four-state enum. (Decision: add `superseded` to the enum, distinct from `rejected`. Final list: `proposed | accepted | rejected | converted_to_capa | superseded`.)
- No background job, no system actor, no AI model may write `status='accepted'` or `status='converted_to_capa'`. The `accept` and `convert-to-capa` endpoints require a real session. A future "auto-accept for low-severity" feature is **out of scope** for the initial build.
- Every state transition writes an `AuditEvent` with `event_type='governance.finding.<state>'`.

### 7.3 AI provenance — reused, not invented

Each finding carries `proposed_by_job_trace_id` (FK → `JobTrace`). The `JobTrace` row records:

- `adapter_name`, `provider`, `model` — the AI substrate (existing `src/draftcheck/ai/substrate.py`).
- `skill_version_id` — what skill produced the proposal.
- `prompt_hash` — what prompt.
- `spend_cap_cents`, `spend_cap_tokens` — the spend cap that was applied.
- `input_artifact_id`, `output_artifact_id` — the evidence in and the proposed text out.
- `cost_usd` — what it cost.

This is exactly what the brief wants for "AI must be cited, versioned, capped" — and we get it by reusing `JobTrace`. No new AI/provider abstraction (per the constraint).

### 7.4 The generalisation from `RuleCandidate`

Today the only AI-proposed-then-human-accepted flow is `RuleCandidate → Rule` (via `src/draftcheck/domain/rules/gate.py:auto_promote`). After this feature:

- The promotion gate logic in `gate.py` is **not deleted**. It is the canonical implementation of *one specific* risk/control: risk=`RULE_EXTRACTION_HALLUCINATION`, control=`EVAL_GATE_AND_REVIEWER_APPROVAL`.
- The generalisation is a new `governance_findings` row that *wraps* a `RuleCandidate` when the candidate's `auto_promote` would fail (e.g. validators failed, eval gate failed). The candidate itself becomes a piece of evidence (via `subject_type='rule_candidate'`, `subject_id=candidate.id`). The `ReviewItem` that `gate.py:_create_review_item` already creates becomes a CAPA — a *derived* one, created from the finding via the same `convert-to-capa` endpoint.
- This means existing operators see no behaviour change: rule extraction that fails today still produces a `ReviewItem` and a `validator_failed` candidate. The new feature simply makes that flow consistent with the rest of the AI review workflow.

### 7.5 Eval-gate as a control

A `governance_controls` row with `code='EVAL_GATE_RULE_EXTRACTION'` will reference the existing eval gate (`src/draftcheck/eval/runner.py:run_eval_case` + `src/draftcheck/domain/rules/gate.py:eval_gate_pass`). The control's `control_function_path` points at the function; the test triggers a synthetic candidate and asserts the gate returns `False` when it should. This way the "control tested" concept is consistent across the system.

---

## 8. Permissions

**Today's state (read from code, not assumed):**

- `src/draftcheck/domain/identity/roles.py:8` defines `IdentityRole = {OWNER, OPERATOR}`.
- `tests/test_v3_schema_contract.py:16` pins the enum to exactly these two values.
- The brief asks for `viewer | process_owner | qa_lead | compliance_owner | admin`.

**What this map proposes (and why it does not invent a parallel auth system):**

- Extend the existing `IdentityRole` enum via Alembic to add `COMPLIANCE_OWNER`. The brief's `viewer | process_owner | qa_lead | compliance_owner | admin` collapses to:
  - `viewer` — read-only. Mapped to existing `OPERATOR` role for governance endpoints (read endpoints accept OPERATOR; write endpoints do not).
  - `process_owner` — edit processes. Mapped to existing `OPERATOR` for governance write endpoints (`/capa`, `/controls/test`, etc.) plus `OWNER` for source-ownership edits.
  - `qa_lead` — accept/reject findings, verify CAPA closure. **New `COMPLIANCE_OWNER` role.**
  - `compliance_owner` — same as qa_lead for our purposes. Mapped to `COMPLIANCE_OWNER`.
  - `admin` — full access. Mapped to `OWNER`.
- Update `tests/test_v3_schema_contract.py` to assert the new enum contains the three values (`OWNER`, `OPERATOR`, `COMPLIANCE_OWNER`).
- Backfill: existing users keep their role. Operators who need governance powers get promoted to `COMPLIANCE_OWNER` explicitly. There is no auto-promotion.

**Endpoint permission matrix (summary; the actual enforcement is in the dependency-injection layer of each router):**

| Endpoint class | OPERATOR | COMPLIANCE_OWNER | OWNER |
| --- | --- | --- | --- |
| `GET` governance/* | yes | yes | yes |
| `POST` sources/{id}/owner | no | yes | yes |
| `POST` sources/{id}/supersede, /retire | no | yes | yes |
| `POST` controls/{id}/test | yes | yes | yes |
| `POST` findings | yes (system actors via background job use `OWNER`) | yes | yes |
| `POST` findings/{id}/accept\|reject | no | yes | yes |
| `POST` findings/{id}/convert-to-capa | no | yes | yes |
| `PATCH` capa/{id} (close) | owner-of-capa only | yes | yes |
| `POST` reviews | no | yes | yes |

"owner-of-capa" = `ReviewItem.assigned_user_id == current_user.id`. Enforced at the endpoint, not via a generic RBAC table — LotFile's existing identity layer doesn't have one, and we are not inventing one.

---

## 9. Test plan

Use the existing pytest harness. The `tests/` directory has 23 files; new tests go in the same style. Test framework is `pytest`; the contract test `test_v3_schema_contract.py:33` already enforces "no `create_all` in src/".

### 9.1 New test files

- `tests/test_governance_schema_contract.py` — the governance tables exist, columns are present, foreign keys are correct, the partial unique index on `governance_findings` is present, and the new role enum contains `COMPLIANCE_OWNER`. Mirror the style of `test_v3_schema_contract.py`.
- `tests/test_governance_validators.py` — one test per validator code in §6. Use an in-memory sqlite-equivalent (or test DB) and seed the minimum rows to exercise the rule. Mirror the style of `test_v3_stage3_validators.py`.
- `tests/test_governance_api.py` — endpoint tests with `TestClient`. Cover: list/get, accept/reject rules, convert-to-capa, capa close requires evidence, capa close requires effectiveness check date, audit-report returns the same data as the script.
- `tests/test_governance_finding_state_machine.py` — state transitions. Proposed → accepted (needs reason+evidence+user). Proposed → rejected (needs reason). Accepted → converted_to_capa (needs linked_capa_id with severity+owner+due_at). Rejected/converted_to_capa are terminal. System actor cannot accept.
- `tests/test_governance_audit_script.py` — invoke `scripts/governance_audit.py` as a subprocess, assert exit code, assert JSON output, assert seeded-invalid data triggers non-zero exit.
- `tests/test_governance_evidence_pack.py` — pack assembly is deterministic, includes the right sources/chunks/citations/audit events for a given (period, scope) window.

### 9.2 Updated test files

- `tests/test_v3_schema_contract.py` — extend the role-enum assertion to include `COMPLIANCE_OWNER`. Update the test docstring to note the new value.

### 9.3 Test categories mapped to brief

| Brief test requirement | Test |
| --- | --- |
| source governance validation | `test_governance_validators.py::test_gov_src_001` … `test_gov_src_005` |
| source freshness checks | `test_governance_validators.py::test_gov_src_002` |
| citation completeness | `test_governance_validators.py::test_gov_chk_001`, `test_gov_chk_002` |
| rule-to-source traceability | `test_governance_validators.py::test_gov_rule_001`, `test_gov_rule_002` |
| compliance check evidence requirements | `test_governance_validators.py::test_gov_chk_001` |
| AI finding acceptance rules | `test_governance_finding_state_machine.py` |
| CAPA closure evidence | `test_governance_validators.py::test_gov_capa_001` |
| audit script failure paths | `test_governance_audit_script.py` |
| permission boundaries if roles exist | `test_governance_api.py::test_permission_matrix` |

### 9.4 Test coverage target

- ≥ 90% line coverage on the new `src/draftcheck/governance/` package.
- Every validator code in §6 has at least one positive and one negative test.
- Every state transition in §7.1 has a test.

---

## 10. PR slicing (recommended)

The 8-PR slicing matches the build's natural pressure points: schema first, then validators + audit, then API, then AI queue, then CAPA linkage, then scripts/CI. Each PR is small enough to review and revert independently.

| PR | Title | Scope | Acceptance |
| --- | --- | --- | --- |
| **PR-1** | **This implementation map** | `docs/process-control/implementation-map.md` only. No code. | Operator approves. |
| **PR-2** | **Schema + new tables (Alembic)** | New Alembic revision(s) creating `governance_pipeline_steps`, `governance_risks`, `governance_controls`, `governance_kpis`, `governance_kpi_results`, `governance_findings`, `governance_reviews`. Indexes and constraints per §5.4. Extend `SourceVersion` and `ReviewItem` per §5.1. New schema-contract test passes. | `alembic upgrade head` succeeds from a fresh DB; `alembic downgrade -1` returns to prior state; `pytest tests/test_governance_schema_contract.py` passes. |
| **PR-3** | **Validation service + tests** | `src/draftcheck/governance/validators/*.py` with the validator functions in §6. `tests/test_governance_validators.py` covers each. | `pytest tests/test_governance_validators.py` passes; line coverage ≥ 90% on the new package. |
| **PR-4** | **Governance API endpoints (read-only + sources)** | `/api/v1/governance/sources/*`, `/api/v1/governance/pipeline-steps`, `/api/v1/governance/evidence` (read endpoints). Tests in `tests/test_governance_api.py`. | Endpoints return the right shapes; permissions enforced; `AuditEvent` written for every write. |
| **PR-5** | **Audit script + CI integration** | `scripts/governance_audit.py` (Python, see §10.1). Add to `.github/workflows/*.yml` (or the existing CI workflow). Support `--json` output. Exit non-zero on critical. | `python scripts/governance_audit.py --json` runs in CI; `pytest tests/test_governance_audit_script.py` passes. |
| **PR-6** | **AI proposed-finding queue** | `/api/v1/governance/findings/*` endpoints. `governance_findings` write paths. State machine enforced in code. `tests/test_governance_finding_state_machine.py`. | All state transitions work; system actor cannot accept; `AuditEvent` written for every transition. |
| **PR-7** | **CAPA / remediation linkage** | `/api/v1/governance/capa/*` endpoints. PATCH close requires evidence+date. `findings → capa` conversion wired. | Close-without-evidence rejected; effectiveness-check overdue detected; existing `gate.py:_create_review_item` flow now writes a finding too. |
| **PR-8** | **KPI dashboard, reviews, audit-report + role enum extension** | `/api/v1/governance/kpis`, `/reviews`, `/audit-report`. Alembic migration to add `COMPLIANCE_OWNER` role. Update `test_v3_schema_contract.py` enum assertion. | Migration applies; old users keep their role; new endpoints return the right shapes; operator can be promoted to `COMPLIANCE_OWNER` via direct SQL or admin tool. |

**Optional, deferred PRs (require operator approval, see §11):**

- **PR-9 (deferred):** CSV/PDF export of evidence pack. Not in initial scope; brief mentions "if export support already exists" — it doesn't.
- **PR-10 (deferred, separate approval):** If a UI is later wanted, it would be a separate track under `web/`, mounted same-origin, with a fresh `process-control` route group. **No UI in this map.**

### 10.1 Audit script

`scripts/governance_audit.py` — a standalone Python entrypoint.

```text
Usage:
  python scripts/governance_audit.py            # human-readable output
  python scripts/governance_audit.py --json     # JSON output
  python scripts/governance_audit.py --strict   # exit non-zero on major+ (not just critical)

Exit codes:
  0   no critical failures
  1   one or more critical failures
  2   script error (DB unreachable, etc.)
```

It uses the same SQLAlchemy engine and the validator functions from PR-3. It writes to stdout (text or JSON) and to stderr (summary line). The CI integration is a single `python scripts/governance_audit.py` step in the existing pipeline. No new dependencies.

---

## 11. Known limitations

### 11.1 What the generic brief asks for that does not fit LotFile

- **Training records (§9 of brief).** Out of scope. LotFile's "process" is software, not people; training records are an HR/people-process concern, not a software-pipeline concern. The brief's `TrainingRecord` table is **not** built.
- **Generic /process-control/* UI (§3 of brief, 8 pages).** Out of scope. The lock against browser UI additions (`AGENTS.md` "Build toward one repo, one VPS..." + the active web rebuild) plus the explicit constraint "Do not build the generic `/process-control/*` frontend" both forbid this. A future UI is a separate, explicitly-approved track (PR-10 above).
- **Full BPMN editor / GRC platform (non-goals).** Out of scope, per the brief itself.
- **External regulatory interpretation engine (non-goals).** Out of scope, per the brief itself and per `AGENTS.md` "LLMs may extract, classify, embed, and draft; they must never decide compliance verdicts."

### 11.2 What is deferred (not in this map)

- **CSV/PDF export of evidence pack.** The brief says "if export support already exists." It doesn't. The pack is JSON for now; CSV/PDF is PR-9.
- **KPI time-series UI.** Even if we wanted a UI, KPI dashboards are out of scope. The audit script computes and reports.
- **Periodic scheduling of the audit.** The script is run on demand and in CI. Cron / Procrastinate scheduling is a separate ops decision.
- **AI finding auto-supersede behaviour beyond the new `superseded` state.** The state exists in the design; the actual logic (when does the system supersede a finding?) is left for a future PR when there is a real trigger.

### 11.3 What requires operator approval before Phase 2 starts

1. **Approve this map.** That is the gate.
2. **Add `COMPLIANCE_OWNER` role.** This is a one-line extension of an existing enum, but it is a *new* permission tier. Operator must explicitly approve the role and the permission matrix in §8.
3. **Extend `ReviewItem` with severity/root_cause/closure_evidence/effectiveness fields.** The table has 155 existing rows; the new columns must be additive and nullable. No backfill required, but operator should confirm "additive only, no backfill" is acceptable.
4. **Allow `governance_findings` to wrap existing `RuleCandidate` failures.** This is a small generalisation, but it changes the meaning of `RuleCandidate.review_status` (from "this is the only AI flow" to "one of several"). Operator should confirm the generalisation is the right move, or specify a different one.

### 11.4 What could break existing architecture if done literally

- **Adding the `/api/v1/governance` prefix.** Already inside the locked `/api/v1` surface; no split-frontend risk. Caddy in `infra/v3/Caddyfile` already proxies `/api/v1` to the FastAPI backend, so the new endpoints are served same-origin automatically. Verified.
- **Extending the role enum.** Today's contract test pins the enum to two values. The extension requires updating the test, which is a contract change. The contract change is small but must be deliberate.
- **Adding fields to `ReviewItem`.** 155 existing rows must continue to function. All new fields are nullable; no NOT NULL constraints. Backwards compatible.
- **Reading from `Source.authority` and `Source.canonical_url` in validation logic.** These are the public, queryable fields. Do not read from `metadata_json` for governance purposes — that's the "wrong place" trap and would make filters/joins impossible.
- **Reusing `JobTrace` for AI finding provenance.** `JobTrace` was designed for the AI substrate. The reuse is intentional and consistent. Do not invent a parallel trace store.
- **Running the audit script against the production database.** The script is read-only and idempotent, so this is safe, but it should run against a stable connection pool. Operator should confirm the right `DATABASE_URL` target for the CI run.
- **Modifying `src/draftcheck/domain/rules/gate.py`.** Do not. The generalisation in §7.4 is *additive*: `gate.py` keeps its existing behaviour. New `governance_findings` rows are written alongside (not instead of) the existing `ReviewItem` rows that `_create_review_item` produces. If a future PR needs to refactor `gate.py` to use the new finding flow end-to-end, that is a separate, larger PR and must not be folded into PR-2/3/6.

### 11.5 Things that look like work but aren't

- **A new "audit" job in the queue.** The audit script is a one-shot CLI, not a background job. The existing Procrastinate queue stays untouched.
- **A new file storage system.** `Artifact` (content-addressed, sha256-indexed) is reused.
- **A new analytics stack.** The KPIs are SQL queries; the dashboard (if any) reads from `governance_kpi_results`. No new BI tool.
- **A new auth provider.** The magic-link + dev-login flow is reused. Cookie/session/CSRF behaviour is unchanged.

---

## 12. What this map is NOT

- It is **not** an implementation. No code has been written. Phase 2 begins only after the operator approves this map.
- It is **not** a replacement for `docs/MASTER_REBUILD_PLAN.md`. The master plan is still authoritative; this is a sub-plan that must remain consistent with it.
- It is **not** a guarantee of compliance. LotFile outputs remain advisory (`likely_pass / likely_fail / needs_more_info / unsupported`). The governance layer is process hygiene, not a certification.
- It is **not** a UI. There is no UI in this map. PR-10 is a separate decision.

---

## 13. Open questions for the operator

1. **§8 role matrix.** Is the `COMPLIANCE_OWNER` mapping acceptable, or do you want a different role name (e.g. `AUDITOR`)?
2. **§7.4 generalisation of `RuleCandidate`.** Approve wrapping existing `RuleCandidate` failures as `governance_findings`, or keep the two flows separate?
3. **PR slicing cadence.** Eight PRs as listed, or fewer/larger PRs?
4. **Audit-script severity threshold.** Default is "exit non-zero on critical only." Should the default be "exit non-zero on major+"? The current draft picks the more permissive default because LotFile's existing CI is green-by-default; flipping to strict would require fixing all current major-severity findings first.
5. **Deferral of CSV/PDF export (PR-9).** Confirm deferral is acceptable.
6. **Naming.** Is `/api/v1/governance/*` the right prefix, or do you prefer `/api/v1/process-control/*` (which is what the brief asked for, but `governance` is more specific to this repo)?

---

## 14. Next step (after operator approval)

PR-2: an Alembic revision adding the new tables per §5.2, plus the additive columns on `SourceVersion` and `ReviewItem` per §5.1, plus the role enum extension per §5.5/§8. New schema-contract test in `tests/test_governance_schema_contract.py`. No endpoints, no validators, no audit script yet.

**Stop. Awaiting review.**
