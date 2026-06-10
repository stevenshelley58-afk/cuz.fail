# PC-001 (R-Codes Vol 1) — Rule Atom Extraction Report

- Source: `corpus\extracted\PC-001\full_text.txt`
- Tables extract: `corpus\extracted\PC-001\tables.json`
- Analysis: `corpus\analysis\PC-001\analysis.json`
- Output: `data\rule_atoms\PC-001.json`
- Pipeline: `docs/RULES_EXTRACTION_PIPELINE.md` §2.2 (multi-pass ensemble)
- Extractor: `scripts/extract_rcodes_atoms.py`
- Atoms emitted: **49**
- Density codes covered: R10, R15, R2, R20, R25, R30, R35, R40, R5, R60
- Building categories covered: A, B, C
- 3-pass+ consensus: 5 | 2-pass consensus: 14 | 1-pass (single view): 30
- Ensemble pass-rate (2-of-3 or better): **39%**
- Pass breakdown (raw candidates emitted by each pass):
  - 45
  - 15
  - 12
  - 5
- Discarded by validator:
  - quote anchor fail: 0
  - out of range: 0
  - applicability invalid: 0

## LLM corroboration
No live LLM provider was configured in this environment (`LLM_PROVIDER=mock`), so the LLM corroboration pass is skipped. The 3-pass ensemble still runs over four independent views of the text (Table B cell view, clause-text view, Part C table view, hand-curated analysis.json view) and quote-anchoring is enforced deterministically. The LLM corroboration is a strict additional check; the consensus confidence and auto-accepted status are computed without it.

## Clauses not structured this round
- Design-principles (P) clauses — out of scope per the brief; the ensemble targets deemed-to-comply only.
- Part C boundary wall length-and-height matrices (Table 3.4b) — these need the table-aware atom-walker (a follow-up pass).
- Visual privacy (Table 3.10a) is emitted per (room type, R-band); the per-(room, R-Code) cross product is in this pass but is unrefined vs the analysis.json example.
- Ancillary dwelling (Table 2.8a) and accessible dwelling (clause 5.5.4) — separate topic, separate run.
- Parking (clause 5.3.3, Table 2.3a), dwelling size (Table 2.1a), and storage (Table 2.1b) — outside the Part 5/6 focus and deferred.
- Boundary wall 9m length and 3.5m height cases in clause 5.1.3 C3.2 — R20 / R25 / R30-R40 variants are emitted; the per-(adjoining R-Code) intersection rule in C3.3 is a `conditions_json` candidate for a future pass.

## Atom shape
The emitted shape matches the brief:

```json
{
  "rule_key": "primary_street_setback_min_m",
  "pathway": "deemed_to_comply",
  "applicability": {"density_code": "R20", "element": "5.1.2 C2.1", "dwelling_type": "Single house or grouped dwelling"},
  "value_json": {"value": 6.0, "unit": "m", "operator": ">="},
  "verbatim_quote": "Buildings, excluding carports, porches, balconies, verandahs, or equivalent, set back from the primary",
  "source_quote_span": {"start": ..., "end": ...},
  "confidence": 0.95,
  "extraction_method": "consensus_3of3",
  "extractor_passes": ["pass1_table_b", "pass2_clause_text", "pass4_curated"],
  "status": "auto_accepted"
}
```

`source_quote_span` is a half-open `[start, end)` character offset into
`corpus/extracted/PC-001/full_text.txt`. The verbatim_quote is recoverable
from that span (whitespace-normalised) and was verified at extraction time
by the deterministic quote-anchoring validator.

## Next steps for a second pass
1. Add the no-orphan-numbers sweep from `RULES_EXTRACTION_PIPELINE.md` §2.5
   to catch numeric standards the table walker missed.
2. Add a clause-disposition pass (rule_bearing / informational /
   definitions / procedural / fluff) to drive the coverage audit.
3. Promote Part C Table 3.3a/3.4a atoms to a full per-(R-Code, dimension)
   matrix once a structured `Rule` schema is in place — the per-cell
   walker is already here, the schema is the missing piece.
4. Wire the LLM corroboration step into CI so the goldens in
   `data/eval/` can be re-verified on every extractor / prompt change.
