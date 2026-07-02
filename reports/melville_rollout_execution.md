# City of Melville rollout — execution report (2026-07-02)

Second council through the COUNCIL_ROLLOUT_PLAN recipe. Result: **844 approved,
cited, council-scoped rules; faithfulness 0.987 (3-judge); canary green with
zero cross-council leakage.** Companion artifacts: `reports/melville_canary_run.json`,
`evals/seeds/melville_canary.json`, `reports/wp0_scope_execution.md` (prerequisite).

## Where the prior attempt stalled

The 2026-06-16 claim ingested 8 documents (LPS6 scheme text + 7 LPPs), chunked
them, and stopped — 0 clauses, 0 candidates, and the doc set missed the
rule-heaviest instruments (LPP 3.1 Residential Development, LPP 1.9 Heights,
LPP 2.1 Non-Residential, the strategy, the Canning Bridge ACP).

## What ran (in order)

1. **Corpus completion** — discovered the council's current 27-policy LPP list,
   seeded 22 manifest rows (`scripts/seed_melville_manifest.py`), acquired 21
   (LPP 1.20 blocked: every URL variant 404s; unblock note in
   `target_manifest.notes`; the acquired CBACP carries the same M10/M15
   provisions). Final corpus: 29 tagged Melville docs.
2. **Bug fixes en route** (commit 6b80157): `wp6_decode.py` numeric-unit call
   (every numeric rule crashed — pilot showed 0 numeric rules, post-fix 18/25);
   `wp4_acquire.py` now derives `local_government` from the issuing authority
   (root cause of WP-0's untagged-docs mess).
3. **Structure pass** — 29 versions segmented into clauses (deterministic).
4. **Decode** — gpt-4o-mini over rule_bearing+procedural clauses, piloted
   25-first per standing rule: 1,493 Melville candidates.
5. **Promote + immediate scope** — 1,520 promoted (incl. 27 state/Cockburn
   stragglers), Melville rules scoped in the same step to avoid a global-leak
   window (`scripts/wp_scope_council.py`, new `--council`-generic scoper).
6. **Correct-don't-delete** — gpt-4o, piloted then applied: 1,520 processed,
   865 kept (406 rewritten to match their quotes), 655 rejected, 0 errors.
7. **Real-rule filter** — pilot (`--scope approved --redo --council 'City of
   Melville'`, new council filter, commit 5252506) kept 25/25 → the correction
   pass had already converged; full redo skipped (decision logged here).
8. **Noise sweep** — SQL: 11 broken-quote rejects. Final: **844 approved**
   (282 boolean, 234 numeric, 184 qualitative, 77 conditional, 67 categorical).
9. **Faithfulness audit** — stratified 75-rule sample
   (`scripts/export_audit_sample.py`), 3 independent claude-haiku-4-5 judges,
   majority vote: **74/75 faithful (0.987 ≥ 0.90 gate)**. The one confirmed
   failure (modality escalation "will need to" → "must") was corrected in
   place (`metadata_json.audit_fix`). One single-judge flag did not survive
   majority.
10. **Canary** — `verify_beeliar.py --address "27 DUNVEGAN ROAD APPLECROSS"
    --other-council "City of Cockburn"`, exit 0: parcel 1222862 → R15 → 6
    facts → 118 categories (38 numeric, 80 advisory, all cited); surfaced
    rules split 55 Melville-scoped + 42 global; a Cockburn-scoped probe
    project surfaced **zero** Melville rules.

## Prod rule DB after this run

| council_scope       | approved rules |
|---------------------|----------------|
| City of Cockburn    | 4,438          |
| City of Melville    | 844            |
| NULL (state/global) | 3,385          |

## Cost

- gpt-4o-mini decode + gpt-4o correction (OpenAI key): ≈ $6–8.
- Claude: 3 Haiku judge agents (~170k subagent tokens total) + one stalled
  Haiku babysitter agent. No frontier-model batch spend.

## Blocked items (one-command unblocks)

- **LPP 1.20**: find the working PDF link on the council's LPP page, then
  `UPDATE target_manifest SET canonical_url='<url>', status='pending' WHERE
  instrument_name LIKE '%LPP 1.20%'` and re-run `wp4_acquire.py`.
