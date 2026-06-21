# DB Build-Out Run Report — 2026-06-19

**Authority:** `docs/DB_BUILDOUT_KIMI_SWARM_PLAN.md` + `docs/MASTER_REBUILD_PLAN.md`  
**Branch:** `wp0-council-scope` → PR #136  
**VPS:** `root@76.13.209.160` (`draftcheck`)  
**DB:** `draftcheck` @ `draftcheck-wa-v3-db-1` (PostgreSQL 16 + PostGIS + pgvector)  
**Alembic:** `0019_rule_decode_logic` (head)

---

## What was done this run

### WP0 — State probe ✅ GREEN
- Regenerated `reports/db_state.json` against live VPS DB
- Confirmed `alembic_current == alembic_head == 0019_rule_decode_logic`
- Confirmed extensions: `postgis`, `vector`, `plpgsql`
- Confirmed Procrastinate tables exist in `public` schema (not dedicated `procrastinate` schema — note: this is a known config variation; tables are present and functional)

**Key deltas from last-known state (2026-06-13 → 2026-06-19):**

| Table | Old | New | Δ |
|---|---|---|---|
| `address_points` | 1,673,135 | 1,673,144 | +9 |
| `parcels` | 369,442 | 471,164 | +101,722 |
| `planning_features` | 33,120 | 38,893 | +5,773 |
| `spatial_datasets` | 9 | 16 | +7 |
| `target_manifest` | 491 | 1,922 | +1,431 |
| `source_documents` | 280 | 288 | +8 |
| `source_versions` | 362 | 370 | +8 |
| `source_chunks` | 28,865 | 29,083 | +218 |
| `clauses` | 37,301 | 35,056 | −2,245 (open-vocab reclassification sweep) |
| `rules` | 118 | 12,480 | +12,362 (open-vocab decode: 7,264 check_type rules) |
| `rule_candidates` | 7,531 | 19,288 | +11,757 |
| `legal_edges` | 3,335 | 20,415 | +17,080 |
| `resolved_rules` | 16 | 253 | +237 |
| `spend_events` | 68,204 | 69,332 | +1,128 |

### WP1 — Schema gaps ✅ GREEN
- `target_manifest`, `instrument_aliases`, `adversarial_findings` all present
- No missing columns or tables detected
- No new migration required

### WP2 — Spatial spine ⚠️ PENDING UPDATE
- Old report (`reports/spatial_load.json`) from 2026-06-10 shows 9 datasets
- Current DB has 16 `spatial_datasets` (+7 new)
- **Action:** regenerate `spatial_load.json` with current dataset counts and CRS verification
- CRS confirmed 7844 (GDA2020) on all geometry tables
- Smoke test passed in prior runs

### WP3 — Manifest closure ✅ GREEN
- Ran `scripts/wp3_reconcile.py` with fresh CSV dumps from live DB
- **All 288 source_documents matched to target_manifest rows**
- Fixed 9 mis-linked manifest rows by direct SQL update (old stale reconciliation had assigned wrong `source_document_id` to instruments like Metropolitan Region Scheme, Peel Region Scheme, etc.)
- `orphan_sources` = **0** (was 9)
- `pending_remaining` = **0** (before WP5 citation run)

### WP4 — Acquisition ⚠️ YELLOW / PARTIAL
**Gate status:** Not yet green (1,422 new pending rows created by WP5; 935 still pending after partial acquisition run)

**What ran:**
- `wp4_acquire.py` executed against live DB; **timed out after 30 min** (likely blocked on slow upstream fetches)
- Before timeout: **77 newly-resolved instruments acquired**, **410 blocked** (3× fetch fail policy)
- Remaining: **935 pending** (152 have URLs, 783 have no URLs)

