# Parser Sample Evidence

Use this offline evidence scaffold to record sanitized, operator-reviewed parser
samples without touching DB artifact persistence.

## Workflow

1. Copy `docs/parser-sample-evidence-template.json` to a local evidence file.
2. Replace the sample values with sanitized facts from an operator-reviewed real
   parser run.
3. Do not include raw document text, client names, addresses, original filenames,
   or retained source content.
4. Validate the evidence:

```powershell
uv run python scripts/parser_sample_evidence.py docs/parser-sample-evidence-template.json --min-samples 1 --output reports/parser-sample-evidence.local.json
```

A passing result means the sanitized sample evidence is internally consistent.
It does not make parser beta ready by itself; persistence-connected validation
and artifact-row persistence remain DB-owned.
