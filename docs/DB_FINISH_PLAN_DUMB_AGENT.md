# DB Finish Plan — Dumb-Agent Dispatch Sheet

Date: 2026-06-12. Subordinate to `docs/MASTER_REBUILD_PLAN.md` and
`docs/DB_BUILDOUT_AGENT_PLAN.md` (read both first; this file is the *remaining work only*,
with exact commands). Written for a cheap, dumb agent: no judgment calls. If a step is
ambiguous, write a row to `review_items` (or append to `reports/escalations.jsonl` if the
DB is unreachable) and move to the next step. **Never stall. Never invent schema.**

## How to run anything

- All work runs **inside the api container on the VPS**:
  `ssh draftcheck 'cd /srv/draftcheck/app/infra/v3 && sudo docker compose exec -T api <cmd>'`
- Long jobs (anything with LLM calls or >5 min): launch detached and poll the log:
  `sudo docker compose exec -dT api sh -c "python /app/scripts/<script>.py ... > /app/reports/<name>.log 2>&1"`
- **CRITICAL: every `git push` to main auto-redeploys and RESTARTS the api container,
  killing any running job inside it.** Do not push while a detached job is running.
  Iterate scripts via `scp` + `sudo docker compose cp <file> api:/app/scripts/...`,
  and commit+push only when the container is idle.
- Reports go to `/app/reports/*.json` in the container; copy them out
  (`sudo docker compose cp api:/app/reports/<f>.json /tmp/` then `scp`), commit them to
  `reports/` in the repo. Reports are the proof, not the chat log.
- DB queries for gates:
  `sudo docker compose exec -T api python -c "from sqlalchemy import create_engine,text; import os; c=create_engine(os.environ['DATABASE_URL']).connect(); print(c.execute(text(\"<SQL>\")).fetchall())"`

## Verified state (2026-06-12, do not re-derive)

- Prod healthy: `https://lotfile.app/api/v1/ready` all ok. Chat live (MiniMax-M3), think-tag
  leak fixed, local dev proxy fixed.
- Migrations at head (0015). Alembic is the ONLY schema authority.
- `target_manifest`: 203 acquired / 14 metadata_only / 17 out_of_scope / 2 blocked / **0 pending**.
  WP4 is DONE (`scripts/wp4_acquire.py`, report `reports/wp4_acquisition.json`).
- `rules` (wp6, lifecycle approved): 86. `rule_candidates`: 1070 validators_passed (506 of
  them single-model-family), 496 pending_review (being drained by wp9_pending_adjudicate),
  1930 validator_failed (dead by design), 313 rejected, ~271+ auto_promoted.
- `eval_cases`: 19 (WP9 seed gate green). 0 orphan source_documents (WP3 gate green).
- Known bugs already fixed in repo: `wp6_adjudicate.py` jsonb concat, `wp6_extract.py`
  `promote_rule` dict-row. Make sure the container copy matches the repo before running.

---

## Task 0 — Collect WP9 output (5 min, no LLM)

1. Check `/app/reports/wp9_adjudication.json` exists. If the log ends in a Traceback,
   re-launch once: `python /app/scripts/wp9_pending_adjudicate.py --report /app/reports/wp9_adjudication.json`.
2. Copy report to `reports/wp9_adjudication.json`, commit.

Gate: `SELECT count(*) FROM rule_candidates WHERE review_status='pending_review'` has
decreased vs 496 and the report's `promoted + still_pending + rejected` equals clauses
processed. Escalate if pending_review INCREASED.

## Task 1 — Unblock the 2 blocked manifest rows (15 min, no LLM)

For each row in `SELECT id, instrument_name, notes FROM target_manifest WHERE status='blocked'`:

1. The notes say "Suspected landing page". Find the real document URL:
   - "Planning and Development Act 2005": use the current consolidated PDF link from
     `https://www.legislation.wa.gov.au` (the "Versions" page for the Act; pick the
     latest "Official Version" PDF link).
   - "Greater Bunbury Region Scheme": same site, scheme text PDF.
