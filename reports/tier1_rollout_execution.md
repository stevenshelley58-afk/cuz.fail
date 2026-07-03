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

**Unblock:** add credit / raise the limit at platform.openai.com → Billing.

## CORPUS GAP addendum (2026-07-02, post-review)

The operator correctly flagged that per-council rule counts were implausibly low
vs Cockburn. Root cause: rules scale with corpus size and the Tier-1 discovery
pass under-collected the structure-plan/LDP layer (Cockburn has 33 SPs ingested;
Kwinana had 1 despite being a growth corridor with dozens). A second discovery
sweep seeded **199 additional instruments** (Kwinana 130, Rockingham 61,
Melville 6, Fremantle 2 — East Fremantle confirmed complete). A
corpus-completeness gate was added to COUNCIL_ROLLOUT_PLAN §1.2a.

**Full resume sequence after OpenAI top-up** (acquire also needs OpenAI for
embeddings; run steps sequentially, each is idempotent):

    ssh draftcheck 'docker exec -d draftcheck-wa-v3-api-1 sh -c "\
      mkdir -p /app/reports && \
      python /app/scripts/wp4_acquire.py --limit 210 --report /app/reports/wp4_sp_wave.json && \
      for c in \"City of Kwinana\" \"City of Rockingham\" \"City of Melville\" \"City of Fremantle\"; do \
        python /app/scripts/run_council_pipeline.py --council \"$c\"; \
        python /app/scripts/wp6_correct.py --apply --workers 16 --model gpt-4o --council \"$c\"; \
      done > /app/reports/sp_wave_resume.log 2>&1"'

then per council: noise sweep + fresh audit sample + 3-judge audit + canary
refresh per the recipe. Estimated spend: ~205 docs ≈ $25–40 (decode + correct
+ embeddings).

## Correction stage migrated to Claude subagents (2026-07-02)

The gpt-4o correction stage (~75% of OpenAI spend) now runs on the operator's
Claude subscription: `export_uncorrected.py` batches → Haiku corrector agents
(same calibrated correct-don't-delete criteria, distinct model tag
`claude:haiku-4.5:correct`) → `apply_corrections.py` with a NUMERAL GATE (any
corrected claim asserting a number absent from the verbatim quote is withheld).

Executed on the 1,143 quota-parked rules in 21 batches: **581 kept/recovered,
554 rejected, gate blocked 8 invented-number claims** (5 fixed on strict redo,
2 rejected as unfixable, 1 operator-fixed in pilot). Rockingham's policy layer
went live from this: 686 approved scoped rules after sweep. Pilot + operator
review preceded the run per COUNCIL_ROLLOUT_PLAN §4.2; the audit stage
(3 judges + operator numeric checks) still applies before any council is
marked done. Revised OpenAI dependency: embeddings + gpt-4o-mini decode only
(~$10 for the remaining Tier-1 queue).

## Exa completeness cross-check (2026-07-02, operator-funded EXA_API_KEY)

`scripts/wp_discover_docs.py` ran an 8-query semantic sweep per council
(council domain + wa.gov.au) for all 5 Tier-1 councils plus Cockburn —
~50 searches, < $0.50. Haiku reconcilers classified 285 candidate URLs against
the manifest: **only 6 genuinely new instruments** (Kwinana Commercial & ACP
Strategy 2024; Fremantle South Beach Village SP, LPP 3.1.3, LPP 3.1.5,
LPP DGN3; Cockburn Coast District SP) — all seeded. Everything else was a
duplicate under a different URL or a non-instrument. Conclusion: after the
199-doc SP wave, the Tier-1 corpus matches the public registers. Evidence:
`reports/exa_discovery/`. Exa also retrieves full text for viewer pages our
fetcher cannot parse (e.g. Melville LPP 1.20) — candidate future unblock path.

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

## Final Tier-1 closeout (2026-07-03)

All Tier-1 council faithfulness gates are closed. Live scoped counts were queried from the
production database after the final rejects.

