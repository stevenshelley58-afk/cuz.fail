# extract_rules

Extracts rule atoms from regulatory clause text. Produces a structured candidate with rule_key, operator, value, unit, condition, quote. Never invents values. Quote must be verbatim from input.

## Input

| Field | Type | Description |
|---|---|---|
| `clause_text` | string | Raw regulatory clause text to extract from |
| `rule_keys_hint` | string[] (optional) | Suggested rule keys to guide extraction |

## Output

A single extraction object conforming to `schema.json`.

## Behaviour contract

- `quote` must be a verbatim substring of `clause_text` — never paraphrased.
- `value_json` must be a number present in the clause. If no numeric value is found, set to `null` and lower `confidence`.
- `operator` is derived from normative language: "must not exceed" → `pct_lte`/`lte`; "minimum of" → `gte`; "at least" → `gte`; "no more than" → `lte`; exact values → `eq`.
- `unit` is `"m"` for metres, `"%"` for percent (when the operator is not already a `pct_*` variant), or `null`.
- `condition_json` captures any qualifying condition (e.g. zone, use type) as a key/value object, or `null` if unconditional.
- `confidence` reflects certainty: 1.0 = unambiguous numeric rule; lower for inferred or ambiguous extractions.
- `rule_type` defaults to `"standard"` unless the clause contains deemed-to-comply, exception, or design-principle language.
- `pathway` is `null` unless a specific assessment pathway is named.
