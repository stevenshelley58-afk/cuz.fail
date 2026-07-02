# DB Build-Out — Kimi Code Swarm Plan (self-driven, no Hermes)

Date: 2026-06-20. **Audience: Kimi Code, running autonomously.**

This is the execution handoff for completing and maintaining the LotFile / DraftCheck corpus
database. It is a faithful re-targeting of `docs/DB_BUILDOUT_AGENT_PLAN.md` for **Kimi Code as the
sole operator**, with one structural change: **Kimi runs the swarm itself.** There is no Hermes
container in the loop — the LLM-bearing work (extraction, citation LLM pass, edge proposal,
adversarial roles) is performed by **Kimi-spawned worker sessions**, coordinated through the
database, not by dispatching to the in-repo `hermes` runtime.

Nothing about the *data contract* changes. The schema authority, the gates, the provenance rules,
the spend/audit substrate, and the per-WP acceptance criteria are all preserved exactly. We spent a
long time getting this build correct; the job here is to **continue it without losing accuracy**,
not to re-derive it.

---

## 0. Authority chain — read these first, in this order

1. `docs/MASTER_REBUILD_PLAN.md` — single authority for the V3 rebuild (§5 schema, §8.1 lawful
   acquisition, §8.2 spatial, §9 corpus). Everything below is **subordinate** to it.
2. `docs/CORPUS_COMPLETENESS_PLAN.md` — the per-phase mechanics (Phases 0–6). The WPs below are the
   *dispatch sheet*; the phase mechanics live there.
3. `docs/OPEN_VOCAB_REBUILD_PLAN.md` — **supersedes WP6's closed vocabulary.** Extractors propose any
   `snake_case` rule_key; canonicalisation is post-hoc. Do not enforce the old fixed rule matrix as a
   hard gate.
4. `docs/CODEX_DEPLOY_SYNC_RUNBOOK.md` — the local→Git→GitHub→VPS sync procedure. Section 9 below is
   the Kimi-specific condensation of it; that file remains the source of truth for deploy.
5. `CLAUDE.md` / `AGENTS.md` at repo root — deployment architecture is **LOCKED**. One host (the
   VPS), same-origin, Vercel retired. Do not relitigate.

If anything below conflicts with #1–#3, those win. If a step is ambiguous: write an escalation row
(`review_items` table, or `reports/escalations.jsonl` if the DB is unreachable) and move on. **Never
stall. Never invent schema — Alembic only.**

---

## 1. This is a CONTINUATION, not a greenfield build

The database is already substantially built. Verified state from `reports/db_state.json` (regenerate
it in WP0 before doing anything — these are last-known values, treat as approximate):

| Area | Status |
|---|---|
| Migrations | `0001`–`0019` exist on disk (`src/draftcheck/db/alembic/versions/`). Last recorded `alembic_current` = `0015`; **WP0 must confirm the live head.** |
| Spatial spine | `address_points` ≈ 1,673,135 · `parcels` ≈ 369,442 · `lg_areas` ≈ 139 · `planning_features` ≈ 33,120 · `spatial_datasets` = 9 |
| Corpus | `target_manifest` = 491 (acquired 281, metadata_only 19, out_of_scope 191) · `source_documents` = 280 · `source_versions` = 362 · `source_chunks` = 28,865 · `clauses` = 37,301 |
| Rules | `rules` = 118 · `rule_candidates` = 7,531 · `legal_edges` = 3,335 · `resolved_rules` = 16. (Git history records a prod-grade pass: **1,723 faithful rules, audited 1.00** — `git log` commit `c198483`.) |
| Evals | `eval_cases` = 19 · `eval_runs` = 16 |
| Adversarial | `adversarial_findings` = 0 (WP8 not yet meaningfully run) |
| Councils live | Cockburn (pilot), Melville rollout in progress (per `docs/COUNCIL_ROLLOUT_PLAN.md`) |

**Implication for Kimi:** Every WP is *idempotent and resumable by design*. Re-running a WP must be
safe (content-hash / natural-key upsert). Do not truncate, do not rebuild from zero, do not "start
clean." Claim pending work, fill gaps, advance gates. The existing 281 acquired sources and the
audited rule set are the accuracy we are protecting.

