import sqlite3
db = r"C:\Dev\Cuz\.claude\worktrees\objective-rubin-7d1432\draftcheck-corpus.db"
c = sqlite3.connect(db, timeout=30)
# The 2 stale pending versions: 579786ef6c7c48d7be81938e80e999bd, 329548fe0de343a29ee20bc1d4dcedd0
# Their newer approved versions: c494a02ed8bf4f36bb4498cc54166115, b8821c39844e419ba39351f605a036aa
# Mark them as superseded by the newer approved version
stale = [
    ("579786ef6c7c48d7be81938e80e999bd", "c494a02ed8bf4f36bb4498cc54166115"),
    ("329548fe0de343a29ee20bc1d4dcedd0", "b8821c39844e419ba39351f605a036aa"),
]
for stale_id, new_id in stale:
    c.execute("update source_versions set superseded_by_version_id = ? where id = ?", (new_id, stale_id))
    print(f"marked {stale_id} as superseded by {new_id}")
c.commit()
print()
# Final state
print("Final state:")
for r in c.execute("select review_status, count(*) from source_versions group by 1 order by 1").fetchall():
    print(f"  {r[0]}: {r[1]}")
c.close()