2. `UPDATE target_manifest SET canonical_url='<pdf url>', status='pending', notes=NULL WHERE id='<id>'`
3. Run `python /app/scripts/wp4_acquire.py --limit 5 --report /app/reports/wp4_unblock.json`

Gate: 0 rows with status='blocked'. If a fetch fails 3× again → leave blocked, escalate, continue.

## Task 2 — WP5 citation closure (NEW SCRIPT, ~1 day, small LLM use optional)

Write `scripts/wp5_citations.py` modeled exactly on `scripts/wp4_acquire.py` (claim loop)
but over `source_versions`:

1. Work queue: every `source_versions` row that has chunks and no row in `legal_edges`
   with `relation='cites'` and `source_version_id=<id>` and `metadata_json->>'wp5'='true'`.
2. Per version, deterministic pass FIRST: regex sweep of chunk text for instrument names —
   patterns: `State Planning Policy [0-9.]+`, `Development Control Policy [0-9.]+`,
   `Local Planning Scheme No\.? ?[0-9]+`, `R-Codes|Residential Design Codes`,
   `[A-Z][a-z]+ (Act|Regulations) [0-9]{4}`, `AS/NZS [0-9.]+`, `NCC|Building Code of Australia`.
3. Resolve each match against `target_manifest.instrument_name` (case-insensitive exact,
   then `instrument_aliases`). Resolution writes a `legal_edges` row:
   `relation='cites'`, verbatim quote (the sentence containing the match) mandatory,
   `metadata_json={'wp5': true}`. Idempotent: unique on (source_version, target, quote hash) —
   use `ON CONFLICT DO NOTHING` with a deterministic id (uuid5 of those fields).
4. Unresolved match → idempotent insert into `target_manifest`
   (`status='pending'`, `category='unknown'`, `notes='WP5 unresolved citation from <sv id>'`,
   uuid5 by (name, authority)) AND an `instrument_aliases` row if it's an obvious alias.
5. After the pool drains: if any new `pending` rows were created, run
   `scripts/wp4_acquire.py` again, then re-run wp5 over ONLY the new versions.
   Repeat until a full pass adds 0 manifest rows (the fixpoint).

Gate: `reports/citation_closure.json` — counts of edges written, 0 unresolved references
remaining (every match resolved or escalated), fixpoint reached. Do NOT use an LLM unless
the deterministic pass plus aliases leaves unresolved matches; then one LLM pass per
document max, strict JSON, quote anchors mandatory.

## Task 3 — WP6 extraction over the new corpus (~2–4 h LLM, biggest spend item)

The 80 newly acquired sources have chunks but no rule extraction.

