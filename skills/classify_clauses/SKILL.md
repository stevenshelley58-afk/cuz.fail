# classify_clauses

Classifies a clause disposition as one of: rule_bearing, definitional, procedural, informational, not_applicable. Normative language (must/shall/required/maximum/minimum) → rule_bearing. Must cite which words triggered the classification.

## Input

| Field | Type | Description |
|---|---|---|
| `text` | string | The clause text to classify |

## Output

A classification object conforming to `schema.json`.

## Disposition definitions

| Disposition | Criteria |
|---|---|
| `rule_bearing` | Contains normative language that imposes a measurable or enforceable requirement: **must**, **shall**, **required**, **maximum**, **minimum**, **must not exceed**, **at least**, **no more than** |
| `definitional` | Defines a term or concept using language like **means**, **is defined as**, **refers to** |
| `procedural` | Describes a process, step, or submission requirement: **must be submitted**, **is required to**, **shall apply to** (application process) |
| `informational` | States intent, purpose, or background without imposing a rule: **aims to**, **intended to**, **seeks to** |
| `not_applicable` | Clause is empty, corrupted, or outside the classification scope |

## Behaviour contract

- `trigger_words` must be a list of exact substrings from the input `text` that drove the classification. Never invent trigger words.
- When multiple dispositions could apply, prefer `rule_bearing` if any normative trigger is present.
- `confidence` reflects certainty: 1.0 = unambiguous; lower for borderline cases.
