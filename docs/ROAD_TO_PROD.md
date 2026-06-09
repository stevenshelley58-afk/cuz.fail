# Road to Prod — Re-baselined Phase Roadmap

Date: 2026-06-09
Status: current map of what's left to ship. Re-baselines `docs/MASTER_REBUILD_PLAN.md` §9 for two
decisions made 2026-06-09: the pipeline is **fully AI** (no human reviewer/approval/signoff gate),
and the two-stack/two-DB consolidation (`docs/CONSOLIDATION_PLAN.md`) is landing first. Product
substance (deterministic engine, citations, advisory-not-certification output) is unchanged.

---

## Where we actually are (build status vs. data status)

Two separate questions per phase: is the **code** written, and is the **data** loaded? They
diverge a lot — most domains have code but empty Postgres tables.

| Phase | Code in `src/draftcheck` | Data in prod DB | Verdict |
|---|---|---|---|
| 0 — Skeleton/VPS/CI/auth | built (`api/`, `domain/identity`, CI, compose) | n/a | **Done** (Vercel cutover finishing via consolidation) |
| 1 — Source library + search + substrate | built (`domain/sources/*` 4.6k LOC, `ai/substrate.py`) | **populated** (81 docs, 28k clauses, 31k chunks/embeddings) | **Mostly done** — verify search + cite-or-refuse |
| 2 — Projects/address/spatial | partial (`domain/address/spatial.py`, `api/address.py`) | **empty** (0 parcels, 0 address_points, 0 projects) | Code exists, never loaded/wired |
| 3 — Rule extraction | partial (`extraction/{validators,vocabulary,normalize}`) | **empty** (0 rules/resolved_rules) | Code exists, never run at scale |
| 4 — Documents/drawing facts | partial (`domain/documents/parsing.py`) | **empty** (0 document_facts) | Code exists, parsers thin |
| 5 — Compliance engine → M1 | **not built** (`checks/__init__.py` is empty) | empty | **Critical gap — the path to prod** |
| 6 — Hermes autonomy | **not built** (`agent/__init__.py` is empty) | empty | Post-prod |
| 7 — RFI/exports/~~signoffs~~ | not built | empty | Signoffs removed; RFI/exports post-M1 |
| 8 — Self-learning | not built | empty | Post-prod |

**Headline:** Phase 1 is real and populated. Phases 2–4 are "code without data." Phase 5 (the
deterministic compliance engine) is the genuine missing piece — and it's the one that makes the
product a product. **Minimum shippable prod = the Phase 5 M1 vertical slice working end-to-end for
real users on one council.** See `docs/M1_GOLDEN_FIXTURE.md`.

---

## What the all-AI decision changes

The master plan's human gates are replaced by automated gates. Specifically:

| Master plan said | Re-baselined (all-AI) |
|---|---|
| Phase 3 exit: "humans promote" rules | Validators + eval-case gate promote; `lifecycle_status` driven by the automated pipeline, not a person |
| Phase 5 exit: "conflicts → human review" | Conflicts → `needs_more_info` / `unsupported` status surfaced to the end user; no reviewer queue |
| Phase 7: "export blocked without signoff" | Signoff gate removed; export carries a manifest + assumptions/limitations + the advisory disclaimer |
| `users.role ∈ {owner, reviewer}`, `signoffs` table, `approved_by_user_id` | Removed (see consolidation Phase B) |

**Retained (not a human gate):** every output stays cited and labelled advisory / **not a final
certification** (`likely_pass | likely_fail | missing_info | unsupported`). This is the one
governance item kept by default — it's output honesty, not human-in-the-loop. Flagged as
overridable in `CONSOLIDATION_PLAN.md` §3.

---

## The road to prod (sequenced)

Stages are gated. Each can be worked on once its predecessor's gate is green. Stages 2–3 prep
(data sourcing, fixture design, eval drafting) is non-conflicting and can start now while the
consolidation branch runs.

### Stage 0 — Consolidation lands *(in progress, Claude Code)*
`CONSOLIDATION_PLAN.md` A–E: one stack, one DB, human-review removed, legacy deleted, sanity green.
**Gate:** single Postgres + single alembic chain; forbidden-pattern grep clean; prod health green.