| Council | Approved scoped rules | Rejected scoped rows | Final audited rate | Canary seed |
|---|---:|---:|---:|---|
| City of Cockburn | 4,543 | 1,276 | 0.933 | `beeliar_canary.json` |
| City of Melville | 1,105 | 834 | 1.00 | `melville_canary.json` |
| City of Fremantle | 1,751 | 1,251 | 0.933 | `fremantle_canary.json` |
| Town of East Fremantle | 697 | 515 | 0.97 | `east_fremantle_canary.json` |
| City of Kwinana | 3,271 | 2,479 | 0.987 | `kwinana_canary.json` |
| City of Rockingham | 1,792 | 1,313 | 0.987 | `rockingham_canary.json` |

Final audit actions applied with `metadata_json.audit_fix =
tier1_final_3judge_2026-07-03`:

| Council | Rule | Action |
|---|---|---|
| City of Fremantle | `68540c1f-d6b6-59a9-9ea3-d3852d1aca64` | Rejected: descriptive freeboard data, not a control. |
| City of Fremantle | `3e4fa8f3-71b5-50ff-8cfe-a5eb02c24746` | Rejected: definition presented as a development control. |
| City of Fremantle | `f861ee7b-5ea7-566e-af05-551bd90943a2` | Rejected: scope/applicability statement, not a rule. |
| City of Fremantle | `3c7ef679-513a-50b1-97d9-9b7593b4e2eb` | Fixed in place: modality `advisory`; technical reports may be required for structure plan and large-scale subdivision applications. |
| City of Fremantle | `4c2bce53-be2c-5939-b09e-e6d58203070a` | Fixed in place: modality `advisory`; retained/enhanced heritage features framed as an assessment criterion. |
| City of Cockburn | `91d38b5a-8e04-569e-9d42-eb50ed02cb3e` | Fixed in place: density wording mirrors R20 cap and Council's R40 permission pathway north of Forrest Road. |
| City of Cockburn | `975494ec-049e-59a3-ab22-e946c18a23be` | Rejected: descriptive cul-de-sac position data, not a control. |
| City of Cockburn | `0113b064-e8f9-51bf-96d0-6e43ff92c9c2` | Rejected: scope/vision statement converted into a development control. |
| City of Cockburn | `fc47bbaa-09c2-51f2-a95b-fc0a78027a1f` | Fixed in place: modality `advisory`; bushfire measures wording now mirrors "will need to be implemented". |
| City of Cockburn | `aa783563-da5f-5996-898e-ec649775f4f2` | Fixed in place: modality `advisory`; firebreak maintenance wording now mirrors "will maintain ... or alternatively provide a bond". |
| City of Cockburn | `8562268d-f170-5d56-bf15-a4a8305b0d0c` | Fixed in place: modality `advisory`; staged density wording now mirrors "may be achieved". |
| City of Kwinana | `2241f295-c8ec-5b4d-ad10-ae42bc8c8b5d` | Previously applied fix: modality/wording corrected to recommended/preferably storage near retained trees. |
| City of Rockingham | `f6f56c7d-8df5-537c-9995-96e53c75bcd1` | Previously applied reject: plan-phase recommendation was upgraded and over-specified. |
| City of Rockingham | `a9e9d5fb-b98d-568a-9863-79abcd46582a` | Previously applied reject: context-free fragment invented battle-axe scope. |
| City of Rockingham | `71127f50-e4d4-506a-80f2-d0fabc4a3c50` | Previously applied reject: claim invented cash-in-lieu exemption consequence absent from quote. |

Cockburn's prior sampler shortfall is fixed in `scripts/export_audit_sample.py`: `NULL`
`check_type` strata now use NULL-safe equality, and the final Cockburn export returned
75/75 rows from a 4,545-row approved population before the two sample rejects.

Remaining non-gating backlog:

- 23 blocked documents remain outside the Tier-1 gate: Kwinana 12 scan-only documents,
  Melville 1 dead URL, and Rockingham 10 amendment/navigation-only documents.
- Run embedding backfill before Tier 2 expansion.
- Add OCR fallback for scan-only planning instruments.
