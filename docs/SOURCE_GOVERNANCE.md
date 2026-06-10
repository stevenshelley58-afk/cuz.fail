# Source Governance

LotFile stores source provenance before source text can support an answer.

Required source metadata:

- source title
- jurisdiction and authority
- local government where applicable
- source type
- canonical URL or file reference
- licence/access notes
- access type
- scrape allowed flag
- version label
- effective date
- published date
- retrieved date
- content SHA-256
- superseded status

## Lawful Ingestion Rules

- Only public lawful sources can be fetched automatically.
- Do not bypass paywalls, login gates, captchas, robots.txt, rate limits, copyright, or licence controls.
- Do not scrape paid Australian Standards full text. Store public metadata and official access references only.
- NCC/ABCB content must be fetched only where the official access path and licence allow it.
- Superseded versions remain audit-visible but are excluded from default retrieval.
- If no current approved source chunk supports an answer, return unsupported.

## Seed Anchors

`data/seed/source_manifest.example.yaml` contains provided source anchors for WA R-Codes, PlanWA, DFES, Building and Energy, NCC/ABCB, Standards Australia metadata, and a generic Cockburn policy example. Treat those as starting points requiring lawful verification during real ingestion.
