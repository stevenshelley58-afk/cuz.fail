"""DeepSeek code review round 2 — engine.py + resolver.py bug hunt."""

import json
import os
import time
import urllib.request
from pathlib import Path

API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
BASE_URL = "https://api.deepseek.com"
MODEL = "deepseek-v4-flash"

SRC = Path(__file__).resolve().parent.parent / "src" / "draftcheck"
ENGINE = (SRC / "checks" / "engine.py").read_text(encoding="utf-8", errors="replace")
RESOLVER = (SRC / "domain" / "address" / "resolver.py").read_text(encoding="utf-8", errors="replace")

SYSTEM = """You are a senior Python code reviewer specializing in compliance engines and geospatial code.
Find REAL bugs, logic errors, race conditions, unhandled edge cases, and silent failures.
Do NOT report style issues, naming, or docstring problems.
Do NOT report things that are already handled correctly.
For each finding:
### <title>
- **Severity**: CRITICAL | HIGH | MEDIUM | LOW
- **Location**: file:line_range
- **Bug**: what goes wrong
- **Fix**: exact code change needed
Only report findings you are >80% confident are real bugs. No speculation."""

USER = f"""## engine.py ({len(ENGINE)} chars)
```python
{ENGINE}
```

## resolver.py ({len(RESOLVER)} chars)
```python
{RESOLVER}
```"""

payload = json.dumps({
    "model": MODEL,
    "messages": [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": USER},
    ],
    "max_tokens": 12000,
    "thinking": {"type": "disabled"},
}).encode()

req = urllib.request.Request(
    f"{BASE_URL}/chat/completions",
    data=payload,
    headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}",
    },
)

print("Calling DeepSeek flash for code review round 2...")
t0 = time.time()
with urllib.request.urlopen(req, timeout=180) as resp:
    data = json.loads(resp.read())
dt = time.time() - t0

msg = data["choices"][0]["message"]
content = msg.get("content", "") or ""
usage = data.get("usage", {})
print(f"Done in {dt:.1f}s — {usage.get('prompt_tokens', '?')}/{usage.get('completion_tokens', '?')} tokens")

out = Path(__file__).resolve().parent.parent / "reports" / "deepseek_code_review_r2.md"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(f"# Code Review Round 2 — engine.py + resolver.py\n\n{content}\n", encoding="utf-8")
print(f"Report: {out}")
print(content[:6000])
