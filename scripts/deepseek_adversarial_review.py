"""DeepSeek adversarial review of LotFile rule-to-address applicability.

Uses deepseek-v4-flash for 4 parallel audit passes (cheap), then
deepseek-v4-pro with thinking mode for the final synthesis (expensive,
but only ONE call).

Run: python scripts/deepseek_adversarial_review.py
Output: reports/deepseek_adversarial_review.md
"""

import os
import sys
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from openai import OpenAI

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
BASE_URL = "https://api.deepseek.com"
FLASH_MODEL = "deepseek-v4-flash"
PRO_MODEL = "deepseek-v4-pro"
REPORT_PATH = Path(__file__).resolve().parent.parent / "reports" / "deepseek_adversarial_review.md"

SRC = Path(__file__).resolve().parent.parent / "src" / "draftcheck"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def read_src(*parts: str) -> str:
    p = SRC.joinpath(*parts)
    if not p.exists():
        return f"[FILE NOT FOUND: {p}]"
    return p.read_text(encoding="utf-8", errors="replace")


def read_scripts(*parts: str) -> str:
    p = Path(__file__).resolve().parent.parent.joinpath("scripts", *parts)
    if not p.exists():
        return f"[FILE NOT FOUND: {p}]"
    return p.read_text(encoding="utf-8", errors="replace")


client = OpenAI(api_key=API_KEY, base_url=BASE_URL)


def call_flash(system: str, user: str, label: str) -> str:
    """Single flash call, no thinking mode (saves tokens)."""
    print(f"  [flash] {label}...", flush=True)
    t0 = time.time()
    resp = client.chat.completions.create(
        model=FLASH_MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        stream=False,
        max_tokens=4096,
    )
    dt = time.time() - t0
    text = resp.choices[0].message.content or ""
    usage = resp.usage
    if usage:
        print(
            f"  [flash] {label} done in {dt:.1f}s — "
            f"{usage.prompt_tokens} in / {usage.completion_tokens} out tokens",
            flush=True,
        )
    return text


def call_pro(system: str, user: str, label: str) -> str:
    """Single pro call WITH thinking mode + high reasoning effort."""
    print(f"  [PRO] {label}...", flush=True)
    t0 = time.time()
    resp = client.chat.completions.create(
        model=PRO_MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        stream=False,
        max_tokens=16384,
        reasoning_effort="high",
        extra_body={"thinking": {"type": "enabled"}},
    )
    dt = time.time() - t0
    text = resp.choices[0].message.content or ""
    usage = resp.usage
    if usage:
        thinking_tokens = getattr(usage, "completion_tokens_details", None)
        thinking_str = ""
        if thinking_tokens and hasattr(thinking_tokens, "reasoning_tokens"):
            thinking_str = f" ({thinking_tokens.reasoning_tokens} thinking)"
        print(
            f"  [PRO] {label} done in {dt:.1f}s — "
            f"{usage.prompt_tokens} in / {usage.completion_tokens}{thinking_str} out tokens",
            flush=True,
        )
    return text


# ---------------------------------------------------------------------------
# Source code bundles
# ---------------------------------------------------------------------------

ENGINE_CODE = read_src("checks", "engine.py")
RESOLVER_CODE = read_src("domain", "address", "resolver.py")
REGISTRY_CODE = read_src("checks", "registry.py")
REGISTRY_GEN_CODE = read_src("checks", "registry_generated.py")
TIER1_CODE = read_src("checks", "tier1.py")
RULES_SERVICE_CODE = read_src("domain", "rules", "service.py")
GATE_CODE = read_src("domain", "rules", "gate.py")
LGA_CODE = read_src("domain", "address", "lga.py")
ADVERSARIAL_CODE = read_scripts("adversarial_review.py")

# ---------------------------------------------------------------------------
# SYSTEM PROMPT (shared)
# ---------------------------------------------------------------------------

