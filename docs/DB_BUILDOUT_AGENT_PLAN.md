# DB Build-Out — Dumb-Agent Work Packages

Date: 2026-06-10. Subordinate to `docs/MASTER_REBUILD_PLAN.md` (§5, §8.1, §8.2, §9) and
`docs/CORPUS_COMPLETENESS_PLAN.md` (the per-phase mechanics live there — this file is the
dispatch sheet: who does what, in what order, with what gate).

**Audience: dumb agents.** No judgment calls. Every WP has exact inputs, an acceptance gate
(machine-checkable), and an escalation rule. If a step is ambiguous: write a row to the
escalation queue (`review_items`, or `reports/escalations.jsonl` if DB unreachable) and move
to the next WP item. Never stall. Never invent schema — Alembic only.

## Current state (verified 2026-06-10)

- Schema: migrations `0001`–`0010` applied; ~45 models in `src/draftcheck/db/models.py`.
  Core §5 tables exist (sources, clauses, rules, legal_edges, spatial, compliance, governance).
- **Missing schema:** `target_manifest`, `instrument_aliases`, `adversarial_findings` (all
  required by CORPUS_COMPLETENESS_PLAN), and `reports/` outputs do not exist.
- Legacy harvest seeds exist: `evals/seeds/*.jsonl` (rule_rows, clause_dispositions,
  golden_eval_cases, golden_eval_runs). `draftcheck.db` (146 MB) still in working tree.
- Scripts available: `scripts/build_wa_council_manifest.py`, `discover_public_sources.py`,
  `harvest_legacy_db.py`, `seed_eval_data.py`, `check_sqlite_integrity.py`.
- Legacy SQLite holds 81 source_documents / 31,200 chunks / 28,068 clauses — harvest source only.

## Swarm architecture

This plan runs as a **swarm**: one coordinator + pools of disposable workers. Workers are
dumb by design — all intelligence lives in the work-item schema and the gates.

```text
COORDINATOR (1, long-lived)
  - owns the dependency graph below; opens a WP only when its blockers' gates are green
  - shards each open WP into work items (rows), spawns workers, retires them on completion
  - never does object-level work itself; only dispatch, gate-checking, report assembly

WORKER POOLS (disposable, stateless, restart-safe)
  - spatial-loaders      WP2   1 per dataset                  (6 workers)
  - index-scrapers       WP3   1 per authoritative index      (6 workers)
  - fetchers             WP4   1 per index/LGA shard          (6–20 workers)
  - citation-resolvers   WP5   1 per acquired source_version
  - extractors           WP6   1 per rule-bearing source_version
  - edge-proposers       WP7   1 per cited instrument pair
  - adversaries          WP8   5 roles × 1 per corpus slice; Defense pool spawns after attackers
  - seeder               WP9   1 worker
```

**Coordination is the database, not chat.** Workers never talk to each other. A worker:

1. **Claims** a work item atomically:
   `UPDATE ... SET claimed_by=:worker, lease_expires_at=now()+interval '30 min'
    WHERE id = (SELECT id FROM <queue> WHERE status='pending' AND (lease_expires_at IS NULL
    OR lease_expires_at < now()) LIMIT 1 FOR UPDATE SKIP LOCKED) RETURNING *`.
   Queues are the natural tables: `target_manifest` (WP3–5), `source_versions` (WP6),
   `adversarial_findings` (WP8 Defense), `spatial_datasets` (WP2). Procrastinate jobs wrap
   the same rows where a queue job already exists (§3.2).
2. **Works** the one item, idempotently (content-hash / natural-key upsert).
3. **Terminates** it: `done` | `blocked` (+ one-command unblock note) | `escalated`
   (`review_items` row). Never leaves an item claimed — lease expiry makes worker death safe.

Swarm rules:

- Any worker can die at any time; a replacement claims the lease-expired item. No state in
  the worker, ever.
- Fan-out is bounded per pool (start 6, raise if the upstream services tolerate it; lawful
  fetch delays from §8.1 are per-worker, so the swarm respects robots/licence by construction).
- Coordinator re-runs each WP's gate query after the pool drains; gate red → it re-shards the
  failures, not the whole WP.
