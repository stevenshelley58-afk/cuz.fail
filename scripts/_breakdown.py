import json
r = json.load(open(r"C:\Dev\Cuz\.claude\worktrees\objective-rubin-7d1432\reports\ingestion_report.json", encoding="utf-8"))
metadata_only = [it for it in r["items"] if it.get("metadata_only")]
print(f"metadata_only: {len(metadata_only)}")
for it in metadata_only:
    print(f"  {it['id']}: chars={it.get('chars')}")
print()
# Show approvals by category
v = json.load(open(r"C:\Dev\Cuz\.claude\worktrees\objective-rubin-7d1432\reports\verification_results.json", encoding="utf-8"))
approved_ids = {it["id"] for it in r["items"] if it.get("approved")}
held_ids = {it["id"] for it in r["items"] if it.get("approved") is False and not it.get("error")}
mo_ids = {it["id"] for it in metadata_only}
by_quality = {}
for it in v["results"]:
    q = it["extraction_quality"]
    by_quality.setdefault(q, []).append(it["id"])
for q, ids in by_quality.items():
    a = len([i for i in ids if i in approved_ids])
    h = len([i for i in ids if i in held_ids])
    m = len([i for i in ids if i in mo_ids])
    o = len([i for i in ids if i not in approved_ids and i not in held_ids and i not in mo_ids])
    print(f"  {q}: approved={a}, held={h}, meta_only={m}, other={o} (total={len(ids)})")
