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
  LPP 3.5 alfresco, sample of R-Codes V1). Outcome: 3 atoms — the closed 14-key vocab
  in src/draftcheck/extraction/vocabulary.py rejected noise/alfresco/signage rules.
- `rcodes50_args.json`, `rcodes50_extractions.json` — focused 50-clause R-Codes V1 run.
  Outcome: 12 atoms (4 clauses produced atoms), confirming the recall is real but
  vocabulary-capped.
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

## Cap / honest read

The 14-key RULE_KEYS vocabulary in src/draftcheck/extraction/vocabulary.py is the
ceiling. Pilot showed only 4 of 50 R-Codes V1 clauses produce in-vocab atoms;
67 of 70 LPP clauses produce nothing (noise / alfresco / signage rules are outside
the vocabulary by design). Even a perfect 100% Sonnet pass over the 1115 Cockburn
slice would emit only ~250-300 atoms because most clauses don't carry a quantitative
rule that fits the 14 keys. Lifting the ceiling needs vocabulary expansion (parking
ratios, lot width / depth, fence height, retaining wall, secondary dwelling area,
etc.) — see project_vocabulary_gap memory note.
