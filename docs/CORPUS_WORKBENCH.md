# WA Planning Corpus Workbench

End-to-end pipeline that builds the production source library: acquire every
planning instrument in `data/manifest.csv`, extract + analyze it, then ingest
it into the V3 source tables with the cite-or-refuse approval gate applied.

Built 2026-06-10. State: **180 manifest rows — 169 extracted, 3 metadata-only
(NCC, registration-walled), 2 blocked (broken council asset / historic policy
with no official source), 5 out-of-scope (water SPPs superseded by SPP 2.9,
recorded with aliases pointing at SPP-007), 1 remaining = none pending.**

## Layout

```
data/manifest.csv               instrument register (single source of truth)
data/instrument_aliases.json    citation alias -> manifest id map
corpus/docs/{id}/source.pdf     raw documents (gitignored; meta.json committed)
corpus/docs/{id}/meta.json      fetch provenance: url, final_url, sha256, http_status
corpus/extracted/{id}/          full_text.txt, tables.json, summary.json (committed)
corpus/analysis/{id}/           agent-written analysis.json: verified title/version,
                                numeric standards, cross references, quality flags
reports/                        acquisition/extraction/ingestion/citation reports
```

## Pipeline (uses .venv-corpus: pdfplumber, httpx, playwright, bs4)

```
python scripts/build_manifest.py        # seed + discovery crawls (idempotent)
python scripts/joondalup_lpps.py        # playwright crawl of Joondalup LPPs
python scripts/pipeline.py              # STREAMING acquire+extract: async download
                                        # workers feed a process-pool of extractors,
                                        # so extraction runs while downloads continue
python scripts/verify_urls.py           # gap checks (blank/draft/failed URLs)
python scripts/check_citations.py       # citation closure vs aliases+manifest
```

`pipeline.py` is resumable: every state change is written to the manifest
atomically, failed rows stay `pending` with the error in `notes`, dead URLs
(404/410) become `blocked`. Re-running only processes unfinished rows.

## DB build (uses .venv: the app environment)

```
# local validation (SQLite, hash-stub embeddings):
.venv/Scripts/python scripts/ingest_corpus.py --local-validate --approve

# production (VPS):
export DATABASE_URL=postgresql+psycopg://...   # from /srv/draftcheck env
export OPENAI_API_KEY=...                      # real embeddings at import
python scripts/ingest_corpus.py --approve
```

`ingest_corpus.py` calls `SqlAlchemySourceLibrary.import_source` per manifest
row (chunking + citations + embeddings are done by the store), carrying the
agent analysis and fetch provenance in `version_metadata`. With `--approve`
an automated validator gate promotes versions to `review_status=approved` +
`licence_status=verified_open` (citable) only when:

  1. the verification fleet confirmed it is the right document
     (`reports/verification_results.json`), and
  2. extracted text >= 400 chars, and
  3. no fatal quality flags from analysis.

Everything else stays `pending_review` — the retrieval layer refuses to cite it.

Embeddings: without `OPENAI_API_KEY` the store falls back to a hash stub
(keyword/FTS search still works; vector search is not meaningful). Unblock on
the VPS with: `OPENAI_API_KEY=... python -m draftcheck.cli re-embed`.

## Known corpus gaps (documented, not silent)

- `reports/citation_gaps.json` — residual cited-but-absent instruments:
  withdrawn planning bulletins (14/18/19/41/61/64/67/69/83/92/94), revoked
  council LPPs, historic Town Planning Schemes. All historical; no official
  source exists on wa.gov.au.
- MEL-LPP-016 (Melville LPP 1.20): council CMS serves a 0-byte asset
  (verified via browser; no Wayback copy). Related coverage exists via
  MEL-SP-001 + MEL-LPP-015. Re-check on next refresh.
- NCC volumes are metadata-only (ABCB registration wall) — cite-or-refuse
  will correctly refuse NCC-specific questions.
- SPP 2.1/2.2/2.3/2.7/2.10 are superseded by SPP 2.9 (in corpus); aliases
  map citations of the old policies to SPP-007.

## Refresh cycle

Re-run `pipeline.py` periodically: unchanged documents are hash-skipped, new
versions overwrite with `content changed` notes, then `ingest_corpus.py`
creates new pending-review versions (the approval gate + supersession chain
handles version succession).
