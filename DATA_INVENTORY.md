# DraftCheck WA Data Inventory

Date: 2026-06-07

Authority: supporting inventory for `docs/MASTER_REBUILD_PLAN.md`.

## Git And Safety Baseline

```text
git ls-files               1 tracked file before PR0 materialisation (`README.md`)
.gitignore                 updated to exclude runtime/private artifacts before staging
draftcheck.db              present locally; excluded from Git; harvest source only after integrity check
.storage/                  present locally; excluded from Git; classify before archive/sharing
data/corpus/               evidence input only; excluded from Git
```

New PR0 guards:

```text
scripts/precommit_guard.py          blocks forbidden paths, files >5 MB, and obvious secrets
scripts/check_sqlite_integrity.py   read-only SQLite integrity and harvest-count check
```

## Local SQLite Integrity

Command:

```powershell
.\.venv\Scripts\python.exe scripts\check_sqlite_integrity.py draftcheck.db --json
```

Observed in this workspace:

```text
integrity_check            ok
database size              153,128,960 bytes
```

Harvestable row counts from the integrity-checked local copy:

| Table | Rows |
|---|---:|
| source_documents | 81 |
| source_versions | 83 |
| source_licence_reviews | 83 |
| clauses | 28,068 |
| source_chunks | 31,200 |
| source_citations | 31,200 |
| rule_rows | 6 |
| rule_extraction_candidates | 4 |
| clause_dispositions | 65 |
| review_queue_items | 155 |
| golden_eval_cases | 19 |
| golden_eval_runs | 16 |
| audit_events | 379 |

PR5 must harvest from a verified or recovered copy and record final row counts here before
`draftcheck.db` is archived out of the working tree.

### Open-vocab rule schema note (2026-06-14)

The rule-extraction pipeline is open-vocab: the extractor proposes any snake_case `rule_key`,
and post-hoc clustering canonicalises the raw strings (see `docs/OPEN_VOCAB_REBUILD_PLAN.md`,
subordinate to `docs/MASTER_REBUILD_PLAN.md`). Schema impact on the `rules` and
`rule_candidates` tables:

- `canonical_rule_key` — `String(160)`, nullable, indexed. Added by migration
  `0018_rule_canonical_keys` on BOTH `rules` and `rule_candidates`. Holds the cluster label
  assigned by `scripts/wp6_cluster_keys.py` and bulk-filled by `scripts/wp6_apply_clustering.py`;
  the free-form `rule_key` is preserved alongside it.
- Open-vocab candidates carry `metadata_json.open_vocab = true` on `rule_candidates` (the
  existing JSONB `metadata_json` column), flagging keys proposed outside the former soft-hint
  set (`RULE_KEY_HINTS` / `is_hinted_key()` in `src/draftcheck/extraction/vocabulary.py`).

## Corpus Inventory

`data/corpus/` is a local evidence input, not source code to track.

```text
file count                 1,422
total size                 1,867,624,576 bytes
```

Top extensions:

| Extension | Files |
|---|---:|
| .txt | 618 |
| .pdf | 526 |
| .bin | 120 |
| .jsonl | 56 |
| .md | 55 |
| .docx | 21 |
| .csv | 20 |
| .log | 4 |
| .doc | 2 |

Known useful slices:

```text
data/corpus/discovery-flatout-20260605-184911
data/corpus/discovery-initial-3
data/corpus/wa-councils-20260605-filtered
```

Use filtered council rows first. Do not bulk-import all batch/deep corpus rows without licence,
currency, relevance, and privacy review.

## Local Object Storage Inventory

`.storage/` is excluded from Git and must be classified before archive or sharing.

```text
file count                 2,233
total size                 18,175,942 bytes
primary contents           project uploads, exports, jobs, local generated artifacts
```

Treat `.storage/projects` and `.storage/exports` as private or test-project artifacts unless the
Fixtures Owner explicitly promotes a scrubbed fixture.

## Licence And Privacy Notes

- Approved source licence rows still need launch review for redistribution and commercial use.
- Metadata-only or restricted rows cannot support regulatory answers.
- Australian Standards full text remains metadata-only unless lawfully supplied and reviewed.
- Landgate/SLIP commercial cadastre licensing remains a launch blocker.
