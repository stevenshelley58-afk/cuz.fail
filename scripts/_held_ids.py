import json
r = json.load(open(r"C:\Dev\Cuz\.claude\worktrees\objective-rubin-7d1432\reports\ingestion_report.json", encoding="utf-8"))
held_ids = []
for it in r["items"]:
    if it.get("approved") is False and not it.get("error"):
        held_ids.append(it["id"])
print(f"held: {len(held_ids)}")
print(held_ids)