---

## 2. The one structural change: Kimi IS the swarm (no Hermes)

In the original plan, LLM work could be dispatched to the governed `hermes` container runtime. **Do
not use Hermes.** Instead:

- **Kimi Code is the coordinator AND the worker substrate.** When a WP says "swarm: extractors, 1 per
  source_version," that means **Kimi opens one worker session per claimed work item** — a sub-task /
  parallel Kimi run — does the LLM reasoning itself, and writes results to the database. No external
  agent runtime, no `hermes` container, no `HERMES_BASE_URL`.
- **Coordination is still the database, never chat.** Workers never talk to each other. They claim a
  row, work it idempotently, and terminate it (`done` | `blocked` | `escalated`). See §4.
- **The governance substrate still applies.** Every LLM/model invocation Kimi makes on behalf of a WP
  must still write a `job_traces` row (model, prompt_hash, skill_version_id, input/output artifact
  ids, tokens, cost) and respect the spend controls. The substrate exists independently of who runs
  the model — Hermes was one client of it; Kimi is now the client. Do **not** remove or bypass
  `job_traces` / `spend_events` writes just because Hermes is out of the loop. (In `db_state.json`,
  `spend_events` = 68,204 — that accounting continues.)
- The `hermes` container can remain defined in `infra/v3/compose.yml` for the running product, but it
  is **not part of this build-out's execution path.** The `HERMES_SPEND_CAP_CENTS` env still caps any
  LLM spend; honour it.

Concretely: each "pool" below is a Kimi fan-out. Bound it (start at 6 concurrent workers per pool,
raise only if upstream services tolerate it). Lawful fetch delays from MASTER_REBUILD §8.1 are
**per-worker**, so a bounded swarm respects robots/licence by construction.

---

## 3. Swarm architecture

```text
COORDINATOR  (Kimi, long-lived — one controlling session)
  - owns the dependency graph (§5); opens a WP only when its blockers' gates are green
  - shards each open WP into work items (DB rows), spawns worker sessions, retires them
  - never does object-level work itself: only dispatch, gate-checking, report assembly,
    git/VPS sync after each gate (§9)

WORKER POOLS (disposable, stateless, restart-safe Kimi sessions)
  - spatial-loaders      WP2   1 per dataset                  (6 workers)
  - index-scrapers       WP3   1 per authoritative index      (6 workers)
  - fetchers             WP4   1 per manifest/LGA shard        (6–20 workers)
  - citation-resolvers   WP5   1 per acquired source_version
  - extractors           WP6   1 per rule-bearing source_version
  - edge-proposers       WP7   1 per cited instrument pair
  - adversaries          WP8   5 roles × 1 per corpus slice; Defense pool spawns after attackers
  - seeder               WP9   1 worker
```

**Worker lifecycle (every worker, every pool):**

