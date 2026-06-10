import json
r = json.load(open(r"C:\Dev\Cuz\.claude\worktrees\objective-rubin-7d1432\reports\ingestion_report.json", encoding="utf-8"))
for it in r["items"]:
    if it["id"] in ["SPP-001", "MEL-MAP-002", "FRE-LPP-001", "JOO-LPP-011"]:
        # Convert 36-char to 32-char
        vid = it["source_version_id"]
        vid32 = vid.replace("-", "")
        print(f"  {it['id']}: report vid={vid} -> 32char={vid32}")
