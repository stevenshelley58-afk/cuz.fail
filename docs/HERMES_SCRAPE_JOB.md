# Hermes Scrape Job

Use this with the VPS Hermes agent after setting `HERMES_BASE_URL` and `HERMES_API_KEY`.

Objective: build a lawful source inventory and raw document corpus for DraftCheck WA.

Constraints:

- Do not answer compliance questions.
- Do not bypass paywalls, login gates, captchas, robots.txt, or access controls.
- Do not scrape Australian Standards full text.
- Store Standards Australia references as public metadata and access notes only.
- Prefer official government, council, legislation, DFES, DPLH, ABCB, and council websites.
- Record licence/access notes for every source.
- Use parallel workers with per-domain politeness.
- Save partial results continuously.

Required outputs:

- `source_inventory.jsonl`
- `fetch_log.jsonl`
- `errors.jsonl`
- `raw/`
- `parsed/`
- `reports/source_summary.md`
- `reports/licensing_risks.md`
- `reports/missing_sources.md`
- `reports/council_coverage_matrix.csv`

Each inventory row should include title, authority, jurisdiction, local government, source type, canonical URL, retrieved URL, content type, raw path, parsed path, SHA-256, published/effective date, retrieved date, licence notes, robots status, access type, parse status, and notes.

## Corpus Import

Import Hermes `source_inventory.jsonl` through either:

- `POST /v1/sources/hermes-corpus/import`
- `python scripts/import_hermes_corpus.py --inventory path/to/source_inventory.jsonl`

The importer treats the inventory as a provenance ledger. Rows with lawful public/open parsed PDF/text content are imported as source documents, stored as content-addressed source versions, chunked for retrieval, and made citable through approved source version/chunk identifiers. Regulatory answers may use that text only when the stored source version supports the answer.

Rows marked blocked, paid, login-gated, captcha-gated, robots-denied, unknown-access, restricted-licence, or otherwise not lawfully accessible are skipped rather than fetched or stored. Rows without usable parsed public text may be imported only as metadata where that is useful for source governance; metadata-only records are not chunked for retrieval. Standards Australia material is always metadata-only: store public metadata, access notes, licence notes, and source references, but do not store paid Australian Standards full text.

For disk imports, pass the corpus root that contains `raw/`, `parsed/`, and `source_inventory.jsonl`. Row paths are resolved under that root; absolute paths or `..` traversal outside the corpus root are rejected.

Import reports should list imported rows, skipped rows with reasons, metadata-only rows, source versions created or reused by SHA-256, suspected superseded sources, licensing risks, and manual review items.

Priority source groups:

- WA R-Codes and explanatory material.
- WA planning, legislation, PlanWA, Building and Energy, DFES bushfire material.
- NCC/ABCB official public access pages where permitted.
- Perth metro council schemes, policies, local development plans, checklists, and forms.

Final report should list collected source counts, failed URLs, blocked/paywalled sources, suspected superseded documents, licensing risks, and manual checks.