SYSTEM = """\
You are an adversarial code reviewer specialising in Australian planning/zoning \
compliance systems (specifically Western Australia — WAPC, DCP 2.2, R-Codes, \
local planning schemes). You think OUTSIDE THE BOX to find edge cases.

Your singular focus: ensuring that ONLY the correct rules are applied to each \
address. A rule that applies to R40 grouped dwellings must NOT be applied to an \
R20 single house. A structure plan rule for SPN 1234 must NOT leak onto a parcel \
outside that structure plan. A City of Stirling rule must NOT apply to a lot in \
the City of Armadale.

You are not looking for style issues, naming conventions, or docstring typos. \
You are looking for:
1. WRONG RULE APPLIED — a rule fires for an address it shouldn't cover
2. CORRECT RULE MISSED — a rule that SHOULD apply is silently skipped
3. WRONG VALUE — the right rule fires but with the wrong threshold/operator
4. SILENT DATA LOSS — a resolution failure that should block the check but doesn't
5. EDGE CASES — corner lots, battle-axe lots, multi-zone parcels, LGA boundaries, \
   structure plan overlaps, R-code boundary conditions, nil/zero/NaN thresholds

Respond in structured markdown. For each finding use:
### Finding: <short title>
- **Severity**: CRITICAL / HIGH / MEDIUM / LOW
- **Category**: wrong_rule_applied | correct_rule_missed | wrong_value | silent_data_loss | edge_case
- **Location**: file + function/line
- **What happens**: concrete scenario
- **Why it's wrong**: the specific mechanism
- **Suggested fix**: actionable, not vague

Be exhaustive. If you find 20 issues, list 20. Do not pad with non-issues. \
Do not repeat findings across sections."""

# ---------------------------------------------------------------------------
# FLASH PASS DEFINITIONS
# ---------------------------------------------------------------------------