### Stage 1 — Lock the first-slice scope
Pick the fixture council + address + the 5 Tier-1 deemed-to-comply checks (done in
`M1_GOLDEN_FIXTURE.md`). Confirm the approved R-Codes Volume 1 (2024) source version is in the
library with licence/review status set. **Gate:** fixture scope signed; source version present and
citable.

### Stage 2 — Phase 2 for one council (data + wiring)
Load spatial datasets **for the fixture council only**, behind the SLIP cadastre licence gate:
parcels (Landgate cadastre via SLIP), `address_points` (G-NAF), planning overlays, LGA boundary.
Wire `domain/address` resolver end-to-end; create the golden fixture project. **Gate:** the fixture
address resolves → parcel/council/zone/overlays with provenance, or `missing_info`; geocode is never
treated as legal proof.

### Stage 3 — Phase 3 rule extraction (all-AI) for the 5 checks
Run the extraction pipeline over R-Codes Volume 1 to produce `rules`/`resolved_rules` for the five
Tier-1 standards. Automated validators (quote-anchoring, normative-language, no-orphan, unit
normalization) + eval-case gate replace human promotion; every extraction traced
(`job_traces`, skill version, prompt hash). **Gate:** each of the 5 rules has quote + clause +
source version + passing validators; no rule emits a verdict without these.

### Stage 4 — Phase 4 drawing facts for the fixture drawing
Parse the fixture site plan; extract dimensions as evidence-linked `document_facts`; enforce the
promotion contract (fact → measurement only with unit + label + evidence link + parser run +
confidence + check_key). Raster scale never inferred without calibration. **Gate:** the fixture
drawing yields the measurements the 5 checks need, each evidence-linked; ambiguous facts stay
`needs_more_info`.

### Stage 5 — Phase 5 compliance engine + M1 slice *(the prod milestone)*
Build `src/draftcheck/checks/`: `check_runs`/`check_results`, applicability + precedence resolvers,
the 5 deemed-to-comply calculators, decision traces; matrix UI + issue cards + evidence drawer in
`web/`. Run the M1 vertical slice end-to-end. **Gate (M1):** pass/fail impossible without
rule + measurement + citation + trace; the fixture runs clean end-to-end; the golden fixture becomes
the permanent canary.

### Stage 6 — Launch hardening
Exports (manifest + assumptions/limitations + disclaimer, no signoff); minimal ops dashboard
(freshness, failures, spend, backups, eval trend); weekly canary on the fixture; spend caps + alerts
verified. **Gate:** export produces a defensible, cited artifact; canary green; backups + alerts live.

### Post-prod (not blocking launch)
- **Phase 6 — Hermes autonomy:** agent loop that proposes candidates/drafts only, eval-gated.
- **Phase 8 — Self-learning:** dispositions → labelled examples → eval-gated skill improvement.
- **Breadth:** extend from the one fixture council to additional LGAs and check tiers.

---

## Critical path & risks

- **Critical path:** Stage 0 → 2 → 3 → 4 → 5. Stage 5 (the engine) is the long pole and is
  currently a 0-line file. Stages 2–4 are mostly "run the code that exists + load data + add the
  automated gates that replaced human ones."
- **Licence gate (high):** SLIP public cadastre is personal-use-licensed; commercial use must be
  confirmed with Landgate before launch (`MASTER_REBUILD_PLAN.md` §8.2). Blocks Stage 2 going wide.
- **Source currency (high):** R-Codes moved from SPP 7.3 to a Planning Code (subsidiary legislation)
  with a 2024 Volume 1 — confirm the library holds that exact version, not the superseded SPP.
- **All-AI accuracy (high):** with no human gate, the eval-case suite *is* the safety net. Stage 3
  must not promote a rule that fails validators; Stage 5 must refuse rather than guess.
- **Scope discipline:** do Stages 2–5 for ONE council/address/drawing first. Breadth is post-prod.

---

## Companion docs
- `docs/CONSOLIDATION_PLAN.md` — Stage 0 execution (cleanup, single DB, human-review removal).
- `docs/M1_GOLDEN_FIXTURE.md` — Stage 1 scope: the fixture council/address + 5 checks (prep).
