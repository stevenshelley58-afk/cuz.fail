# Tier-1 council rollout — execution report (2026-07-02)

Ran the per-council recipe (COUNCIL_ROLLOUT_PLAN) for the four remaining Tier-1
councils in one orchestrated session: Haiku subagents for discovery, babysitting
and judging; gpt-4o-mini decode; gpt-4o correction; deterministic everything else.

## Result

| Council | Instruments | Approved scoped rules | Audit (3 Haiku judges + operator) | Canary |
|---|---|---|---|---|
| Town of East Fremantle | 13/13 | **697** | 0.973 (1 fixed, 2 judge flags overturned) | ✅ R12, no leakage |
| City of Kwinana | 17/19 | **759** | 0.987 (1 fixed) | ✅ R12.5/20, no leakage |
| City of Fremantle | 46/52 | **1,522** | 0.987 (1 numeric fix via operator check) | ✅ R20/25, no leakage |
| City of Rockingham | 38/40 acquired | **blocked mid-decode** | — | — |

Prod rule DB after this run: Cockburn 4,433 · Fremantle 1,522 · Melville 844 ·
Kwinana 759 · East Fremantle 697 · state/global 3,373. Cross-council isolation
verified in every canary, both directions.

## BLOCKED: Rockingham (one-command unblock)

The **OpenAI account quota exhausted** mid-run (both gpt-4o and gpt-4o-mini
return 429 "exceeded your current quota"). Rockingham died mid-decode; its
partially-promoted rules (1,131) plus 12 Kwinana mop-up rules were **parked**
(`lifecycle_status='rejected'`, `metadata_json.parked='awaiting_correction_openai_quota'`)
so nothing uncorrected or unscoped is live. The correction pass's `combined`
scope automatically recovers parked rules it keeps.

**Unblock:** add credit / raise the limit at platform.openai.com → Billing, then:

    ssh draftcheck 'docker exec -d draftcheck-wa-v3-api-1 sh -c "\
      python /app/scripts/run_council_pipeline.py --council \"City of Rockingham\" && \
      python /app/scripts/wp6_correct.py --apply --workers 16 --model gpt-4o --council \"City of Rockingham\" && \
      python /app/scripts/wp6_correct.py --apply --workers 8 --model gpt-4o --council \"City of Kwinana\" \
      > /app/reports/rockingham_resume.log 2>&1"'

then noise sweep + audit + canary per the recipe (est. remaining spend ≈ $5).

## Structural fixes shipped (benefit every council)

1. **Parcel dedupe** — overlapping bbox imports had loaded the same SLIP parcels
   repeatedly (111,823 duplicate rows); `planning_for_parcel`'s
   cadastre_id+limit(1) lookup could pick a stale copy. Deduped keeping newest.
2. **R-code regex** (`synth_facts.py`, commit 51d8197) — the old pattern only
   matched activity-centre codes; plain R20/R12.5 worked only inside the area
   stamped by a never-committed script. Found by the Kwinana canary
   (R12.5/20 → None); new pattern covers plain, RR, AC and split codes.
3. **Spatial dataset refresh approvals** — new 2026-07-02 SLIP versions were
   `pending_review` (resolution ignored them); approved with audit_events
   extending the operator's 2026-06-15 open-data decision.
4. Generic tooling: `seed_council_manifest.py` (discovery JSON → manifest),
   `run_council_pipeline.py` (structure→decode→promote→scope, one command).

## Corpus blockers recorded in target_manifest.notes

- Rockingham: 3.2.1/3.2.6 out_of_scope (superseded by the Strategic Centre PSP).
- Kwinana: LPP 5 page 404s; LPP 12 out_of_scope (revoked).
- Fremantle: 4 LDPs + 2 structure plans are 1-page drawings (guard-blocked,
  low rule value); LPP DGF5 is an unparseable scan; LPP DGF9 low-text.

## Audit-integrity notes

Haiku judge panels are effective but need the operator loop: across 4 panels,
2 majority flags were false positives (verdicts contradicted their own reasons —
overturned), and 1 real numeric error (parking ratio doubled) was caught only as
a single-judge flag that operator spot-checking confirmed. Rule adopted: always
verify single-judge NUMERIC flags manually; require judge reasons to justify
verdicts (prompt updated).

## Cost (this session)

- OpenAI: decode ~6,600 clauses (mini) + correction ~5,400 rules (gpt-4o) ≈ $25–35
  before quota exhaustion.
- Claude: ~15 Haiku agents (discovery ×5, judges ×9, babysitter ×1); main loop
  orchestration only.