1. **Claim** a work item atomically with a lease (so a dead worker's item is auto-recovered):
   ```sql
   UPDATE <queue> SET claimed_by = :worker,
                      lease_expires_at = now() + interval '30 min'
   WHERE id = (
     SELECT id FROM <queue>
     WHERE status = 'pending'
       AND (lease_expires_at IS NULL OR lease_expires_at < now())
     ORDER BY id
     LIMIT 1
     FOR UPDATE SKIP LOCKED
   )
   RETURNING *;
   ```
   The queues are the natural tables: `target_manifest` (WP3–5), `source_versions` (WP6),
   `adversarial_findings` (WP8 Defense), `spatial_datasets` (WP2).
2. **Work** the one item, idempotently (content-hash / natural-key upsert). Re-doing it must not
   double-write.
3. **Terminate** it: `done` | `blocked` (+ a one-command unblock note) | `escalated` (write a
   `review_items` row). **Never leave an item claimed.** Lease expiry makes worker death safe.

**Swarm rules:**

- Any worker can die at any time; a replacement claims the lease-expired item. No state in the
  worker, ever.
- Two workers writing the same natural key is resolved by idempotent upsert, not by locking beyond
  the claim. If a WP can't be made idempotent, it does **not** get a swarm — it gets **one** worker
  (WP0, WP7 precedence ruleset, WP9).
- The coordinator re-runs each WP's gate query after the pool drains. Gate red → re-shard the
  failures only, not the whole WP.

---

## 4. Coordination is the database (claim/lease pattern)

There is no message bus and no shared scratch file. The lease query in §3 is the entire coordination
protocol. A few invariants:

- **Lease, don't lock.** Hold `FOR UPDATE SKIP LOCKED` only for the duration of the claim UPDATE,
  then release. The 30-minute lease is what protects against crashed workers, not a held transaction.
- **Idempotency keys are natural keys:** `sha256` for source content, `(alias_text)` for
  `instrument_aliases`, `(dataset_id)` for `spatial_datasets`, `(round, agent_role, target, claim)`
  for `adversarial_findings`. Upsert on these.
- **Every fetch** writes a `source_fetch_log` row. **Every approve/override** writes an `audit_events`
  row. These are non-negotiable provenance.
- **Reports are the proof, not the chat log.** Every WP gate emits a JSON/CSV under `reports/` and it
  gets committed (§9). If the chat is lost, the reports + the DB are the record.

---

## 5. Dependency graph

```text
WP0 state probe
 └─ WP1 schema gaps (one migration, only if a gap is found)
     ├─ WP2 spatial spine load          (parallel with WP3+)
     ├─ WP3 scope + manifest            → WP4 acquisition (fan-out)
     │                                     → WP5 citation closure (loop to WP4)
     │                                        → WP6 extraction + rule matrix (fan-out)
     │                                           → WP7 legal graph + conflict sweep
     │                                              → WP8 adversarial rounds
     └─ WP9 eval seed load (anytime after WP1)
WP10 freshness + CI assertions (after WP6; permanent)
```

The coordinator opens a downstream WP only when every blocker's gate report is green and committed.

---

## 6. Work packages (WP0–WP10)

Each WP lists: **inputs / the exact script(s) that already exist / gate (machine-checkable) /
escalation.** Prefer the existing `scripts/wp*.py` — they encode the accuracy we are protecting. Do
not reimplement them; call them, and only extend them through a PR if a real gap exists.

### WP0 — State probe (1 worker, 1 session) — DO THIS FIRST, EVERY RUN

Never plan against an imagined DB.

- On the VPS (see §9 for connection): `alembic current`, `alembic heads` — confirm they match and
  record the head (disk has `0019`; the live DB may be behind — find out).
- Regenerate `reports/db_state.json`: row counts for every §5 table
  (`SELECT relname, n_live_tup FROM pg_stat_user_tables ORDER BY relname`).
- Confirm extensions: `SELECT extname FROM pg_extension` must include `postgis` and `vector`.
- Confirm Procrastinate schema is applied (table presence or `procrastinate schema --check`).

**Gate:** `reports/db_state.json` committed. **Escalate (do not fix):** missing extension, divergent
alembic head, any §5 table that migrations claim to create but is absent.

### WP1 — Schema gaps (1 worker, 1 PR) — likely already satisfied

The three tables this WP originally added — `target_manifest`, `instrument_aliases`,
`adversarial_findings` — **already exist** (they appear in `db_state.json`, and migrations run to
`0019`). So WP1 is normally a no-op: confirm presence and move on.

Only if WP0 reveals a genuinely missing column/table: add **one** Alembic migration
(`00NN_<purpose>`), with matching SQLAlchemy models, `upgrade` + `downgrade` both tested in CI.

**Gate:** `alembic upgrade head && alembic downgrade -1 && alembic upgrade head` green in CI; **no
`create_all` anywhere** (the import-linter rule must stay green: `lint-imports --config
pyproject.toml`).

### WP2 — Spatial spine load (swarm: spatial-loaders, 1 per dataset)

Per MASTER_REBUILD §8.2 + Appendix B. Existing scripts: `scripts/wp2_spatial_load.py`,
`scripts/wp2_council_spatial.py`, `scripts/spatial_stamp_rcodes.py`. All idempotent; everything →
**GDA2020 (EPSG:7844)** at import; every load writes a `spatial_datasets` row (dataset_id, licence,
licence_status, source_crs, version, fetched_at, refresh_due) **before** feature rows.

| Dataset | Target table | Source | Note |
|---|---|---|---|
| G-NAF address points (WA) | `address_points` | Geoscape via data.gov.au | quarterly; EULA CC-BY-4.0-based |
| Cadastre (pilot LGA first) | `parcels` | Landgate SLIP public tier | `licence_status=review` until Landgate commercial terms confirmed — load, but resolver flags it |
| LGA boundaries | `lg_areas` | Landgate admin boundaries | merge with council registry |
| Scheme zones + R-codes | `planning_features` (layer_type=zone) | DPLH-071 WFS | pilot LGA first |
| Bushfire-prone areas | `planning_features` (bushfire) | SPP 3.7 mapping via SLIP | confirm dataset ID at import |
| Heritage | `planning_features` (heritage) | state + local registers | confirm dataset ID at import |

Dumb rules: fetch fails 3× → log to `source_fetch_log`, mark the dataset row
`licence_status=blocked` with a one-command unblock note, continue. **Never hand-digitise. Never load
a dataset without a licence note.**

**Gate:** `reports/spatial_load.json` — per dataset: row count > 0 (or blocked + reason), CRS
confirmed 7844 (`SELECT DISTINCT ST_SRID(geom)`), spatial index present. Smoke test: one known
pilot-LGA address resolves end-to-end (G-NAF point → parcel → LGA → zone/R-code) and writes
`property_facts` rows with `method=parcel_intersection`.

### WP3 — Scope + target manifest (scope: 1 worker; then swarm: index-scrapers, 1 per index)

CORPUS_COMPLETENESS_PLAN Phases 0–1 verbatim. Existing scripts:
`scripts/build_wa_council_manifest.py`, `scripts/wp3_manifest_seed.py`, `scripts/wp3_reconcile.py`,
`scripts/wp3_melville_manifest.py`, `scripts/wp0_scope_cockburn.py`, `scripts/resolve_manifest_urls.py`.

1. Maintain `docs/CORPUS_SCOPE.md` (in / metadata-only / out-of-scope per the plan).
2. Seed/extend `target_manifest` from existing audits + `build_wa_council_manifest.py`, then scrape
   the **six authoritative indexes**: legislation register, DPLH SPP index, DPLH DC policies,
   pilot-LGA council pages, ABCB NCC index, PlanWA/SLIP catalogue.
3. Reconcile every existing `source_document` → matched to a manifest row (`acquired` + FK) or flagged
   `orphan_source` (`wp3_reconcile.py`).

**Gate:** `reports/manifest_closure.json` — **0 `orphan_source`** (this is the hard requirement);
per-category counts printed. (`reports/manifest_closure.json` already exists — extend, don't clobber.)

### WP4 — Acquisition (swarm: fetchers, claim `target_manifest` rows where status=`pending`)

CORPUS_COMPLETENESS_PLAN Phase 2 verbatim. Existing script: `scripts/wp4_acquire.py` (and
`scripts/wp4a_parse_melville_clauses.py` for council-specific parsing).

For each `pending` manifest row: **lawful fetch** → `source_documents` → `source_versions` (sha256)
→ `artifacts` → parse → chunk → FTS + embeddings (**pinned embedding model**, `embedding_model`
recorded per chunk).

Rules: 3 failed fetches → `blocked` + unblock note, continue. Unparseable after OCR fallback →
`blocked`, artifact preserved (a doc we can't read is **NOT** acquired). Paid/licensed →
`metadata_only`, **never store full text.** No source supports answers until `source_reviews` pass.

**Gate:** `reports/acquisition_report.json` — **0 `pending`**; every `acquired` row has
`parse_status=ok` + chunks + embeddings (SQL assertion). Cross-check `embedding_audit.json`.

### WP5 — Citation closure (swarm: citation-resolvers, 1 per source_version; coordinator owns the loop)

Phase 3 verbatim. Existing script: `scripts/wp5_citations.py`. Each worker claims one acquired
`source_version`, extracts cross-references (**deterministic pass + LLM pass — the LLM pass is Kimi
itself, not Hermes**) → `legal_edges` `relation=cites` → resolves against the manifest via
`instrument_aliases` → an unresolved reference becomes a new `target_manifest` row `pending`
(idempotent insert by alias key).

**The coordinator runs the fixpoint loop:** pool drains → any new `pending` rows? → re-open WP4 for
them, then re-shard WP5 over the *new* versions only. Repeat until a full pass adds zero rows.

**Gate:** `reports/citation_closure.json` — **0 unresolved external_references**, fixpoint reached.
(`reports/citation_closure.json` exists — this is the live artifact.)

### WP6 — Extraction + rule matrix (swarm: extractors, claim rule-bearing `source_versions`)

> **Active pipeline = `docs/OPEN_VOCAB_REBUILD_PLAN.md` (supersedes the old closed vocabulary,
> 2026-06-14).** Extractors propose **any** `snake_case` rule_key (structurally validated by
> `validators.validate_rule_key`, `[a-z][a-z0-9_]{2,60}`). The former fixed Tier-1 key set is now a
> **soft hint only** (`RULE_KEY_HINTS` / `is_hinted_key()` in
> `src/draftcheck/extraction/vocabulary.py`), not a drop filter. Raw keys are canonicalised post-hoc
> into the `canonical_rule_key` column (migration `0018_rule_canonical_keys`).

This is the largest WP and where the bulk of the existing `scripts/wp6_*.py` toolchain lives. The
pipeline, in order:

1. **Extract** — `scripts/wp6_extract.py`: structure pass → 3-pass blind ensemble (temp 0, strict
   JSON, **mandatory quote anchors**). *This is Kimi doing the model passes itself.*
2. **Decode / re-decode** — `scripts/wp6_decode.py`, `wp6_redecode.py`, `wp6_promote_decode.py`,
   `wp6_solo_promote.py`.
3. **Validate** — deterministic universal validators: quote-anchor, no-orphan-numbers,
   normative-language, operator/unit canonical, `validate_value_finite`,
   `validate_unit_category_sanity`. These catch garbage regardless of key.
4. **Adjudicate** — `scripts/wp6_adjudicate.py`, `wp6_challenge.py`: 3/3 auto-accept @0.95, 2/3
   challenge, else `pending_review`. Drain `pending_review` with `wp6_pending_adjudicate` logic.
5. **Correct / review** — `scripts/wp6_correct.py` (faithfulness correction), `wp6_review.py`,
   `wp6_apply_open_review.py`, `wp6_apply_adv_review.py`, `wp6_sonnet_postprocess.py`.
6. **Cluster + register** — `scripts/wp6_cluster_keys.py` → `wp6_apply_clustering.py` populate
   `canonical_rule_key`; `wp6_register_checks_from_clusters.py` generates
   `src/draftcheck/checks/registry_generated.py` (CheckDefinitions derived from clusters, **not**
   declared up-front).
7. **Curate** — e.g. `scripts/wp6_curate_lot_area_operators.py` for known operator cleanups.

Mandatory data rules: `pathway` on every R-Codes atom; a DTC atom without its design-principle
sibling linked `performance_alternative_to` = **audit failure**. Table clauses get the vision pass
with cell coordinates in provenance.

**Per-doc acceptance gate** (CI assertion — a `source_version` cannot go `active` otherwise): 100%
dispositions, 0 orphan numbers, 0 unresolved exception clauses, `pending_review` drained.

**Gate:** `reports/rule_matrix.csv` — Tier-1 keys × R5–R80 × pilot LGA filled (approved atom or cited
`n/a`). Golden evals green. **Treat the matrix as coverage telemetry, not a vocabulary ceiling** —
the open-vocab pipeline accepts new keys and canonicalises post-hoc. The accuracy bar to protect is
the audited **1.00 faithfulness** recorded in git (`c198483`); do not regress it.

### WP7 — Legal graph + conflict sweep (swarm: edge-proposers, 1 per instrument pair; precedence + sweep: 1 worker)

Phase 4b verbatim. Existing script: `scripts/wp7_conflict_sweep.py`.

**Swarmed:** exception atoms (`rule_type=exception` + `exception_to` edge; base rule blocked from
`approved` while its exception is unresolved) and **blind 2-model edge proposal** (Kimi runs both
model passes, different families if possible) — one worker per instrument pair where WP5 found
citations. **Verbatim quote required, validator-confirmed.**

**NOT swarmed (1 worker, after the edge pool drains):** the precedence ruleset in code
(`src/draftcheck/checks/`, **never AI-decided**) and the deterministic conflict sweep + dependency
closure.

**Gate:** 0 unstructured exception clauses; 0 quoteless edges; `reports/conflict_sweep.json` empty;
dependency closure 100%. (`reports/conflict_sweep.json` exists.)

### WP8 — Adversarial rounds (swarm: adversaries — 5 roles × 1 worker per corpus slice)

Phase 5 verbatim. `adversarial_findings` currently = 0, so this is the **biggest remaining quality
lift.** All five attacker roles are Kimi worker pools, sharded by corpus slice, writing **only** to
`adversarial_findings`:

- **Re-extractor** — blind, different model family from WP6.
- **Prosecutor** — DB-only answers verified against raw sources.
- **Gap hunter** — web vs manifest.
- **Conflict prosecutor** — concrete lot fact-patterns → exactly one winner or cited
  `needs_more_info`.

The **Defense pool spawns after attackers drain**, claims `open` findings via the standard lease
query (§3), and either fixes or refutes with a verbatim quote — no third option. **Judge** (1 worker)
resolves disputes; every confirmed finding adds a golden eval case. The coordinator counts the round
and decides stop/continue.

**Gate:** 2 consecutive full rounds with **zero confirmed findings** → `reports/adversarial_closure.json`.

### WP9 — Eval seed + label load (1 worker, anytime after WP1)

Existing scripts: `scripts/seed_eval_data.py`, `scripts/harvest_legacy_db.py`,
`scripts/wp9_complete_db.py`, `scripts/wp9_pending_adjudicate.py`.

1. Load `evals/seeds/*.jsonl` into `eval_cases` / `eval_runs` / clause-disposition labels
   (idempotent — content-hash dedupe).
2. Verify counts vs `DATA_INVENTORY.md` (19 golden cases, 65 dispositions, 6 rule_rows). DB already
   shows 19 eval_cases — confirm, don't duplicate.
3. Archive `draftcheck.db` + `draftcheck-corpus.db` out of the working tree per MASTER_REBUILD §4.2
   (storage archive + `.gitignore`; confirm seeds committed first).

**Gate:** ≥19 eval cases in DB; `draftcheck.db` **no longer** in `git ls-files`.

### WP10 — Freshness + CI (1 worker, permanent)

Phase 6 verbatim. Weekly watcher job (re-scrape indexes → diff → `pending` → auto-WP4; changed
sha256 ⇒ new `source_version`, old rules → `stale`; an amendment without re-extraction in 7 days =
**red CI**). CI on every merge asserts: manifest closure, citation closure, per-doc gates, rule
matrix fill, golden evals, 0 open adversarial findings >14 days. Runtime backstop: weekly clustering
of `unsupported`/`needs_more_info` answers → Gap-hunter findings.

**Gate:** scheduled job live on the VPS; CI assertions merged and green.

---

## 7. Per-council repeat recipe

After the pilot (Cockburn) and the in-flight second council (Melville), each new LGA is a repeat of
WP2 (council spatial) → WP3 (council manifest) → WP4–WP8 scoped to that council. Follow
`docs/COUNCIL_ROLLOUT_PLAN.md` and claim the council's row in its shared status tracker before
starting (council-scope isolation — WP-0 of that plan — comes before the second council's data lands;
see git commits `d0cf780`, `337ac6f`). Use `--scope <council>` flags where the wp scripts support them.

---

## 8. Standing rules (every worker, every WP)

- **Alembic is the only schema authority.** No `create_all`, no ad-hoc DDL.
- **Idempotent jobs only:** re-running any WP must be safe (content-hash / upsert by natural key).
- **Every fetch → `source_fetch_log`; every approve/override → `audit_events`.**
- **Every LLM call → `job_traces` + `spend_events`,** and respects `HERMES_SPEND_CAP_CENTS` (the cap
  applies to Kimi's spend now). The breaker pauses extraction/agent queues only; deterministic jobs
  keep running.
- **Outputs are advisory.** Never claim final legal/planning/building/certification compliance. Cite
  approved source versions or return `unsupported` / `needs_more_info`. Statuses are
  `likely_pass / likely_fail / needs_more_info / unsupported`.
- **Prefer deterministic calculations** for measurements; absent/ambiguous → return missing info.
- **Blocked ≠ stalled:** record the blocker + a one-command unblock, continue, list it in the final
  report.
- **All reports land in `reports/` and are committed** — they are the proof, not the chat log.

---

## 9. Connect, upload-as-you-go, keep it clean (VPS + GitHub)

This is the part that keeps everything in sync. The coordinator does this **after every green gate**,
not once at the end. Authority: `docs/CODEX_DEPLOY_SYNC_RUNBOOK.md`. Standing approval is recorded
(operator Steven, `CLAUDE.md` 2026-06-09): **commit, push, open PRs, merge once CI is green, deploy to
the VPS, change CI, run backups — without pausing to ask.**

### 9.1 The three places state lives, and the rule

| Place | What | How Kimi reaches it |
|---|---|---|
| **Local repo** | working tree, `reports/`, code, migrations | `C:\Dev\Cuz` (branch `main`) |
| **GitHub** | source of truth for code + committed reports | `origin = https://github.com/stevenshelley58-afk/cuz.fail.git`, via `gh` (already authenticated) |
| **VPS (production DB lives here)** | Postgres+PostGIS+pgvector, the live corpus | `ssh draftcheck` → `root@76.13.209.160` (host `srv1625369`); app checkout `/srv/draftcheck/app`; compose in `/srv/draftcheck/app/infra/v3` |

**The rule: code flows Local → GitHub → VPS. Data lives on the VPS. Reports flow VPS → Local →
GitHub.** The DB build runs *against the VPS Postgres* (that's the real corpus); the wp scripts read
DB connection from `infra/v3/.env` on the server. Run them on the VPS via `ssh draftcheck`, or against
the VPS DB over an SSH tunnel. **Never** create a second production DB.

### 9.2 Connect to the VPS

Resolve the target from `$DRAFTCHECK_VPS_HOST` or `Host draftcheck` in `~/.ssh/config`
(`root@76.13.209.160`). All server commands run inside `ssh draftcheck '...'`; the quoted command
executes on the server, not on Windows. Examples:

```bash
# Run a wp script against the live DB, on the server, inside the api container:
ssh draftcheck 'cd /srv/draftcheck/app/infra/v3 && \
  sudo docker compose exec -T api python scripts/wp4_acquire.py --limit 50'

# Probe DB state (WP0):
ssh draftcheck 'cd /srv/draftcheck/app/infra/v3 && \
  sudo docker compose exec -T api alembic current && \
  sudo docker compose exec -T db psql -U draftcheck -c "SELECT extname FROM pg_extension;"'
```

**Fallback if the VPS is unreachable:** do all GitHub-side work, write the exact `ssh draftcheck …`
commands needed into the final report as the one-command unblocks, and keep going. Do not block other
WPs on it.

### 9.3 Pull latest code onto the VPS before a DB run

The wp scripts must match the migrations on the server. Before running a WP's scripts:

```bash
ssh draftcheck 'cd /srv/draftcheck/app && git fetch origin && git reset --hard origin/main && \
  cd infra/v3 && sudo docker compose build api && sudo docker compose up -d --wait && \
  sudo docker compose exec -T api alembic upgrade head'
```

This is the same idea as `infra/v3/deploy.sh` (full-stack). For a **UI-only** change use
`infra/v3/deploy-web-only.sh` instead — do **not** run compose/Alembic/psql for a frontend fix.

### 9.4 Commit + push after every green gate (upload-as-you-go)

After a WP gate goes green, the coordinator pulls the fresh `reports/*.json` down from the VPS to
local, commits, and pushes. Per-WP cadence keeps history clean and recoverable:

```bash
# 1. bring the gate report(s) from the VPS into the local tree
scp draftcheck:/srv/draftcheck/app/reports/acquisition_report.json C:/Dev/Cuz/reports/

# 2. stage and PROVE nothing forbidden is staged
git add -A
git status --porcelain | grep -Ei "\.db|\.sqlite|\.storage/|data/corpus/|\.vercel/|^\?\? \.env|node_modules" \
  && echo "FORBIDDEN PATH STAGED - FIX" || echo "clean"
python scripts/precommit_guard.py $(git diff --cached --name-only)

# 3. commit with the WP + gate result in the message, push, PR, auto-merge on green CI
git checkout -b wpN/<short>
git commit -m "WPN: <what> — gate green (<report path>)"
git push -u origin wpN/<short>
gh pr create --title "WPN <short>" --body "Gate: reports/<x>.json green. Authority: docs/DB_BUILDOUT_KIMI_SWARM_PLAN.md + MASTER_REBUILD_PLAN.md."
gh pr merge --auto --squash --delete-branch
gh pr checks --watch
git checkout main && git pull
```

Small follow-ups (doc fixes, a single script tweak) may go straight to `main`; CI runs on push.

### 9.5 Tripwires — NEVER commit these (keeps the repo clean)

`.gitignore` + `scripts/precommit_guard.py` enforce this; GitHub will reject the 153 MB DB anyway. Do
not weaken either.

- **Never stage/commit:** `*.db` / `*.sqlite*` (incl. `draftcheck.db`), `.storage/`, `data/corpus/`,
  `.vercel/`, `.env` / `.env.*` (except `.env.example`), `node_modules/`, `web/dist/`, `.codex/`.
- **Never:** force-push, rewrite history, `git clean`, delete legacy `apps/ packages/ api/ ui/` (M1
  work), add `create_all` to V3, mount anything besides `/api/v1` in the new app.
- **Secrets** are generated on the VPS and live only in `infra/v3/.env` there — never committed.

Anything not on those lists is yours to do without asking.

### 9.6 Local pre-push gate (mirror of CI)

Before pushing code (not needed for reports-only commits):

```bash
pip install -e ".[dev]"
python -m ruff check .
python -m mypy src
lint-imports --config pyproject.toml
python -m pytest -q                 # expect ~342+ passing
( ! grep -R "create_all" src web )  # must find nothing
cd web && npm ci && npm run build && cd ..
git diff --check
```

### 9.7 Backups before destructive DB work

Any WP that rewrites large tables: take a dump first.

```bash
ssh draftcheck 'cd /srv/draftcheck/app/infra/v3 && \
  sudo docker compose exec -T db pg_dump -U draftcheck -Fc draftcheck \
  > /srv/draftcheck/backups/draftcheck-$(date +%F-%H%M).dump'
```

Nightly cron already exists (`/etc/cron.d/draftcheck-backup`). If `$RESTIC_*` creds are present,
offsite is configured; if not, local dumps only — note "offsite pending creds" in the report.

### 9.8 End-of-run sync assertion

```bash
git status --porcelain                                          # empty
git rev-parse main origin/main                                  # identical
gh run list --branch main --limit 1                             # CI: success
ssh draftcheck 'git -C /srv/draftcheck/app rev-parse HEAD'      # == origin/main
ssh draftcheck 'cd /srv/draftcheck/app/infra/v3 && sudo docker compose ps'   # healthy
curl -fsS https://lotfile.app/api/v1/ready                      # 200
```

In sync = local `main` == `origin/main` == VPS HEAD, CI green, compose healthy, `/ready` 200, no
Vercel deploys.

---

## 10. Final report (instead of asking questions along the way)

End the run with: which WPs advanced (with before/after row counts from `db_state.json`), every gate
result (report path + pass/fail), the commits/tags pushed, decisions taken autonomously, and the
short list of items blocked on missing credentials (VPS host, DNS token, restic creds — whichever
applied) — **each with the exact one command Steven runs to unblock it.**

The proof of accuracy is: gates green in `reports/`, golden evals passing, WP6 faithfulness ≥ the
recorded 1.00 audit, `adversarial_findings` reaching 2 clean rounds, and local == GitHub == VPS.