FLASH_PASSES = [
    {
        "label": "rule_selection_logic",
        "user": f"""\
## AUDIT: Rule Selection & Applicability Filtering

Review the compliance engine's rule selection and filtering logic for cases \
where the WRONG rule could be applied to an address, or a CORRECT rule could \
be silently skipped.

Focus areas:
- `_select_rule_with_context` ranking logic — can a lower-ranked rule shadow \
the correct one? Can exception rules beat standard rules?
- `_get_applicable_rules` SQL filtering — NULL applicable_zones/r_codes means \
"global". Is this safe? What if a rule has an empty JSON array `[]` instead of \
NULL? What if zone_codes is an empty list vs None?
- Council scope filtering — `_resolve_council_scope` reads from facts AND \
project fields. What if they disagree? What if canonical_local_government_name \
normalises differently than the DB stored it?
- `_filter_rules_by_spatial_scope` — structure plan fail-closed logic. What if \
`required_refs` is empty but the source IS a structure plan? What about LDP \
references that don't match the fact format?
- R-code specificity — `rule.applicable_r_codes` intersection with `r_codes`. \
What if the fact stores "R40" but the rule stores "R-40" or "R 40"?

```python
# engine.py
{ENGINE_CODE}

# lga.py
{LGA_CODE}
```""",
    },
    {
        "label": "address_resolution",
        "user": f"""\
## AUDIT: Address Resolution Pipeline

Review the address resolver for cases where a property could resolve to the \
WRONG parcel, zone, R-code, or LGA — which would cause wrong rules to apply.

Focus areas:
- G-NAF trigram lookup with similarity > 0.3 — is 0.3 too low? Could "12 Smith \
St" match "12 Smith Street, DIFFERENT SUBURB"? What about unit numbers \
("Unit 3, 12 Smith St")?
- ST_Within for parcel lookup — what if the G-NAF point sits exactly on a \
parcel boundary? What about multi-polygon parcels where the point is in a \
different polygon?
- LGA resolution — ST_Intersects with lg_areas. What if the point sits on an \
LGA boundary? What if lg_areas has gaps or overlaps?
- Zone/R-code intersection — ST_Intersects on planning_features. A parcel can \
span multiple zones. `zones[0]` is used for zone_code — what determines \
ordering? What if the parcel is 90% R20 and 10% R40?
- Frontage heuristic — longest exterior ring edge. Battle-axe lots, irregular \
shapes, lots with rear lane access. The code acknowledges this but does the \
downstream engine USE frontage for rule selection?
- Corner lot heuristic — 60% threshold. What about L-shaped lots? What about \
lots with 3 long edges?
- `_upsert_facts` — deletes non-confirmed facts then re-inserts. What if a \
user had a manual_override fact? Does the DELETE preserve it? (check the \
WHERE clause)
- Multiple zones/R-codes — the resolver collects ALL zones and R-codes. But \
the engine uses `fact_by_type` which is a dict keyed by fact_type — so only \
the LAST zone fact wins. Is this correct?

```python
# resolver.py
{RESOLVER_CODE}

# lga.py
{LGA_CODE}
```""",
    },
    {
        "label": "spatial_scope_and_conditions",
        "user": f"""\
## AUDIT: Spatial Scope Filtering & Condition Matching

Review how the engine filters rules by spatial scope (structure plans, LDPs) \
and how condition matching works for numeric thresholds.

Focus areas:
- `_source_spatial_scope` — determines if a source needs spatial scoping. \
Title-based detection ("structure plan", "local development plan"). What if a \
document TITLE contains "structure plan" but it's actually a state-wide policy? \
False positive scoping would EXCLUDE valid rules.
- `_normalized_spatial_reference` — normalises "SPN 1234", "SPN/1234", \
"SPN-1234" to "SPN/1234". What about "SPN1234" (no separator)? What about \
lowercase "spn 1234"? What about "Structure Plan 1234"?
- `_property_spatial_scopes` — reads from facts. Calls \
`structure_plan_is_current(value)` — what does that do? What if a structure \
plan is superseded but still in the DB? What if the fact has no "code" key?
- `_condition_rank` — numeric conditions (wall_height_m, wall_length_m). \
Upper-bound buckets unless label says "over". What if the label is "Over 3.5m" \
vs "over 3.5m" vs "OVER 3.5"? Case sensitivity?
- `_CONDITION_METADATA_KEYS` — density_codes, dwelling_type, wall_height_label, \
wall_length_label are treated as metadata (ignored for matching). What if a \
rule has a NEW condition key not in this set? It goes into `unsupported` and \
BLOCKS the rule. Is that safe or too conservative?
- `conditional_rules_seen and not conditional_rule_matched` — returns None \
with "condition:no_matching_rule". This means if ANY conditional rule exists \
for a check but NONE match, the check is silently dropped even if an \
unconditional rule would have matched.

```python
# engine.py (spatial + condition sections)
{ENGINE_CODE}
```""",
    },
    {
        "label": "check_registry_consistency",
        "user": f"""\
## AUDIT: Check Registry Consistency & Rule Coverage Gaps

Compare the check registry, tier1 definitions, and the engine's \
_CHECK_TO_BASE_RULE_KEYS mapping for inconsistencies that could cause \
wrong rules or missed checks.

Focus areas:
- `_CHECK_TO_BASE_RULE_KEYS` maps check keys to base rule keys. E.g. \
"setback_front" -> ("primary_street_setback", "front_setback"). What if a rule \
is stored as "setback.front" (the registry pattern) but the engine looks for \
"primary_street_setback"? The `_base_rule_key` function splits on "." and \
takes [0] — so "setback.front" -> "setback", not "front_setback".
- `registry.py` SEED checks use keys like "setback_front", "site_cover". \
`tier1.py` uses "setback_side" (singular) but the registry has \
"setback_side_primary" and "setback_side_secondary". These are DIFFERENT keys.
- `registry_generated.py` — generated from clusters. What if a generated check \
key doesn't appear in `_CHECK_TO_BASE_RULE_KEYS`? The engine's \
`_select_rule_with_context` falls back to `rule.rule_key == check_key` — but \
generated checks use `canonical_rule_key`. Does the matching logic handle this?
- Advisory rules — `_get_advisory_rules` loads ALL approved non-numeric rules, \
sorted by relevance. Cap of 80. What if there are 200 advisory rules and the \
most relevant ones for THIS address are ranked below position 80?
- `_advisory_relevance_score` — keyword-based scoring. "residential" +2, \
"subdivision" -1.5. What if a genuinely relevant rule mentions "subdivision" \
in a condition ("applies to subdivision lots in residential zones")? \
Net score: +0.5. A less relevant rule about "setback" scores +1. Wrong ordering.
- Operator aliases — "pct_lte" -> "lte", "<=" -> "lte". What about "≤"? \
What about "not more than"? What about "maximum"?
- fact_keys in CheckDefinition vs CHECK_FACT_MAP in tier1.py — are they \
consistent? The engine uses `check_def.fact_keys` from the registry, NOT \
tier1.py's CHECK_FACT_MAP. So tier1.py is dead code? Or used elsewhere?

```python
# registry.py
{REGISTRY_CODE}

# tier1.py
{TIER1_CODE}

# engine.py (relevant sections)
{ENGINE_CODE}
```""",
    },
]

# ---------------------------------------------------------------------------
# PRO SYNTHESIS
# ---------------------------------------------------------------------------

