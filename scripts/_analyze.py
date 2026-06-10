import json
r = json.load(open(r"C:\Dev\Cuz\.claude\worktrees\objective-rubin-7d1432\reports\ingestion_report.json", encoding="utf-8"))
print("counts:", r["counts"])
print()
# Show non-approved, non-duplicate, non-error items
held = [it for it in r["items"] if it.get("approved") is False and not it.get("duplicate") and not it.get("error")]
print(f"held_pending (executed, not approved, not duplicate): {len(held)}")
for it in held[:30]:
    print(f"  {it['id']}: {it.get('held_reason', {})}")
print()
# Show duplicates (existing versions re-approved)
dups = [it for it in r["items"] if it.get("duplicate")]
print(f"duplicates: {len(dups)}")
dups_approved = [it for it in dups if it.get("approved")]
dups_held = [it for it in dups if it.get("approved") is False]
print(f"  approved: {len(dups_approved)}")
print(f"  held: {len(dups_held)}")
for it in dups_held[:10]:
    print(f"    {it['id']}: {it.get('held_reason')}")
print()
# Show imported (new) items
imported = [it for it in r["items"] if not it.get("duplicate") and not it.get("error") and not it.get("metadata_only")]
print(f"imported (new): {len(imported)}")
for it in imported[:5]:
    print(f"  {it['id']}: approved={it.get('approved')} held={it.get('held_reason')}")
print()
errors = [it for it in r["items"] if it.get("error")]
print(f"errors: {len(errors)}")
for it in errors[:5]:
    print(f"  {it['id']}: {it['error']}")
