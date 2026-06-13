# Cockburn Sonnet-third-family WP6 extraction slices

Date: 2026-06-13. Authority: docs/GO_LIVE_EXECUTION_PLAN.md §B5 + DB_BUILDOUT_AGENT_PLAN.md WP6.

## Why

The WP6 family-aware adjudicator (src/draftcheck/extraction/adjudication.py) refuses
to promote rule candidates unless at least two distinct model families produced a
validator-passing atom with the same deterministic core. Today's families on the VPS
are minimax (rate-limited / 402'd) and openai (works). For 31 single_model_family
core groups the only working unblocking option is to add a third family.

Anthropic models (via the Claude Code session subagent path, model='sonnet') become
"anthropic:claude-sonnet-4-6" — family_of() returns "anthropic", a distinct family.

## Files

- `clauses.jsonl` — every Cockburn / R-Codes-V1 / SPP 7.3 / SPP 3.7 rule-bearing clause
  that does NOT yet have an anthropic-family candidate (1115 rows).
- `pilot_args.json`, `pilot_extractions.json` — first 70-clause pilot (LPP 1.12 noise,
  LPP 3.5 alfresco, sample of R-Codes V1). Outcome under the OLD closed vocab: 3 atoms —
  the then-closed 14-key vocab in src/draftcheck/extraction/vocabulary.py rejected
  noise/alfresco/signage rules. (Superseded 2026-06-14 — the closed-vocab cap was lifted;
  those categories are now extracted freely and canonicalised by clustering. See
  docs/OPEN_VOCAB_REBUILD_PLAN.md. The 3-atom count is retained here only as a historical
  record of that closed-vocab run.)
- `rcodes50_args.json`, `rcodes50_extractions.json` — focused 50-clause R-Codes V1 run.
  Outcome under the OLD closed vocab: 12 atoms (4 clauses produced atoms), confirming the
  recall is real but — at the time — vocabulary-capped. (Superseded 2026-06-14 — recall is
  no longer capped by a fixed key set; un-hinted keys now pass and are clustered.)
- `slice1_*.{json,sql}` — combined pilot + rcodes50 (120 clauses, 15 atoms,
  9 validators_passed). The SQL is idempotent: PK = uuid5 of
  (group, atom_index, signature), so re-runs upsert in place.
- `single_family_clauses.jsonl` — the 37 clauses where minimax OR openai voted alone
  on a core. Targeted Sonnet extraction on these is the highest-yield slice for
  promoting stuck cores via cross-family agreement.

## How to add another slice

```bash
# 1. Pull a slice from VPS (any selector you like — examples in single_family.sql).
# 2. Build a workflow script:
python .claude/.../wp6-sonnet-build-rcodes50.py <args.json> <out.js>

# 3. Run via Workflow tool (from inside Claude Code):
#    Workflow({scriptPath: "...<out.js>"})

# 4. Save and post-process:
python scripts/wp6_sonnet_postprocess.py \
  --extractions data/extraction/cockburn/<slice>_extractions.json \
  --batches    data/extraction/cockburn/<slice>_args.json \
  --validated-out data/extraction/cockburn/<slice>_validated.json \
  --sql-out       data/extraction/cockburn/<slice>_candidates.sql

# 5. Push to VPS:
scp data/extraction/cockburn/<slice>_candidates.sql draftcheck:/tmp/
ssh draftcheck "sudo docker compose -f /srv/draftcheck/app/infra/v3/compose.yml \
  cp /tmp/<slice>_candidates.sql db:/tmp/x.sql && \
  sudo docker compose -f /srv/draftcheck/app/infra/v3/compose.yml \
  exec -T db psql -U draftcheck -d draftcheck -f /tmp/x.sql"

# 6. Re-adjudicate:
ssh draftcheck "cd /srv/draftcheck/app/infra/v3 && \
  sudo docker compose exec -T api python /app/scripts/wp6_adjudicate.py --apply \
  --report /app/reports/wp6_adjudication.json"
```

## Cap / honest read (superseded 2026-06-14 — cap lifted, see open-vocab note below)

Historical record (closed-vocab era, accurate as of 2026-06-13): the 14-key RULE_KEYS
vocabulary in src/draftcheck/extraction/vocabulary.py was the ceiling. Pilot showed only
4 of 50 R-Codes V1 clauses produced in-vocab atoms; 67 of 70 LPP clauses produced nothing
(noise / alfresco / signage rules were outside the vocabulary by design). Under that closed
vocab, even a perfect 100% Sonnet pass over the 1115 Cockburn slice would have emitted only
~250-300 atoms because most clauses don't carry a quantitative rule that fit the 14 keys.
These counts and observations are kept as a record of that closed run.

### Update 2026-06-14 — the cap is gone (open-vocab pipeline)

The closed-vocab ceiling described above no longer applies. Per the operator decision
(Steven, 2026-06-14; docs/OPEN_VOCAB_REBUILD_PLAN.md, subordinate to
docs/MASTER_REBUILD_PLAN.md):

- The former closed set is renamed `RULE_KEY_HINTS` in
  src/draftcheck/extraction/vocabulary.py and is now only a SOFT signal (telemetry /
  confidence weighting via `is_hinted_key()`), NOT a hard gate. The LLM proposes any
  snake_case rule_key it sees; nothing is dropped for being "outside the vocab".
- The previously-dropped categories (noise, alfresco, signage, plus bushfire, heritage,
  parking ratios, lot width / depth, fence height, retaining wall, secondary dwelling area,
  etc.) are now extracted and canonicalised — not gated out. The "vocabulary expansion"
  this section once called for is exactly what open-vocab delivers, without a fixed key list.
- Universal structural validators (quote-anchor, no-orphan-numbers, normative-language,
  operator/unit canonical, value-finite, unit-category sanity) catch garbage regardless of
  rule_key. The old range_prior check is demoted to a soft confidence score for un-hinted keys.
- Post-hoc clustering canonicalises the raw rule_key strings: scripts/wp6_cluster_keys.py
  groups variants and scripts/wp6_apply_clustering.py bulk-fills the `canonical_rule_key`
  column (String(160), nullable, indexed) added by migration 0018_rule_canonical_keys on both
  the rules and rule_candidates tables. Open-vocab candidates carry
  `metadata_json.open_vocab = true`.

So the ~250-300 atom estimate above was a property of the closed vocab, not of the data or
the extractor; with open-vocab extraction the Cockburn slice is expected to yield materially
more. (The project_vocabulary_gap memory note records why the old plateau existed; it is
history, not the current ceiling.)
