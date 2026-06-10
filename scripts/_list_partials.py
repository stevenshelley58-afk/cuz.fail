"""List partial-quality docs with chars >= 5000 and rank them."""
import json
import os
from pathlib import Path

ROOT = Path(r"C:\Dev\Cuz\.claude\worktrees\objective-rubin-7d1432")
EXTRACTED = ROOT / "corpus" / "extracted"
VERIFICATION = ROOT / "reports" / "verification_results.json"


def main() -> None:
    verification = json.loads(VERIFICATION.read_text(encoding="utf-8"))
    rows = []
    for entry in verification["results"]:
        if entry.get("extraction_quality") != "partial":
            continue
        doc_id = entry["id"]
        txt = EXTRACTED / doc_id / "full_text.txt"
        if not txt.exists():
            continue
        chars = txt.stat().st_size
        if chars < 5000:
            continue
        rows.append((doc_id, chars, entry.get("reason", ""), entry.get("analyst_confidence", "")))
    rows.sort(key=lambda r: -r[1])
    print(f"partial-quality docs with chars >= 5000: {len(rows)}")
    print(f"{'id':<14} {'chars':>9}  conf  reason")
    for r in rows:
        print(f"{r[0]:<14} {r[1]:>9}  {r[3]:<6}  {r[2][:80]}")
    out = ROOT / "reports" / "partial_candidates.json"
    out.write_text(
        json.dumps(
            [{"id": r[0], "chars": r[1], "confidence": r[3], "reason": r[2]} for r in rows],
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
