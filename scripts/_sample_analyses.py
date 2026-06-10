"""Sample partial docs and summarize quality_flags across them."""
import json
from pathlib import Path

ROOT = Path(r"C:\Dev\Cuz\.claude\worktrees\objective-rubin-7d1432")
ANALYSIS = ROOT / "corpus" / "analysis"

# Sample top 20 by size + a mix of mid-size
samples = [
    "LEG-001", "LEG-005", "LEG-004", "MEL-SP-002", "REG-001",
    "PC-003", "MEL-SCH-002", "PC-002", "PC-001", "MEL-SP-003",
    "MEL-SP-001", "FRE-SCH-001", "LEG-002", "LEG-003", "MEL-SP-004",
    "DC-006", "MEL-SCH-001", "SPP-006", "MEL-LPP-027", "SPP-012",
]

for doc_id in samples:
    p = ANALYSIS / doc_id / "analysis.json"
    if not p.exists():
        print(f"{doc_id}: NO analysis.json")
        continue
    data = json.loads(p.read_text(encoding="utf-8"))
    flags = data.get("quality_flags", [])
    print(f"=== {doc_id} ===")
    for f in flags:
        print(f"  - {f[:200]}")
    print()
