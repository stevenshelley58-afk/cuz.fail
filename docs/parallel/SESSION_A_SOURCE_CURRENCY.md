# Session A — Source Currency Audit (multi-agent)

Authority: `docs/MASTER_REBUILD_PLAN.md` §8 (governance), `docs/SOURCE_GOVERNANCE.md`,
`docs/DATA_SOURCES.md`. Conventions: `docs/MULTI_AGENT_BUILD_PLAN.md` §5–6.
**Sole output:** `docs/SOURCE_CURRENCY_AUDIT.md`. Read-only on the DB; web allowed. Touch no code.

## Why
With no human review gate, the source library *is* the ground truth. If it holds a **superseded**
regulatory version (e.g. R-Codes as SPP 7.3 rather than the 2024 Planning Code Volume 1), Stage 3
will extract rules from a dead source and every downstream verdict inherits the error. This audit
finds that before extraction runs.

## Goal
A currency matrix of every regulatory source in the library: what version is stored, what the
current authoritative version is, whether they match, and licence/review status. Flag superseded,
stale (>review window), and metadata-only sources that cannot support answers.

## Agents
| Agent | Scope | Task |
|---|---|---|
| **Library Auditor** (worker) | read `draftcheck.db` (legacy) + V3 `sources`/`source_versions` if reachable | Enumerate `source_documents`/`source_versions`/`source_licence_reviews`: title, version, effective_from/to, sha256, licence_status, review_status. Focus: R-Codes, NCC/BCA, bushfire (AS 3959 / SPP 3.7), heritage, council LPS. |
| **Currency Verifier** (worker, parallel) | web (wa.gov.au, abcb.gov.au, legislation.wa.gov.au) | For each source, confirm the **current** authoritative version + effective date + canonical URL. Note the R-Codes move from SPP 7.3 → Planning Code (subsidiary legislation), 2024 Volume 1. |
| **Governance Reviewer** (fresh, read-only) | read both outputs | Cross-check the matrix against §8 rules: no superseded/metadata-only source may support a regulatory answer; every "approved" source has a licence permitting the use. Flag violations. |

Library Auditor and Currency Verifier run concurrently; Reviewer runs after both.

## Method notes
- Legacy data is in `draftcheck.db` (SQLite): `source_documents` (81), `source_versions` (83),
  `source_licence_reviews` (83). The V3 Postgres library is the real target — query it if the app/DB
  is reachable; otherwise audit the SQLite and mark the V3 check as a follow-up.
- Use `WebSearch`/`web_fetch` only for currency confirmation. If a gov page won't fetch, record the
  URL and move on — do not work around fetch restrictions.

## Output: `docs/SOURCE_CURRENCY_AUDIT.md`
A table: `source | stored version | current version | match? | licence | review_status | action`,
plus a prioritised remediation list (which sources must be re-fetched/re-versioned before Stage 3),
and an explicit R-Codes finding (current vs superseded). Cite every currency claim.

## Acceptance gate
Every regulatory source classified match / superseded / stale / metadata-only with a cited current
version; R-Codes verdict explicit; remediation list ordered by Stage-3 impact; no uncited currency
claim.
