# WP-0 execution on prod — council-scope isolation (2026-07-02)

Executed `scripts/wp0_scope_cockburn.py` on the production DB plus root-cause data fixes.
Companion verification: `reports/wp0_scope_verification.json` (verify_beeliar.py, exit 0).

## What was found

- 3,526 approved Cockburn local rules were still `council_scope = NULL` (global) — WP-0
  code had merged (f546677) but never run against prod.
- 80 approved rules carried a stale non-canonical `'Cockburn'` scope; 52 of them came from
  32 Cockburn LPP `source_documents` rows that had `local_government IS NULL` (untagged),
  so the WP-0 join could not see them.
- Doc tagging was inconsistent: Cockburn docs tagged `'Cockburn'` (short name), Melville
  docs tagged `'City of Melville'` (canonical).
- 369,442 parcels carried the legacy `'City of Cockburn (bbox extent)'` LGA string, and the
  `spatial.py` fact-write path copied it into `property_facts` verbatim (4 legacy facts).

## Data fixes applied (prod DB, in order)

1. `wp0_scope_cockburn.py` run 1: reset 28 non-canonical scopes, scoped 3,526 rules.
2. Tagged the 32 untagged `City of Cockburn LPP%` docs `local_government='City of Cockburn'`.
3. Normalised 107 docs tagged `'Cockburn'` → `'City of Cockburn'` (no code matches the
   literal short name; WP-0 joins with ILIKE).
4. Backfilled 369,442 parcels `'City of Cockburn (bbox extent)'` → `'City of Cockburn'`.
5. Backfilled 4 legacy `property_facts` LGA values to canonical.
6. Cleared stale `'Cockburn'` scope on 153 non-approved rules (hygiene; engine reads
   approved only).
7. `wp0_scope_cockburn.py` run 2: reset 52, scoped 902 more (rules from the newly tagged docs).

## Final state

| council_scope        | approved rules |
|----------------------|----------------|
| City of Cockburn     | 4,428          |
| NULL (state/global)  | 3,368          |

## Code hardening (this PR)

- `checks/engine.py::_resolve_council_scope` canonicalises fact- and project-derived scope
  via `canonical_local_government_name` (legacy stored facts can no longer miss the match).
- `domain/address/spatial.py` canonicalises `local_government` at fact-write time (the
  path that produced the bbox-extent facts).

## Gate (verify_beeliar.py, exit 0)

- `1 BLACK SWAN RISE BEELIAR` → resolved parcel 1585770 → R20 → 6 synth facts.
- 118 categories evaluated: 38 numeric checks, 80 advisory rules, all cited.
- `council_scope` resolved to `City of Cockburn` from `property_fact:local_government`.
- Cross-council isolation: a `City of Melville`-scoped project evaluated 118 categories
  with **zero** Cockburn local rules surfaced (`foreign_council_scopes_found: []`).

WP-0 is complete. Second-council work (Melville) is unblocked.
