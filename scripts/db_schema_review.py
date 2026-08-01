"""DeepSeek schema review — identifies structural DB improvements.

Uses flash model (cheap) to analyze the LotFile schema and suggest
indexes, constraints, and normalization improvements.
"""

import json
import os
import sys
import time
import urllib.request
from pathlib import Path

API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
BASE_URL = "https://api.deepseek.com"
MODEL = "deepseek-v4-flash"


def call_deepseek(system: str, user: str) -> tuple[str, dict]:
    """Call DeepSeek API via urllib (no openai SDK dependency)."""
    payload = json.dumps({
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "max_tokens": 4096,
    }).encode()
    req = urllib.request.Request(
        f"{BASE_URL}/chat/completions",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {API_KEY}",
        },
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read())
    content = data["choices"][0]["message"]["content"] or ""
    usage = data.get("usage", {})
    return content, usage

SRC = Path(__file__).resolve().parent.parent / "src" / "draftcheck"

def read(*parts):
    p = SRC.joinpath(*parts)
    return p.read_text(encoding="utf-8", errors="replace") if p.exists() else f"[NOT FOUND: {p}]"

# Read key files
MODELS = read("db", "models.py")
ENGINE = read("checks", "engine.py")
RESOLVER = read("domain", "address", "resolver.py")
MIGRATION_0020 = (Path(__file__).resolve().parent.parent / "src" / "draftcheck" / "db" / "alembic" / "versions" / "0020_add_rule_coverage_columns.py")
MIG_0020 = MIGRATION_0020.read_text(encoding="utf-8", errors="replace") if MIGRATION_0020.exists() else "[NOT FOUND]"

client = None  # unused — using urllib directly

SYSTEM = """You are a PostgreSQL performance engineer reviewing a planning compliance database.
Focus on:
1. Missing indexes for common query patterns (especially the compliance engine's rule loading)
2. Missing constraints (CHECK, FK) that prevent bad data
3. Normalization issues (JSONB arrays that should be junction tables)
4. Performance anti-patterns in the query patterns shown in engine.py and resolver.py

For each finding, output:
### <title>
- **Type**: index | constraint | normalization | performance
- **Impact**: HIGH | MEDIUM | LOW
- **Table(s)**: affected
- **SQL**: the exact CREATE INDEX / ALTER TABLE / migration SQL
- **Why**: one sentence

Be specific. Give exact column names from the schema. Output only findings, no preamble."""

USER = f"""## Schema (models.py — key tables)

```python
{MODELS[:40000]}
```

## Latest migration (0020)
```python
{MIG_0020}
```

## Query patterns from engine.py (rule loading)
```python
{ENGINE[:20000]}
```

## Query patterns from resolver.py (spatial lookups)
```python
{RESOLVER[:15000]}
```

Analyze and produce findings."""

print("Calling DeepSeek flash for schema review...")
t0 = time.time()
result, usage = call_deepseek(SYSTEM, USER)
dt = time.time() - t0
print(f"Done in {dt:.1f}s — {usage.get('prompt_tokens', '?')} in / {usage.get('completion_tokens', '?')} out tokens\n")

# Write report
out = Path(__file__).resolve().parent.parent / "reports" / "db_schema_review.md"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(f"# DB Schema Review — DeepSeek Flash\n\n{result}\n", encoding="utf-8")
print(f"Report: {out}")
print("\n" + result[:3000])