1. List rule-bearing versions: `SELECT sv.id FROM source_versions sv JOIN source_documents sd
   ON sd.id=sv.source_id WHERE sd.source_type IN ('state_planning_policy','dc_policy',
   'local_planning_policy','local_planning_scheme','region_scheme','act') AND NOT EXISTS
   (SELECT 1 FROM clauses c WHERE c.source_version_id=sv.id)` (adjust column names against
   models.py if the join fails — escalate, don't guess).
2. For each id, detached, ONE AT A TIME (spend control):
   `python /app/scripts/wp6_extract.py --source-version <uuid> --report /app/reports/wp6/<uuid>.json`
3. After every 10 documents check spend:
   `SELECT sum((amount_json->>'usd')::float) FROM spend_events WHERE created_at > now() - interval '1 day'`
   — if > $50/day, stop and escalate (column name may differ; check models.py first).
4. After the pool drains run `python /app/scripts/wp6_adjudicate.py --apply --report /app/reports/wp6_adjudication.json`.

Gate: every processed version has clauses; `rules` count increased; report committed.
A doc whose extraction crashes twice → skip, escalate, continue.

## Task 4 — WP6 challenge round for the 506 single-family groups (~1–2 h LLM)

`wp9_pending_adjudicate.py` only covers `pending_review`. The 506 single-model-family
groups sit at `validators_passed` with `metadata_json->>'pending_reason'='single_model_family'`.

1. Confirm OPENAI_API_KEY (or ANTHROPIC) is set in the container env — the first corpus
   run produced single-family groups because pass 3's second family was unavailable.
   If no second family key: STOP, escalate ("need OPENAI_API_KEY in infra/v3 env"), skip task.
2. Write `scripts/wp6_challenge.py`: clone of `wp9_pending_adjudicate.py` but the candidate
   query selects `review_status='validators_passed' AND metadata_json->>'pending_reason'='single_model_family'`,
   and the fresh passes must use a DIFFERENT model family than the votes' `extractor_model`
   (use `family_of()` from `draftcheck.extraction.adjudication`).
3. Same promote/still-pending/reject rules as wp9_pending_adjudicate (2 fresh votes promote
   at 0.85). Detached run, report to `/app/reports/wp6_challenge.json`.

Gate: 0 candidates left with pending_reason='single_model_family' that haven't been
challenged (metadata gets `challenge_done: true` either way).

## Task 5 — WP7 legal graph + conflict sweep (1 day, mostly deterministic)

Per DB_BUILDOUT_AGENT_PLAN WP7, after Tasks 2–4:

1. Exception atoms: `SELECT count(*) FROM rules WHERE rule_type='exception'` and verify each
   has an `exception_to` edge in `legal_edges`. Missing edge → create from the candidate's
   clause context if the quote names the base rule; else `review_items` row.
2. Conflict sweep (pure SQL, write `scripts/wp7_conflict_sweep.py`): for every
   (rule_key, density_code, pathway) with >1 approved rule from DIFFERENT instruments,
   emit a row to `reports/conflict_sweep.json`. Two rules with the same key+applicability
   and different values from the same instrument = extraction bug → `review_items`.
3. Precedence is CODE, not AI: check `src/draftcheck/checks/` for the precedence ruleset;
   if absent, escalate to operator (it's a product decision), continue.

Gate: `reports/conflict_sweep.json` committed; 0 quoteless edges
(`SELECT count(*) FROM legal_edges WHERE quote IS NULL OR quote=''` → 0, else escalate).

## Task 6 — WP8 adversarial rounds (LLM, run only after 2–5 green)

Run exactly as DB_BUILDOUT_AGENT_PLAN WP8. Minimum viable round for a dumb agent:

1. Re-extractor: pick 20 random approved rules, re-extract their clause with a different
   family, compare values. Mismatch → `adversarial_findings` row (`round=1, agent_role='re_extractor', status='open'`).
2. Prosecutor: ask `/api/v1/search/ask` 20 questions derived from approved rules
   ("what is <rule_key> for <density_code>?"), check the answer cites the rule's source and
   matches the value. Mismatch → finding.
3. Defense: for each `open` finding, fix (correct the rule via the normal candidate →
   adjudication path, never direct UPDATE of values) or refute with verbatim quote.
4. Every confirmed finding becomes a golden eval case (`eval_cases` insert, content-hash id).

Gate: 2 consecutive rounds with 0 confirmed findings → `reports/adversarial_closure.json`.

## Task 7 — WP10 freshness + CI (half day, permanent)

1. Cron on the VPS (`/etc/cron.d/draftcheck-freshness`): weekly
   `wp4_acquire.py --limit 50` rerun after re-seeding indexes via
   `scripts/wp3_manifest_seed.py` (changed sha256 ⇒ import_source already creates a new
   version; old rules for superseded versions → set `lifecycle='stale'` — check the actual
   lifecycle column name in models.py first).
2. CI job (`.github/workflows/`): on merge, run against a scratch Postgres the assertions:
   alembic up/down/up; 0 pending manifest (or listed); 0 quoteless edges; eval seeds load;
   `pytest -q` green.

Gate: cron file exists on VPS; CI green on a no-op PR.

---

## Standing rules (unchanged, every task)

- Alembic only. Idempotent jobs only. Every fetch → `source_fetch_log`.
- Outputs advisory, cite or refuse. Never claim final compliance.
- Blocked ≠ stalled: record blocker + one-command unblock, continue, list in final report.
- Commit every report under `reports/`. Push only when no detached job is running.