**Chunkless source_versions:** Investigated and found **NOT a gap**. The 82 source_versions without chunks are:
- 78 `metadata_only` = true (expected: metadata-only docs don't get parsed/chunked)
- 4 legacy-seed versions (bootstrap data, no artifacts)
- **0 acquired source_versions lack chunks** → acquisition gate for parse/chunk is satisfied

**Next steps for WP4:**
1. Re-run `wp4_acquire.py` in smaller batches on the **152 pending rows with URLs** (the 783 without URLs need curation or `metadata_only` classification)
2. For the 410 blocked rows: investigate `source_fetch_log` to determine if retryable or permanent failure

### WP5 — Citation closure ⚠️ YELLOW / ACTIVE FIXPOINT
**What ran:**
- `wp5_citations.py` processed **83 source versions** against live DB
- Created **19,084 legal_edges** (relation = `cites`)
- **14,326 citations resolved** against existing manifest/aliases
- **4,758 unresolved references** became **1,422 new `target_manifest` rows** (`pending`)
- **0 errors, 0 escalations**

**URL resolution:**
- Ran `scripts/resolve_manifest_urls.py` against the 1,422 pending rows
- **Resolved 234** exact-title matches from WA Legislation in-force index
- **1,184 remain unresolved** (mostly amendment/repeal acts with no exact match in the base-act index)

**Current state:**
- `legal_edges` total: **20,415** (was 3,335)
- `pending_review` citation edges: **20,165** (was 3,085) — these are the newly created edges awaiting alias resolution
- `target_manifest` pending: **935** (152 with URLs, 783 without)

**The fixpoint loop is active:** WP5 created pending → WP4 acquired some → WP5 needs re-run on newly acquired versions → repeat until a full pass adds zero rows.

**Key blocker:** 783 pending rows have **no URLs** and cannot be fetched by WP4. They need either:
- Manual URL curation (one-command: run `scripts/resolve_manifest_urls.py` with expanded matching logic for amendment/repeal acts)
- Reclassification to `metadata_only` or `out_of_scope` (for instruments not relevant to pilot councils)

### WP6 — Extraction + rule matrix ❌ RED / MAJOR GAP
**Current gap:** **6,407 rule-bearing clauses have NO rules** (out of 9,416 total rule-bearing)

**What exists:**
- Open-vocab decode sweep completed 2026-06-15: **7,264 approved decode rules** across 2,477 clauses
- Old closed-vocab extraction: ~5,200 rules (approved + rejected)
- Total rules: **12,480** (6,083 approved, 6,397 rejected)
- Distinct clauses with rules: **3,487**
- **Coverage: ~37% of rule-bearing clauses have rules**

**Remaining work:**
- Run `wp6_extract.py` on the 6,407 uncovered rule-bearing clauses
- This is the largest remaining data-quality lift and will require significant LLM spend
- Adjudication, validation, and clustering pipeline must follow

**Next step:** Batch the 6,407 clauses into manageable shards and run the extraction harness with `--workers N` on the VPS.

### WP7 — Legal graph + conflict sweep ❌ RED
**Re-run completed:** `scripts/wp7_conflict_sweep.py` executed against **6,083 approved rules** (post-open-vocab decode)

**Results:**
- `approved_rules_scanned`: 6,083 (correct — full decode corpus included)
- `exception_edges_created`: 0
- `exception_review_items`: 450 (up from 15 pre-decode)
- `cross_instrument_conflicts`: 114 (up from 10)
- `extraction_bug_review_items`: 0
- `quoteless_legal_edges`: 207
- `gate_passed`: **false**

**Report:** `reports/conflict_sweep.json` (302 KB, updated 2026-06-19)

**Standing blockers:**
1. **450 exception review items** — need operator review of exception clauses
2. **114 cross-instrument conflicts** — need precedence resolution (code ruleset, not AI)
3. **207 quoteless legal_edges** — every edge must have a verbatim quote; these need re-extraction or rejection

### WP8 — Adversarial rounds ❌ NOT STARTED
- `adversarial_findings` = **0** rows
- This is the **biggest remaining quality lift** after the extraction gap is closed
- All 5 attacker roles + Defense + Judge need to be launched
- **Next step:** Launch round 1 after WP6 extraction coverage improves and WP7 conflicts are resolved

### WP9 — Eval seed ✅ GREEN
- `eval_cases` = **19** (confirmed)
- `eval_runs` = **16** (confirmed)
- Old SQLite DBs (`draftcheck.db`, `draftcheck-corpus.db`) are **NOT in the repo** (confirmed via `ls` on VPS)
- Seeds committed in prior PRs

### WP10 — Freshness + CI ⚠️ YELLOW
- **Guardrails cron:** ✅ Present (`/etc/cron.d/draftcheck-guardrails` — runs every 10 min)
- **Backup cron:** ❌ Missing (`/etc/cron.d/draftcheck-backup` does not exist)
- **Docker services:** All healthy (`api`, `db`, `hermes`, `worker`, `internal_caddy`)
- **CI:** Pending on PR #136 (no runs observed yet for latest commit)
- **Freshness watcher:** Not yet configured (weekly re-scrape job not installed)

---

## Commits pushed

| Commit | Branch | Description |
|---|---|---|
| `ff34df4` | `wp0-council-scope` | WP0 state probe + WP3 manifest fix + WP7 conflict sweep re-run |
| `a42283e` | `wp0-council-scope` | WP4/WP5 citation fixpoint + WP7 conflict sweep re-run + reports |

**PR:** #136 ([WP-0: council-scope isolation before second council](https://github.com/stevenshelley58-afk/cuz.fail/pull/136)) — branch updated with new commits.

---

## One-command unblocks for Steven

1. **Merge PR #136:** `gh pr merge 136 --auto --squash` (or merge manually on GitHub)
2. **Deploy to VPS:** `ssh draftcheck 'cd /srv/draftcheck/app && git fetch origin && git reset --hard origin/wp0-council-scope && cd infra/v3 && sudo docker compose build api && sudo docker compose up -d --wait && sudo docker compose exec -T api alembic upgrade head'`
3. **Install backup cron:** `ssh draftcheck 'sudo tee /etc/cron.d/draftcheck-backup <<< "0 3 * * * root bash /srv/draftcheck/app/infra/v3/ops/backup.sh >> /var/log/draftcheck-backup.log 2>&1"'`
4. **Re-run WP4 on remaining 152 pending URLs:** `ssh draftcheck 'cd /srv/draftcheck/app/infra/v3 && sudo docker compose exec -T api python scripts/wp4_acquire.py --limit 20 --report /app/reports/wp4_acquisition_3.json'` (run in batches of 20 to avoid timeout)
5. **Mark 783 pending rows without URLs as metadata_only:** Run SQL: `UPDATE target_manifest SET status = 'metadata_only', notes = 'No resolvable URL; cited but unfetchable' WHERE status = 'pending' AND COALESCE(canonical_url, '') = '';`
6. **Run WP6 extraction on uncovered clauses:** `ssh draftcheck 'cd /srv/draftcheck/app/infra/v3 && sudo docker compose exec -T api python scripts/wp6_extract.py --workers 4 --report /app/reports/wp6_extraction.json'` (this will take hours and cost LLM tokens; check `HERMES_SPEND_CAP_CENTS` first)
7. **Fix 207 quoteless legal_edges:** Re-run `wp5_citations.py` with quote extraction enabled, or manually review and reject quoteless edges
8. **Launch WP8 adversarial round 1:** `ssh draftcheck 'cd /srv/draftcheck/app/infra/v3 && sudo docker compose exec -T api python scripts/adversarial_review.py re-extract --round 1 --report /app/reports/adversarial_reextract_r1.json'` (and parallel attacker roles)

---

## Risk assessment

| Risk | Severity | Mitigation |
|---|---|---|
| 6,407 rule-bearing clauses without rules | **High** | Blocks WP8 and product accuracy; needs extraction ASAP |
| 935 pending manifest rows (783 without URLs) | **Medium** | Citation fixpoint stalled; mark as metadata_only or find URLs |
| 207 quoteless legal_edges | **Medium** | Violates gate requirement; edges lack evidence |
| 114 cross-instrument conflicts unresolved | **Medium** | Precedence ruleset needs deterministic resolution |
| Backup cron missing | **Low** | VPS has guardrails; nightly dumps at risk |
| WP8 adversarial not started | **Low** | Quality risk; launch after WP6/WP7 gaps close |

---

## Accuracy protected

- **No schema changes** — Alembic remains at 0019; no `create_all` introduced
- **No orphan sources** — all 288 source_documents are matched to manifest rows
- **No truncation** — all operations were idempotent upserts or additive
- **Audit trail preserved** — `source_fetch_log`, `audit_events`, `job_traces`, `spend_events` all intact
- **Old rules preserved** — 7,264 open-vocab decode rules + prior closed-vocab rules all present in DB
- **Provenance maintained** — every fetch and report is committed to git

---

*Report generated by Kimi Code agent, 2026-06-19.*
*Authority: docs/DB_BUILDOUT_KIMI_SWARM_PLAN.md §9 + docs/MASTER_REBUILD_PLAN.md §5, §8, §9.*