PRO_SYNTHESIS_SYSTEM = SYSTEM + """

You are now doing the FINAL SYNTHESIS pass. You have findings from 4 parallel \
auditors. Your job:

1. DEDUPLICATE — merge findings that describe the same root cause
2. CROSS-REFERENCE — find COMPOUND bugs where two findings interact to create \
a worse problem than either alone (e.g. wrong zone resolution + wrong rule \
selection = completely wrong compliance verdict)
3. RANK — order by real-world severity for a WA property buyer/developer
4. EDGE CASE HUNT — using your deep reasoning, find at least 5 ADDITIONAL edge \
cases the auditors missed. Think about:
   - Battle-axe lots (rear access, no street frontage)
   - Lots spanning two R-code boundaries
   - Lots on LGA boundaries (different council rules)
   - Grouped vs single dwelling classification errors
   - Structure plan areas that partially overlap a parcel
   - Nil/zero thresholds vs missing thresholds
   - Rules extracted from the WRONG clause of a planning scheme
   - Corner lots where front/side/rear setback definitions swap
   - Heritage overlay parcels with additional height limits
   - Bushfire-prone areas with BAL requirements
5. VERDICT — for each Tier-1 check, state whether the current code can be \
trusted to apply ONLY the correct rules, with a confidence percentage

Use deep, structured thinking. This is the expensive pass — be thorough."""


def build_pro_user(flash_results: dict[str, str]) -> str:
    sections = []
    for label, result in flash_results.items():
        sections.append(f"## Flash Audit: {label}\n\n{result}")
    all_findings = "\n\n---\n\n".join(sections)

    return f"""\
## All Source Code Under Review

### engine.py (compliance engine — rule selection, filtering, evaluation)
```python
{ENGINE_CODE}
```

### resolver.py (address → parcel → zone → R-code → facts pipeline)
```python
{RESOLVER_CODE}
```

### lga.py (council name normalisation)
```python
{LGA_CODE}
```

### registry.py (check definitions)
```python
{REGISTRY_CODE}
```

### tier1.py (legacy check keys)
```python
{TIER1_CODE}
```

### rules/service.py (rule extraction & lifecycle)
```python
{RULES_SERVICE_CODE}
```

### rules/gate.py (promotion gate — validators, eval, auto-promote)
```python
{GATE_CODE}
```

---

## Flash Audit Findings (4 parallel passes)

{all_findings}

---

## YOUR TASK

Produce the FINAL ADVERSARIAL REVIEW. Follow the system instructions for \
structure. Be exhaustive. Find compound bugs. Find at least 5 edge cases the \
auditors missed. Give per-check confidence verdicts.

Remember: the ONLY thing that matters is that the correct rules are applied \
to each address. Every finding must tie back to this."""


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    if not API_KEY:
        print("ERROR: Set DEEPSEEK_API_KEY environment variable")
        sys.exit(1)

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*60}")
    print("LotFile Adversarial Review — DeepSeek V4")
    print(f"Flash model: {FLASH_MODEL} (4 parallel passes)")
    print(f"Pro model:   {PRO_MODEL} (1 synthesis pass, thinking=high)")
    print(f"Report:      {REPORT_PATH}")
    print(f"{'='*60}\n")

    # ---- Phase 1: Flash passes (parallel) ----
    print("Phase 1: Flash audit passes (parallel)...")
    flash_results: dict[str, str] = {}
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {
            pool.submit(call_flash, SYSTEM, p["user"], p["label"]): p["label"]
            for p in FLASH_PASSES
        }
        for fut in as_completed(futures):
            label = futures[fut]
            try:
                flash_results[label] = fut.result()
            except Exception as e:
                print(f"  [flash] {label} FAILED: {e}", flush=True)
                flash_results[label] = f"[AUDIT FAILED: {e}]"

    # ---- Phase 2: Pro synthesis ----
    print("\nPhase 2: Pro synthesis (thinking=high)...")
    pro_result = call_pro(
        PRO_SYNTHESIS_SYSTEM,
        build_pro_user(flash_results),
        "final_synthesis",
    )

    # ---- Write report ----
    report = f"""# LotFile Adversarial Review — DeepSeek V4
Generated: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}
Flash model: {FLASH_MODEL} | Pro model: {PRO_MODEL}

---

## Flash Pass: Rule Selection Logic
{flash_results.get('rule_selection_logic', '[missing]')}

---

## Flash Pass: Address Resolution
{flash_results.get('address_resolution', '[missing]')}

---

## Flash Pass: Spatial Scope & Conditions
{flash_results.get('spatial_scope_and_conditions', '[missing]')}

---

## Flash Pass: Check Registry Consistency
{flash_results.get('check_registry_consistency', '[missing]')}

---

## PRO SYNTHESIS (deep thinking)
{pro_result}
"""
    REPORT_PATH.write_text(report, encoding="utf-8")
    print(f"\nReport written to {REPORT_PATH}")
    print(f"Total size: {len(report):,} chars")


if __name__ == "__main__":
    main()