- Two workers writing the same natural key is resolved by idempotent upsert, not locking
  beyond the claim. If a WP can't be made idempotent, it doesn't get a swarm — it gets one
  worker (WP0, WP7 precedence ruleset, WP9).

## Dependency graph

```text
WP0 state probe
 └─ WP1 schema gaps (one migration)
     ├─ WP2 spatial spine load          (parallel with WP3+)
     ├─ WP3 scope + manifest            → WP4 acquisition (fan-out)
     │                                     → WP5 citation closure (loop to WP4)
     │                                        → WP6 extraction + rule matrix (fan-out)
     │                                           → WP7 legal graph + conflict sweep
     │                                              → WP8 adversarial rounds
     └─ WP9 eval seed load (anytime after WP1)
WP10 freshness + CI assertions (after WP6; permanent)
```

---

## WP0 — State probe (1 agent, 1 session)

Purpose: never plan against an imagined DB.

1. On the VPS: `alembic current`, `alembic heads` — confirm head = `0010`.
2. Run and commit `reports/db_state.json`: row counts for every §5 table
   (`SELECT relname, n_live_tup FROM pg_stat_user_tables ORDER BY relname`).
3. Confirm extensions: `SELECT extname FROM pg_extension` must include `postgis`, `vector`.
4. Confirm Procrastinate schema applied (`procrastinate schema --check` or table presence).

Gate: `reports/db_state.json` committed. Escalate (don't fix): missing extension, divergent
alembic head, any table from §5 absent that migrations claim to create.

## WP1 — Schema gaps (1 agent, 1 PR)

One Alembic migration (`0011_corpus_buildout_support`):

- `target_manifest` — columns exactly as CORPUS_COMPLETENESS_PLAN Phase 1 specifies
  (`status ∈ {pending, acquired, metadata_only, blocked, out_of_scope}`, FK to
  `source_documents`, `last_checked_at`, `notes`).
- `instrument_aliases` — `alias_text, canonical_manifest_id, match_kind ∈ {exact, regex}`.
- `adversarial_findings` — columns per Phase 5 (`round, agent_role, target, claim,
  evidence_quote, severity, status ∈ {open, confirmed, rejected, fixed}`).
- Matching SQLAlchemy models; `upgrade` + `downgrade` both tested in CI.

Gate: `alembic upgrade head && alembic downgrade -1 && alembic upgrade head` green in CI;
no `create_all` anywhere (existing import-linter rule must stay green).

## WP2 — Spatial spine load (swarm: spatial-loaders, 1 per dataset)

Per §8.2 + Appendix B. One agent per dataset; all idempotent; everything → GDA2020 (EPSG:7844)
at import; every load writes a `spatial_datasets` row (dataset_id, licence, licence_status,
source_crs, version, fetched_at, refresh_due) BEFORE feature rows.

| Dataset | Target table | Source | Note |
|---|---|---|---|
| G-NAF address points (WA) | `address_points` | Geoscape via data.gov.au | quarterly; EULA CC-BY-4.0-based |
| Cadastre (pilot LGA first) | `parcels` | Landgate SLIP public tier | licence_status=`review` until Landgate commercial terms confirmed — load, but resolver flags it |
| LGA boundaries | `lg_areas` | Landgate admin boundaries | merge with council registry |
| Scheme zones + R-codes | `planning_features` (layer_type=zone) | DPLH-071 WFS | pilot LGA first |
| Bushfire-prone areas | `planning_features` (bushfire) | SPP 3.7 mapping via SLIP | confirm dataset ID at import |
| Heritage | `planning_features` (heritage) | state + local registers | confirm dataset ID at import |

Dumb-agent rules: fetch fails 3× → log to `source_fetch_log`, mark dataset row
`licence_status=blocked` with one-command unblock note, continue. Never hand-digitise.
Never load a dataset without a licence note.

Gate: `reports/spatial_load.json` — per dataset: row count > 0 (or blocked+reason), CRS
confirmed 7844 (`SELECT DISTINCT ST_SRID(geom)`), spatial index present. Smoke test: one
known pilot-LGA address resolves end-to-end (G-NAF point → parcel → LGA → zone/R-code) and
writes `property_facts` rows with `method=parcel_intersection`.

## WP3 — Scope + target manifest (scope: 1 worker; then swarm: index-scrapers, 1 per index)

Execute CORPUS_COMPLETENESS_PLAN Phases 0–1 verbatim:

1. Write `docs/CORPUS_SCOPE.md` (in / metadata-only / out-of-scope, per the plan's list).
2. Seed `target_manifest` from existing audits + `scripts/build_wa_council_manifest.py`
   output, then scrape the six authoritative indexes (legislation register, DPLH SPP index,
   DPLH DC policies, pilot-LGA council pages, ABCB NCC index, PlanWA/SLIP catalogue).
3. Reconcile the 81 existing `source_documents` → every one matched to a manifest row
   (`acquired` + FK) or flagged `orphan_source`.

Gate: `reports/manifest_closure.json` — 0 `pending`-without-fetch-attempt at seed time is not
required, but 0 `orphan_source` is. Per-category counts printed.

## WP4 — Acquisition (swarm: fetchers, claim `target_manifest` rows where status=pending)

CORPUS_COMPLETENESS_PLAN Phase 2 verbatim. For each `pending` manifest row: lawful fetch →
`source_documents` → `source_versions` (sha256) → `artifacts` → parse → chunk → FTS +
embeddings (pinned model, `embedding_model` recorded per chunk).

Rules: 3 failed fetches → `blocked` + unblock note, continue. Unparseable after OCR fallback →
`blocked`, artifact preserved (a doc we can't read is NOT acquired). Paid/licensed →
`metadata_only`, never store full text. No source supports answers until `source_reviews` pass.

Gate: `reports/acquisition_report.json` — 0 `pending`; every `acquired` row has
`parse_status=ok` + chunks + embeddings (SQL assertion).

## WP5 — Citation closure (swarm: citation-resolvers, 1 per source_version; coordinator owns the loop)

Phase 3 verbatim, swarmed per document: each worker claims one acquired `source_version`,
extracts cross-references (deterministic pass + LLM pass) → `legal_edges` `relation=cites` →
resolves against manifest via `instrument_aliases` → unresolved reference = new manifest row
`pending` (idempotent insert by alias key). The **coordinator** runs the fixpoint loop: pool
drains → new `pending` rows? → re-open WP4, then re-shard WP5 over the new versions only.
Repeat until a full pass adds zero rows.

Gate: `reports/citation_closure.json` — 0 unresolved external_references, fixpoint reached.

## WP6 — Extraction + rule matrix (swarm: extractors, claim rule-bearing `source_versions`)

> **SUPERSEDED 2026-06-14 — active pipeline is `docs/OPEN_VOCAB_REBUILD_PLAN.md`.**
> The extraction pipeline no longer enforces a closed/fixed `rule_key` vocabulary, and the
> "Tier-1 check keys × R5–R80" rule matrix below is no longer a hard gate. Extractors now
> propose **any** `snake_case` rule_key they see (validated structurally by
> `validators.validate_rule_key`, `[a-z][a-z0-9_]{2,60}`); the former closed set is now a
> soft signal only (`RULE_KEY_HINTS` / `is_hinted_key()` in
> `src/draftcheck/extraction/vocabulary.py`), not a drop filter. Universal structural
> validators (quote-anchor, no-orphan-numbers, normative-language, operator/unit canonical,
> `validate_value_finite`, `validate_unit_category_sanity`) catch garbage regardless of key;
> raw keys are canonicalised post-hoc by `scripts/wp6_cluster_keys.py` /
> `scripts/wp6_apply_clustering.py` into the `canonical_rule_key` column (migration
> `0018_rule_canonical_keys`, on both `rules` and `rule_candidates`), and CheckDefinitions are
> derived from clusters (`scripts/wp6_register_checks_from_clusters.py` →
> `src/draftcheck/checks/registry_generated.py`), not declared up-front. The original WP6
> procedure is kept below as history.
>
> Authority: `docs/OPEN_VOCAB_REBUILD_PLAN.md`, subordinate to `docs/MASTER_REBUILD_PLAN.md`.

Phase 4 verbatim: structure pass → 3-pass blind ensemble (temp 0, strict JSON, mandatory
quote anchors) → deterministic validators → adjudication (3/3 auto-accept @0.95, 2/3
challenge, else `pending_review`) → per-doc acceptance gate (100% dispositions, 0 orphan
numbers, 0 unresolved exception clauses, pending_review drained — CI assertion, source_version
cannot go active otherwise).

Mandatory: `pathway` on every R-Codes atom; DTC atom without its design-principle sibling
linked `performance_alternative_to` = audit failure. Table clauses get the vision pass with
cell coordinates in provenance.

Gate: `reports/rule_matrix.csv` — Tier-1 check keys × R5–R80 × pilot LGA, 100% filled
(approved atom or cited `n/a`). Golden evals green. (Superseded 2026-06-14 — the closed Tier-1
key matrix is no longer a hard gate; the open-vocab pipeline accepts new `snake_case` keys and
canonicalises them post-hoc. Treat this matrix as coverage telemetry, not a vocabulary ceiling.
See `docs/OPEN_VOCAB_REBUILD_PLAN.md`.)

## WP7 — Legal graph + conflict sweep (swarm: edge-proposers, 1 per instrument pair; precedence + sweep: 1 worker)

Phase 4b verbatim: exception atoms (`rule_type=exception` + `exception_to` edge; base rule
blocked from `approved` while exception unresolved) and blind 2-model edge proposal are
swarmed — one worker per instrument pair where WP5 found citations (verbatim quote required,
validator-confirmed). The precedence ruleset in code (`src/draftcheck/checks/`, never
AI-decided) and the deterministic conflict sweep + dependency closure are NOT swarmed: one
worker, after the edge pool drains.

Gate: 0 unstructured exception clauses; 0 quoteless edges; `reports/conflict_sweep.json`
empty; dependency closure 100%.

## WP8 — Adversarial rounds (swarm: adversaries — 5 roles × 1 worker per corpus slice)

Phase 5 verbatim: Re-extractor (blind, different model family), Prosecutor (DB-only answers
verified against raw sources), Gap hunter (web vs manifest), Conflict prosecutor (concrete
lot fact-patterns → exactly one winner or cited `needs_more_info`) all run as parallel
attacker pools, sharded by corpus slice, writing only to `adversarial_findings`. The Defense
pool spawns after attackers drain and claims `open` findings via the standard lease query —
fix or refute with verbatim quote, no third option. Judge (1 worker) resolves disputes; every
confirmed finding adds a golden eval case. Coordinator counts the round and decides
stop/continue.

Gate: 2 consecutive full rounds with zero confirmed findings →
`reports/adversarial_closure.json`.

## WP9 — Eval seed + label load (1 agent, anytime after WP1)

1. Load `evals/seeds/*.jsonl` into `eval_cases` / `eval_runs` / clause-disposition labels
   via `scripts/seed_eval_data.py` (idempotent — content-hash dedupe).
2. Verify counts vs `DATA_INVENTORY.md` (19 golden cases, 65 dispositions, 6 rule_rows).
3. Then archive `draftcheck.db` + `draftcheck-corpus.db` out of the working tree per §4.2
   (storage archive + `.gitignore`; confirm seeds committed first).

Gate: ≥19 eval cases in DB; `draftcheck.db` no longer in `git ls-files`.

## WP10 — Freshness + CI (1 agent, permanent)

Phase 6 verbatim: weekly watcher job (re-scrape indexes → diff → `pending` → auto WP4;
changed sha256 ⇒ new source_version, old rules → `stale`; amendment without re-extraction in
7 days = red CI). CI on every merge asserts: manifest closure, citation closure, per-doc
gates, rule matrix fill, golden evals, 0 open adversarial findings >14 days. Runtime
backstop: weekly clustering of `unsupported`/`needs_more_info` answers → Gap-hunter findings.

Gate: scheduled job live on VPS; CI assertions merged and green.

---

## Standing rules (every agent, every WP)

- Alembic is the only schema authority. No `create_all`, no ad-hoc DDL.
- Idempotent jobs only: re-running any WP must be safe (content-hash / upsert by natural key).
- Every fetch → `source_fetch_log`; every approve/override → `audit_events`.
- Outputs are advisory; never claim final compliance; cite or refuse.
- Blocked ≠ stalled: record the blocker + one-command unblock, continue, list in final report.
- All reports land in `reports/` and are committed — they are the proof, not the chat log.
